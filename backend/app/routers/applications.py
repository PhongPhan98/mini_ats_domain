from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Application, Candidate, Job
from app.rbac import require_roles
from app.schemas import ApplicationOut, ApplicationStageUpdate
from app.services.applications import change_application_stage
from app.services.audit import log_event
from app.services.automation import run_stage_change_automations
from app.services.tenancy import ensure_user_organization

router = APIRouter(prefix="/api/applications", tags=["applications"])


def _get_application(db: Session, application_id: int, actor) -> Application:
    application = db.get(Application, application_id)
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    org_id = ensure_user_organization(db, actor)
    if application.organization_id != org_id:
        raise HTTPException(status_code=404, detail="Application not found")
    if actor.role == "recruiter" and application.owner_user_id != actor.id:
        raise HTTPException(status_code=403, detail="Not allowed to manage this application")
    return application


@router.get("", response_model=list[ApplicationOut])
def list_applications(
    job_id: int | None = Query(default=None),
    candidate_id: int | None = Query(default=None),
    stage: str | None = Query(default=None),
    db: Session = Depends(get_db),
    actor=Depends(require_roles("admin", "recruiter", "interviewer", "hiring_manager")),
):
    org_id = ensure_user_organization(db, actor)
    stmt = select(Application).where(Application.organization_id == org_id)
    if actor.role == "recruiter":
        stmt = stmt.where(Application.owner_user_id == actor.id)
    if job_id:
        stmt = stmt.where(Application.job_id == job_id)
    if candidate_id:
        stmt = stmt.where(Application.candidate_id == candidate_id)
    if stage:
        stmt = stmt.where(Application.stage == stage)
    return list(db.execute(stmt.order_by(Application.applied_at.desc())).scalars().all())


@router.patch("/{application_id}/stage", response_model=ApplicationOut)
def update_application_stage(
    application_id: int,
    payload: ApplicationStageUpdate,
    db: Session = Depends(get_db),
    actor=Depends(require_roles("admin", "recruiter", "hiring_manager")),
):
    application = _get_application(db, application_id, actor)
    change_application_stage(db, application, payload.stage, actor_user_id=actor.id, note=payload.note, rejection_reason=payload.rejection_reason)
    candidate = db.get(Candidate, application.candidate_id)
    run_stage_change_automations(
        candidate_id=application.candidate_id,
        candidate_name=(candidate.name if candidate else None) or f"Candidate #{application.candidate_id}",
        stage=application.stage,
        email=candidate.email if candidate else None,
        owner_key=actor.email if actor.role == "recruiter" else "*",
    )
    db.commit()
    db.refresh(application)
    log_event(actor.email, "application.stage.update", f"application:{application.id}", {"stage": application.stage, "job_id": application.job_id})
    return application


@router.post("/{application_id}/withdraw", response_model=ApplicationOut)
def withdraw_application(application_id: int, db: Session = Depends(get_db), actor=Depends(require_roles("admin", "recruiter", "hiring_manager"))):
    application = _get_application(db, application_id, actor)
    application.withdrawn_at = datetime.utcnow()
    db.commit()
    db.refresh(application)
    return application


@router.patch("/{application_id}/match-review", response_model=ApplicationOut)
def review_match(application_id: int, payload: dict, db: Session = Depends(get_db), actor=Depends(require_roles("admin", "recruiter", "hiring_manager"))):
    application = _get_application(db, application_id, actor)
    metadata = dict(application.match_metadata or {})
    metadata.update({
        "human_reviewed": True,
        "reviewed_by_user_id": actor.id,
        "reviewed_at": datetime.utcnow().isoformat(),
        "overridden": bool(payload.get("overridden", False)),
        "review_note": str(payload.get("note") or "")[:1000],
    })
    application.match_metadata = metadata
    db.commit()
    db.refresh(application)
    return application
