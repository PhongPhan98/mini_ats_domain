from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Candidate
from app.rbac import require_roles

router = APIRouter(prefix="/api/activity", tags=["activity"])


def _can_access_candidate(user, candidate: Candidate) -> bool:
    if getattr(user, "role", "") != "recruiter":
        return True
    parsed = candidate.parsed_json or {}
    owner_id = parsed.get("owner_user_id")
    owner_email = str(parsed.get("owner_email") or "").lower()
    return (owner_id is not None and int(owner_id) == int(user.id)) or (owner_email and owner_email == user.email.lower())


@router.get("")
def activity_feed(
    limit: int = Query(default=200, ge=1, le=1000),
    db: Session = Depends(get_db),
    actor=Depends(require_roles("admin", "recruiter", "hiring_manager", "interviewer")),
):
    events = []
    candidates = list(db.execute(select(Candidate)).scalars().all())
    for c in candidates:
        if not _can_access_candidate(actor, c):
            continue
        for ev in (c.parsed_json or {}).get("timeline", []):
            events.append({
                "candidate_id": c.id,
                "candidate_name": c.name,
                "type": ev.get("type"),
                "value": ev.get("value"),
                "timestamp": ev.get("timestamp"),
            })
    events.sort(key=lambda x: str(x.get("timestamp") or ""), reverse=True)
    return {"events": events[:limit]}
