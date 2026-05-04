from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Candidate, InterviewSchedule
from app.rbac import get_current_user, require_roles
from app.schemas import InterviewScheduleCreate, InterviewScheduleOut
from app.services.automation import append_event, run_stage_change_automations

router = APIRouter(prefix="/api/interviews", tags=["interviews"])


def _append_timeline_event(candidate: Candidate, event_type: str, value: str):
    parsed_json = dict(candidate.parsed_json or {})
    timeline = list(parsed_json.get("timeline", []))
    timeline.append({"type": event_type, "value": value, "timestamp": datetime.utcnow().isoformat()})
    parsed_json["timeline"] = timeline
    parsed_json["manual_reviewed"] = True
    candidate.parsed_json = parsed_json


@router.post("", response_model=InterviewScheduleOut)
def create_interview(
    payload: InterviewScheduleCreate,
    candidate_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
    _=Depends(require_roles("admin", "recruiter", "hiring_manager")),
):
    candidate = db.get(Candidate, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    schedule = InterviewSchedule(
        candidate_id=candidate_id,
        organizer_user_id=user.id,
        interviewer_email=payload.interviewer_email,
        scheduled_at=payload.scheduled_at,
        duration_minutes=payload.duration_minutes,
        meeting_link=payload.meeting_link,
        notes=payload.notes,
    )
    db.add(schedule)

    _append_timeline_event(candidate, "schedule", f"Interview scheduled at {payload.scheduled_at.isoformat()} with {payload.interviewer_email}")
    run_stage_change_automations(candidate_id=candidate.id, candidate_name=candidate.name or f"Candidate #{candidate.id}", stage="interview", email=candidate.email)
    append_event({"timestamp": datetime.utcnow().isoformat(), "candidate_id": candidate.id, "candidate_name": candidate.name or f"Candidate #{candidate.id}", "stage": "interview", "rule_id": "schedule-notify", "action": {"type": "email", "to": payload.interviewer_email, "subject": f"Interview scheduled: {candidate.name or candidate.id}"}, "result": f"queued_schedule_notification:{payload.interviewer_email}"})

    db.commit()
    db.refresh(schedule)
    return schedule
