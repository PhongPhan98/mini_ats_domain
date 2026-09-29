from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Application, ApplicationStageHistory, Candidate, CandidateTimeline, Job
from app.services.candidate_workflow import normalize_candidate_status

ALLOWED_STAGES = {"applied", "screening", "interview", "offer", "hired", "rejected"}


def create_application(
    db: Session,
    *,
    candidate: Candidate,
    job: Job,
    owner_user_id: int | None,
    source: str = "direct",
) -> Application:
    existing = db.execute(
        select(Application).where(Application.candidate_id == candidate.id, Application.job_id == job.id)
    ).scalar_one_or_none()
    if existing:
        return existing
    application = Application(
        organization_id=job.organization_id or candidate.organization_id,
        candidate_id=candidate.id,
        job_id=job.id,
        owner_user_id=owner_user_id,
        stage="applied",
        source=(source or "direct").strip().lower()[:80],
    )
    db.add(application)
    db.flush()
    db.add(ApplicationStageHistory(application_id=application.id, from_stage=None, to_stage="applied", changed_by_user_id=owner_user_id))
    db.add(CandidateTimeline(candidate_id=candidate.id, actor_user_id=owner_user_id, event_type="application", value=f"applied_to_job:{job.id}", metadata_json={"application_id": application.id, "job_id": job.id}))
    return application


def change_application_stage(
    db: Session,
    application: Application,
    stage: str,
    *,
    actor_user_id: int | None,
    note: str | None = None,
    rejection_reason: str | None = None,
) -> Application:
    stage = normalize_candidate_status(stage)
    if stage not in ALLOWED_STAGES:
        raise HTTPException(status_code=400, detail=f"Invalid stage '{stage}'")
    old_stage = application.stage
    if stage == old_stage:
        return application
    application.stage = stage
    application.stage_changed_at = datetime.utcnow()
    if stage == "rejected":
        application.rejection_reason = (rejection_reason or note or "").strip() or None
    db.add(ApplicationStageHistory(
        application_id=application.id,
        from_stage=old_stage,
        to_stage=stage,
        changed_by_user_id=actor_user_id,
        note=(note or "").strip() or None,
    ))
    # Keep the old candidate status meaningful for screens that do not select a job.
    candidate = db.get(Candidate, application.candidate_id)
    if candidate:
        candidate.status = stage
        db.add(CandidateTimeline(
            candidate_id=candidate.id,
            actor_user_id=actor_user_id,
            event_type="status",
            value=f"application:{application.id}:{stage}",
            metadata_json={"application_id": application.id, "job_id": application.job_id, "from_stage": old_stage, "to_stage": stage},
        ))
    return application
