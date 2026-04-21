from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from urllib import request

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
                {"type": "log", "message": "Interview stage reached"}
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
    EVENTS_FILE.write_text(
        EVENTS_FILE.read_text(encoding="utf-8") + json.dumps(event, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def read_events(limit: int = 200) -> list[dict[str, Any]]:
    _ensure_files()
    lines = [ln for ln in EVENTS_FILE.read_text(encoding="utf-8").splitlines() if ln.strip()]
    rows = [json.loads(ln) for ln in lines[-limit:]]
    rows.reverse()
    return rows


def _call_webhook(url: str, payload: dict[str, Any]) -> tuple[bool, str]:
    try:
        req = request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with request.urlopen(req, timeout=8) as resp:
            return True, f"webhook:{resp.status}"
    except Exception as e:
        return False, f"webhook_error:{e}"


def run_stage_change_automations(*, candidate_id: int, candidate_name: str, stage: str, email: str | None):
    rules = load_rules().get("rules", [])
    outputs: list[dict[str, Any]] = []
    for rule in rules:
        if not rule.get("enabled", True):
            continue
        if (rule.get("on_stage") or "").strip().lower() != stage:
            continue

        for action in rule.get("actions", []):
            action_type = action.get("type")
            result = "ok"
            if action_type == "webhook":
                ok, result = _call_webhook(
                    action.get("url", ""),
                    {
                        "candidate_id": candidate_id,
                        "candidate_name": candidate_name,
                        "stage": stage,
                        "email": email,
                        "timestamp": datetime.utcnow().isoformat(),
                    },
                )
                if not ok:
                    result = f"failed:{result}"
            elif action_type == "email":
                # v1: queued-only stub (no SMTP yet)
                result = f"queued_email_to:{email or 'unknown'}"
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
