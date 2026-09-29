from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Candidate, CandidateTimeline
from app.rbac import require_roles
from app.services.candidate_access import can_manage_candidate

router = APIRouter(prefix="/api/activity", tags=["activity"])


@router.get("")
def activity_feed(
    limit: int = Query(default=200, ge=1, le=1000),
    db: Session = Depends(get_db),
    actor=Depends(require_roles("admin", "recruiter", "hiring_manager", "interviewer")),
):
    events = []
    candidates = list(db.execute(select(Candidate).where(Candidate.organization_id == actor.organization_id)).scalars().all())
    for c in candidates:
        if not can_manage_candidate(actor, c):
            continue
        timeline = list(db.execute(select(CandidateTimeline).where(CandidateTimeline.candidate_id == c.id)).scalars().all())
        for ev in timeline:
            events.append({
                "candidate_id": c.id,
                "candidate_name": c.name,
                "type": ev.event_type,
                "value": ev.value,
                "timestamp": ev.created_at.isoformat(),
            })
    events.sort(key=lambda x: str(x.get("timestamp") or ""), reverse=True)
    return {"events": events[:limit]}
