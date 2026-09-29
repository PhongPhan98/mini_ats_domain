from __future__ import annotations

import hashlib
import hmac
import json
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from typing import Any
from urllib import request

from app.config import settings
from app.database import SessionLocal
from app.models import AutomationEvent, AutomationRule, Candidate, User


def _owner(db, owner_key: str | None, candidate_id: int | None = None):
    if owner_key and owner_key != "*":
        return db.query(User).filter(User.email == owner_key.lower()).first()
    if candidate_id:
        candidate = db.get(Candidate, candidate_id)
        if candidate and candidate.owner_user_id:
            return db.get(User, candidate.owner_user_id)
    return None


def load_rules(owner_key: str | None = None) -> dict[str, Any]:
    with SessionLocal() as db:
        owner = _owner(db, owner_key)
        query = db.query(AutomationRule)
        if owner:
            query = query.filter(AutomationRule.organization_id == owner.organization_id, AutomationRule.owner_user_id == owner.id)
        elif owner_key not in (None, "*"):
            return {"rules": []}
        rows = query.order_by(AutomationRule.id).all()
        return {"rules": [{"id": row.rule_key, "enabled": row.enabled, "on_stage": row.on_stage, "actions": row.actions or []} for row in rows]}


def save_rules(payload: dict[str, Any], owner_key: str | None = None) -> dict[str, Any]:
    with SessionLocal() as db:
        owner = _owner(db, owner_key)
        if not owner:
            return {"rules": []}
        db.query(AutomationRule).filter(AutomationRule.organization_id == owner.organization_id, AutomationRule.owner_user_id == owner.id).delete()
        saved = []
        for index, rule in enumerate(payload.get("rules", [])):
            row = AutomationRule(
                organization_id=owner.organization_id,
                owner_user_id=owner.id,
                rule_key=str(rule.get("id") or f"rule-{index + 1}")[:120],
                enabled=bool(rule.get("enabled", True)),
                on_stage=str(rule.get("on_stage") or "").lower()[:32],
                actions=list(rule.get("actions") or []),
            )
            db.add(row)
            saved.append({"id": row.rule_key, "enabled": row.enabled, "on_stage": row.on_stage, "actions": row.actions})
        db.commit()
        return {"rules": saved}


def append_event(event: dict[str, Any], owner_key: str | None = None):
    with SessionLocal() as db:
        candidate_id = int(event.get("candidate_id") or 0) or None
        owner = _owner(db, owner_key, candidate_id)
        candidate = db.get(Candidate, candidate_id) if candidate_id else None
        db.add(AutomationEvent(
            organization_id=(owner.organization_id if owner else getattr(candidate, "organization_id", None)),
            owner_user_id=(owner.id if owner else getattr(candidate, "owner_user_id", None)),
            candidate_id=candidate_id,
            payload=event,
        ))
        db.commit()


def clear_events(owner_key: str | None = None):
    with SessionLocal() as db:
        owner = _owner(db, owner_key)
        query = db.query(AutomationEvent)
        if owner:
            query = query.filter(AutomationEvent.organization_id == owner.organization_id)
            if owner.role == "recruiter":
                query = query.filter(AutomationEvent.owner_user_id == owner.id)
        query.delete(synchronize_session=False)
        db.commit()


def read_events(limit: int = 200, owner_key: str | None = None) -> list[dict[str, Any]]:
    with SessionLocal() as db:
        owner = _owner(db, owner_key)
        query = db.query(AutomationEvent)
        if owner:
            query = query.filter(AutomationEvent.organization_id == owner.organization_id)
            if owner.role == "recruiter":
                query = query.filter(AutomationEvent.owner_user_id == owner.id)
        return [row.payload for row in query.order_by(AutomationEvent.created_at.desc()).limit(limit).all()]


def _render_template(text: str, payload: dict[str, Any]) -> str:
    for key, value in payload.items():
        text = text.replace(f"{{{{{key}}}}}", str(value))
    return text


def _send_email(to_email: str, subject: str, body: str) -> tuple[bool, str]:
    if not settings.smtp_enabled or not settings.smtp_host or not settings.smtp_from_email:
        return False, "smtp_not_configured"
    try:
        message = MIMEText(body, "plain", "utf-8")
        message["Subject"], message["From"], message["To"] = subject, settings.smtp_from_email, to_email
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as server:
            if settings.smtp_use_tls:
                server.starttls()
            if settings.smtp_username:
                server.login(settings.smtp_username, settings.smtp_password)
            server.sendmail(settings.smtp_from_email, [to_email], message.as_string())
        return True, "email_sent"
    except Exception as exc:
        return False, f"email_error:{exc}"


def _call_webhook(url: str, payload: dict[str, Any]) -> tuple[bool, str]:
    if not url.lower().startswith("https://"):
        return False, "webhook_requires_https"
    try:
        raw = json.dumps(payload).encode()
        headers = {"Content-Type": "application/json"}
        if settings.webhook_signing_secret:
            signature = hmac.new(settings.webhook_signing_secret.encode(), raw, hashlib.sha256).hexdigest()
            headers["X-MiniATS-Signature"] = f"sha256={signature}"
        with request.urlopen(request.Request(url, data=raw, headers=headers, method="POST"), timeout=8) as response:
            return True, f"webhook:{response.status}"
    except Exception as exc:
        return False, f"webhook_error:{exc}"


def run_stage_change_automations(*, candidate_id: int, candidate_name: str, stage: str, email: str | None, owner_key: str | None = None):
    with SessionLocal() as db:
        owner = _owner(db, owner_key, candidate_id)
        resolved_key = owner.email if owner else owner_key
    rules = load_rules(resolved_key).get("rules", [])
    base = {"candidate_id": candidate_id, "candidate_name": candidate_name, "stage": stage, "email": email or "", "timestamp": datetime.utcnow().isoformat()}
    outputs = []
    for rule in rules:
        if not rule.get("enabled", True) or str(rule.get("on_stage", "")).lower() != stage:
            continue
        for action in rule.get("actions", []):
            action_type = action.get("type")
            if action_type == "email":
                recipient = action.get("to") or email
                ok, result = _send_email(recipient, _render_template(action.get("subject", "Stage update"), base), _render_template(action.get("body", "Candidate stage updated."), base)) if recipient else (False, "missing_recipient")
            elif action_type == "webhook":
                ok, result = _call_webhook(str(action.get("url") or ""), base)
            elif action_type == "log":
                ok, result = True, str(action.get("message") or "logged")
            else:
                ok, result = False, f"unsupported_action:{action_type}"
            event = {**base, "rule_id": rule.get("id"), "action": action, "result": result if ok else f"failed:{result}"}
            append_event(event, resolved_key)
            outputs.append(event)
    return outputs
