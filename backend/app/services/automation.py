from __future__ import annotations

import hashlib
import hmac
import json
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any
from urllib import request

from app.config import settings

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
RULES_FILE = DATA_DIR / "automation_rules.json"
EVENTS_FILE = DATA_DIR / "automation_events.jsonl"

DEFAULT_RULES = {
    "rules": [
        {
            "id": "notify-interview",
            "enabled": True,
            "on_stage": "interview",
            "actions": [
                {
                    "type": "email",
                    "subject": "Interview stage update",
                    "body": "Hello {{candidate_name}}, your application moved to interview stage.",
                }
            ],
        }
    ]
}


def _ensure_files():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not RULES_FILE.exists():
        RULES_FILE.write_text(json.dumps(DEFAULT_RULES, indent=2), encoding="utf-8")
    if not EVENTS_FILE.exists():
        EVENTS_FILE.write_text("", encoding="utf-8")


def load_rules() -> dict[str, Any]:
    _ensure_files()
    return json.loads(RULES_FILE.read_text(encoding="utf-8"))


def save_rules(payload: dict[str, Any]) -> dict[str, Any]:
    _ensure_files()
    RULES_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def append_event(event: dict[str, Any]):
    _ensure_files()
    with EVENTS_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")


def read_events(limit: int = 200) -> list[dict[str, Any]]:
    _ensure_files()
    lines = [ln for ln in EVENTS_FILE.read_text(encoding="utf-8").splitlines() if ln.strip()]
    rows = [json.loads(ln) for ln in lines[-limit:]]
    rows.reverse()
    return rows


def _render_template(text: str, payload: dict[str, Any]) -> str:
    out = text
    for k, v in payload.items():
        out = out.replace(f"{{{{{k}}}}}", str(v))
    return out


def _send_email(to_email: str, subject: str, body: str) -> tuple[bool, str]:
    if not settings.smtp_enabled:
        return False, "smtp_disabled"
    if not settings.smtp_host or not settings.smtp_from_email:
        return False, "smtp_incomplete_config"

    try:
        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = subject
        msg["From"] = settings.smtp_from_email
        msg["To"] = to_email

        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as server:
            if settings.smtp_use_tls:
                server.starttls()
            if settings.smtp_username:
                server.login(settings.smtp_username, settings.smtp_password)
            server.sendmail(settings.smtp_from_email, [to_email], msg.as_string())
        return True, "email_sent"
    except Exception as e:
        return False, f"email_error:{e}"


def _call_webhook(url: str, payload: dict[str, Any]) -> tuple[bool, str]:
    try:
        raw = json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json"}

        if settings.webhook_signing_secret:
            sig = hmac.new(
                settings.webhook_signing_secret.encode("utf-8"),
                raw,
                hashlib.sha256,
            ).hexdigest()
            headers["X-MiniATS-Signature"] = f"sha256={sig}"

        req = request.Request(url, data=raw, headers=headers, method="POST")
        with request.urlopen(req, timeout=8) as resp:
            return True, f"webhook:{resp.status}"
    except Exception as e:
        return False, f"webhook_error:{e}"


def run_stage_change_automations(*, candidate_id: int, candidate_name: str, stage: str, email: str | None):
    rules = load_rules().get("rules", [])
    outputs: list[dict[str, Any]] = []

    base_payload = {
        "candidate_id": candidate_id,
        "candidate_name": candidate_name,
        "stage": stage,
        "email": email or "",
        "timestamp": datetime.utcnow().isoformat(),
    }

    for rule in rules:
        if not rule.get("enabled", True):
            continue
        if (rule.get("on_stage") or "").strip().lower() != stage:
            continue

        for action in rule.get("actions", []):
            action_type = action.get("type")
            result = "ok"

            if action_type == "webhook":
                ok, result = _call_webhook(action.get("url", ""), base_payload)
                if not ok:
                    result = f"failed:{result}"

            elif action_type == "email":
                to_email = action.get("to") or email
                subject = _render_template(action.get("subject", "Stage update"), base_payload)
                body = _render_template(action.get("body", "Candidate stage updated."), base_payload)

                if not to_email:
                    result = "failed:missing_recipient"
                else:
                    ok, result = _send_email(to_email, subject, body)
                    if not ok:
                        result = f"failed:{result}"

            elif action_type == "log":
                result = action.get("message", "logged")

            else:
                result = f"unsupported_action:{action_type}"

            event = {
                "timestamp": datetime.utcnow().isoformat(),
                "candidate_id": candidate_id,
                "candidate_name": candidate_name,
                "stage": stage,
                "rule_id": rule.get("id"),
                "action": action,
                "result": result,
            }
            append_event(event)
            outputs.append(event)

    return outputs
