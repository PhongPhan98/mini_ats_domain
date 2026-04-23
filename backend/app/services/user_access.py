from pathlib import Path
import json

_ACCESS_PATH = Path(__file__).resolve().parents[1] / "data" / "users_access.json"


def _load() -> dict:
    try:
        data = json.loads(_ACCESS_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save(data: dict):
    _ACCESS_PATH.parent.mkdir(parents=True, exist_ok=True)
    _ACCESS_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def is_disabled(user_id: int, email: str) -> bool:
    data = _load()
    disabled_ids = {int(x) for x in data.get("disabled_user_ids", [])}
    disabled_emails = {str(x).lower() for x in data.get("disabled_emails", [])}
    return user_id in disabled_ids or email.lower() in disabled_emails


def set_disabled(user_id: int, email: str, disabled: bool):
    data = _load()
    disabled_ids = {int(x) for x in data.get("disabled_user_ids", [])}
    disabled_emails = {str(x).lower() for x in data.get("disabled_emails", [])}

    if disabled:
        disabled_ids.add(user_id)
        disabled_emails.add(email.lower())
    else:
        disabled_ids.discard(user_id)
        disabled_emails.discard(email.lower())

    data["disabled_user_ids"] = sorted(disabled_ids)
    data["disabled_emails"] = sorted(disabled_emails)
    _save(data)


def list_disabled_ids() -> set[int]:
    data = _load()
    return {int(x) for x in data.get("disabled_user_ids", [])}
