from datetime import datetime, timezone
import re

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Application, Candidate, InterviewSchedule, EmailSchedule
from app.rbac import get_current_user, require_roles
from app.schemas import InterviewScheduleCreate, InterviewScheduleOut
from app.services.automation import append_event, run_stage_change_automations
from app.services.candidate_workflow import append_timeline_event as _append_timeline_event
from app.services.candidate_access import can_access_candidate, can_manage_candidate

router = APIRouter(prefix="/api/interviews", tags=["interviews"])


def _ics_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


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
    if not can_manage_candidate(user, candidate):
        raise HTTPException(status_code=403, detail="Not allowed to schedule this candidate")
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

    _append_timeline_event(candidate, "schedule", f"Interview scheduled at {payload.scheduled_at.isoformat()} with {payload.interviewer_email}")
    run_stage_change_automations(candidate_id=candidate.id, candidate_name=candidate.name or f"Candidate #{candidate.id}", stage="interview", email=candidate.email)
    append_event({"timestamp": datetime.utcnow().isoformat(), "candidate_id": candidate.id, "candidate_name": candidate.name or f"Candidate #{candidate.id}", "stage": "interview", "rule_id": "schedule-notify", "action": {"type": "email", "to": payload.interviewer_email, "subject": f"Interview scheduled: {candidate.name or candidate.id}"}, "result": f"queued_schedule_notification:{payload.interviewer_email}"})

    if candidate.email:
        db.add(EmailSchedule(
            created_by_user_id=getattr(user, "id", None),
            organization_id=candidate.organization_id,
            candidate_id=candidate.id,
            to_email=candidate.email,
            subject=f"Interview Invitation - {candidate.name or 'Candidate'}",
            body=f"Hello {candidate.name or ''},\n\nYou are invited to interview at {payload.scheduled_at.isoformat()}.\n\nBest regards.",
            send_at=datetime.now(timezone.utc),
            status="scheduled",
        ))

    db.commit()
    db.refresh(schedule)
    return schedule


@router.get("/{schedule_id}/calendar.ics")
def download_interview_calendar(
    schedule_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_roles("admin", "recruiter", "interviewer", "hiring_manager")),
):
    schedule = db.get(InterviewSchedule, schedule_id)
    candidate = db.get(Candidate, schedule.candidate_id) if schedule else None
    if not schedule or not candidate or not can_access_candidate(user, candidate):
        raise HTTPException(status_code=404, detail="Interview not found")
    start = schedule.scheduled_at.strftime("%Y%m%dT%H%M%SZ")
    end = (schedule.scheduled_at + __import__("datetime").timedelta(minutes=schedule.duration_minutes)).strftime("%Y%m%dT%H%M%SZ")
    description = _ics_escape("\n".join(value for value in [schedule.notes or "", schedule.meeting_link or ""] if value))
    body = "\r\n".join([
        "BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Mini ATS//Interview//EN", "BEGIN:VEVENT",
        f"UID:interview-{schedule.id}@mini-ats", f"DTSTAMP:{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}",
        f"DTSTART:{start}", f"DTEND:{end}", f"SUMMARY:{_ics_escape(f'Interview - {candidate.name or candidate.id}')}",
        f"DESCRIPTION:{description}", f"ATTENDEE:mailto:{schedule.interviewer_email}", "END:VEVENT", "END:VCALENDAR", "",
    ])
    return Response(body, media_type="text/calendar", headers={"Content-Disposition": f'attachment; filename="interview-{schedule.id}.ics"'})
