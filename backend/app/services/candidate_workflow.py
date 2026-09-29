from datetime import datetime
from typing import Any
from sqlalchemy.orm import object_session

from app.models import CandidateTimeline


def normalize_candidate_status(value: str | None) -> str:
    if not value:
        return "applied"
    normalized = value.strip().lower()
    return {"new": "applied", "shortlisted": "screening"}.get(normalized, normalized)


def append_timeline_event(candidate: Any, event_type: str, value: str) -> None:
    parsed = dict(candidate.parsed_json or {})
    timeline = list(parsed.get("timeline", []))
    timeline.append(
        {
            "type": event_type,
            "value": value,
            "timestamp": datetime.utcnow().isoformat(),
        }
    )
    parsed["timeline"] = timeline
    parsed["manual_reviewed"] = True
    candidate.parsed_json = parsed
    session = object_session(candidate)
    if session is not None and getattr(candidate, "id", None):
        session.add(CandidateTimeline(candidate_id=candidate.id, event_type=event_type, value=value))
