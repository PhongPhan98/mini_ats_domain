from datetime import datetime
import re

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Application, Candidate, InterviewSchedule
from app.rbac import get_current_user, require_roles
from app.schemas import InterviewScheduleCreate, InterviewScheduleOut
from app.services.automation import append_event, run_stage_change_automations
from app.services.candidate_workflow import append_timeline_event as _append_timeline_event
from app.services.candidate_access import can_access_candidate, can_manage_candidate

router = APIRouter(prefix="/api/candidates", tags=["schedules"])


@router.get("/{candidate_id}/schedules", response_model=list[InterviewScheduleOut])
def list_schedules(
    candidate_id: int,
    db: Session = Depends(get_db),
    actor=Depends(require_roles("admin", "recruiter", "interviewer", "hiring_manager")),
):
    candidate = db.get(Candidate, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    if not can_access_candidate(actor, candidate):
        raise HTTPException(status_code=403, detail="Not allowed")

    stmt = (
        select(InterviewSchedule)
        .where(InterviewSchedule.candidate_id == candidate_id)
        .order_by(InterviewSchedule.scheduled_at.desc())
    )
    return list(db.execute(stmt).scalars().all())


@router.post("/{candidate_id}/schedules", response_model=InterviewScheduleOut)
def create_schedule(
    candidate_id: int,
    payload: InterviewScheduleCreate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
    _=Depends(require_roles("admin", "recruiter", "hiring_manager")),
):
    candidate = db.get(Candidate, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    if not can_manage_candidate(user, candidate):
        raise HTTPException(status_code=403, detail="Not allowed")
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", payload.interviewer_email.strip().lower()):
        raise HTTPException(status_code=422, detail="Enter a valid interviewer email")
    application = db.get(Application, payload.application_id) if payload.application_id else None
    if application and application.candidate_id != candidate.id:
        raise HTTPException(status_code=400, detail="Application does not belong to candidate")

    schedule = InterviewSchedule(
        candidate_id=candidate_id,
        application_id=application.id if application else None,
        organizer_user_id=user.id,
        interviewer_email=payload.interviewer_email,
        scheduled_at=payload.scheduled_at,
        duration_minutes=payload.duration_minutes,
        meeting_link=payload.meeting_link,
        notes=payload.notes,
    )
    db.add(schedule)

    _append_timeline_event(
        candidate,
        "schedule",
        f"Interview scheduled at {payload.scheduled_at.isoformat()} with {payload.interviewer_email}",
    )

    # Reuse automation runtime for notification dispatch
    run_stage_change_automations(
        candidate_id=candidate.id,
        candidate_name=candidate.name or f"Candidate #{candidate.id}",
        stage="interview",
        email=candidate.email,
    )

    append_event(
        {
            "timestamp": datetime.utcnow().isoformat(),
            "candidate_id": candidate.id,
            "candidate_name": candidate.name or f"Candidate #{candidate.id}",
            "stage": "interview",
            "rule_id": "schedule-notify",
            "action": {
                "type": "email",
                "to": payload.interviewer_email,
                "subject": f"Interview scheduled: {candidate.name or candidate.id}",
            },
            "result": f"queued_schedule_notification:{payload.interviewer_email}",
        }
    )

    db.commit()
    db.refresh(schedule)
    return schedule
