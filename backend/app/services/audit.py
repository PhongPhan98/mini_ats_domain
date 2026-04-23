from __future__ import annotations

from datetime import datetime
from pathlib import Path
import json

_AUDIT_PATH = Path(__file__).resolve().parents[1] / "data" / "audit_events.jsonl"


def log_event(actor_email: str, action: str, target: str, metadata: dict | None = None):
    _AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "timestamp": datetime.utcnow().isoformat(),
        "actor_email": actor_email,
        "action": action,
        "target": target,
        "metadata": metadata or {},
    }
    with _AUDIT_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def read_events(limit: int = 200) -> list[dict]:
    if not _AUDIT_PATH.exists():
        return []
    lines = _AUDIT_PATH.read_text(encoding="utf-8").splitlines()
    out = []
    for line in lines[-limit:]:
        try:
            out.append(json.loads(line))
        except Exception:
            continue
    out.reverse()
    return out
