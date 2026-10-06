import re
import hashlib
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Application, Candidate, Job
from app.rbac import require_roles
from app.schemas import JobCreate, JobOut, MatchItem, MatchResponse
from app.services.applications import create_application
from app.services.audit import log_event
from app.services.candidate_access import can_manage_candidate
from app.services.rule_based import match_candidate_rule_based
from app.services.tenancy import ensure_user_organization

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


def _slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "job"


def _unique_slug(db: Session, title: str, job_id: int | None = None) -> str:
    root = _slugify(title)
    slug = root
    suffix = 2
    while True:
        match = db.execute(select(Job).where(Job.slug == slug)).scalar_one_or_none()
        if not match or (job_id is not None and match.id == job_id):
            return slug
        slug = f"{root}-{suffix}"
        suffix += 1


def _can_access_job(user, job_or_id, settings: dict | None = None) -> bool:
    """Compatibility friendly job access check used by routes and older tests."""
    job_id = int(getattr(job_or_id, "id", job_or_id))
    if getattr(user, "role", "") != "recruiter":
        actor_org = getattr(user, "organization_id", None)
        job_org = getattr(job_or_id, "organization_id", actor_org)
        return actor_org is None or job_org is None or int(actor_org) == int(job_org)
    if settings is not None:
        meta = settings.get(str(job_id), {})
        return meta.get("owner_user_id") == getattr(user, "id", None) or str(meta.get("owner_email") or "").lower() == str(getattr(user, "email", "")).lower()
    owner_id = getattr(job_or_id, "owner_user_id", None)
    return owner_id is not None and int(owner_id) == int(getattr(user, "id", 0))


def _require_job(db: Session, job_id: int, actor) -> Job:
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if not _can_access_job(actor, job):
        raise HTTPException(status_code=403, detail="Not allowed to access this job")
    return job


def _apply_payload(job: Job, payload: JobCreate) -> None:
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        if isinstance(value, str):
            value = value.strip()
        setattr(job, key, value)
    if not job.status:
        job.status = "draft"
    if not job.pipeline_stages:
        job.pipeline_stages = ["applied", "screening", "interview", "offer", "hired", "rejected"]
    if job.status == "published" and not job.published_at:
        job.published_at = datetime.utcnow()
    if len(job.title) < 2 or len(job.requirements) < 2:
        raise HTTPException(status_code=422, detail="Job title and requirements are required")
    if job.salary_min is not None and job.salary_max is not None and job.salary_min > job.salary_max:
        raise HTTPException(status_code=422, detail="salary_min cannot be greater than salary_max")
    allowed_stages = {"applied", "screening", "interview", "offer", "hired", "rejected"}
    if not job.pipeline_stages or any(stage not in allowed_stages for stage in job.pipeline_stages):
        raise HTTPException(status_code=422, detail="pipeline_stages contains an unsupported stage")
    job.pipeline_stages = list(dict.fromkeys(job.pipeline_stages))


def _to_candidate_payload(c: Candidate) -> dict:
    parsed = c.parsed_json or {}
    return {
        "name": c.name, "email": c.email, "phone": c.phone, "skills": c.skills or [],
        "years_of_experience": c.years_of_experience, "education": c.education or [],
        "previous_companies": c.previous_companies or [], "summary": c.summary,
        "current_title": parsed.get("current_title"), "projects": parsed.get("projects", []),
        "certifications": parsed.get("certifications", []), "languages": parsed.get("languages", []),
    }


@router.post("", response_model=JobOut)
def create_job(payload: JobCreate, db: Session = Depends(get_db), actor=Depends(require_roles("admin", "recruiter", "hiring_manager"))):
    org_id = ensure_user_organization(db, actor)
    job = Job(organization_id=org_id, owner_user_id=actor.id, title=payload.title, requirements=payload.requirements)
    _apply_payload(job, payload)
    job.slug = _unique_slug(db, job.title)
    db.add(job)
    db.commit()
    db.refresh(job)
    log_event(actor.email, "job.create", f"job:{job.id}", {"title": job.title, "organization_id": org_id})
    return job


@router.get("", response_model=list[JobOut])
def list_jobs(include_deleted: bool = Query(default=False), db: Session = Depends(get_db), actor=Depends(require_roles("admin", "recruiter", "interviewer", "hiring_manager"))):
    org_id = ensure_user_organization(db, actor)
    stmt = select(Job).where(Job.organization_id == org_id)
    stmt = stmt.where(Job.deleted_at.is_not(None) if include_deleted else Job.deleted_at.is_(None))
    jobs = list(db.execute(stmt.order_by(Job.created_at.desc())).scalars().all())
    return [j for j in jobs if _can_access_job(actor, j)]


@router.post("/{job_id}/match", response_model=MatchResponse)
def match_candidates(job_id: int, threshold: int | None = Query(default=None), lang: str = Query(default="en"), db: Session = Depends(get_db), actor=Depends(require_roles("admin", "recruiter", "hiring_manager"))):
    job = _require_job(db, job_id, actor)
    candidates = list(db.execute(select(Candidate).where(Candidate.organization_id == job.organization_id, Candidate.deleted_at.is_(None))).scalars().all())
    candidates = [c for c in candidates if can_manage_candidate(actor, c)]
    minimum = max(0, min(100, int(threshold if threshold is not None else job.match_threshold)))
    results = []
    for candidate in candidates:
        matched = match_candidate_rule_based(job.title, job.requirements, _to_candidate_payload(candidate), lang=lang)
        if matched["match_score"] >= minimum:
            results.append(MatchItem(candidate_id=candidate.id, candidate_name=candidate.name, match_score=matched["match_score"], explanation=matched["explanation"]))
            application = db.execute(select(Application).where(Application.job_id == job.id, Application.candidate_id == candidate.id)).scalar_one_or_none()
            if application:
                application.match_score = matched["match_score"]
                application.match_explanation = matched["explanation"]
                application.match_metadata = {
                    "method": "rule",
                    "provider": "local_rule_engine",
                    "model": "rule-v2",
                    "matched_at": datetime.utcnow().isoformat(),
                    "threshold": minimum,
                    "job_input_sha256": hashlib.sha256(f"{job.title}\n{job.requirements}".encode()).hexdigest(),
                    "human_reviewed": False,
                }
    db.commit()
    results.sort(key=lambda item: item.match_score, reverse=True)
    return MatchResponse(job_id=job.id, job_title=job.title, results=results)


@router.patch("/{job_id}", response_model=JobOut)
def update_job(job_id: int, payload: JobCreate, db: Session = Depends(get_db), actor=Depends(require_roles("admin", "recruiter", "hiring_manager"))):
    job = _require_job(db, job_id, actor)
    _apply_payload(job, payload)
    job.slug = _unique_slug(db, job.title, job.id)
    db.commit()
    db.refresh(job)
    return job


@router.delete("/{job_id}")
def soft_delete_job(job_id: int, db: Session = Depends(get_db), actor=Depends(require_roles("admin", "recruiter", "hiring_manager"))):
    job = _require_job(db, job_id, actor)
    job.deleted_at = datetime.utcnow()
    job.status = "closed"
    db.commit()
    log_event(actor.email, "job.soft_delete", f"job:{job_id}", {})
    return {"ok": True}


@router.post("/{job_id}/restore")
def restore_job(job_id: int, db: Session = Depends(get_db), actor=Depends(require_roles("admin", "recruiter", "hiring_manager"))):
    job = _require_job(db, job_id, actor)
    job.deleted_at = None
    job.status = "draft"
    db.commit()
    return {"ok": True}


@router.get("/{job_id}/settings")
def get_job_settings(job_id: int, db: Session = Depends(get_db), actor=Depends(require_roles("admin", "recruiter", "hiring_manager"))):
    job = _require_job(db, job_id, actor)
    return {"job_id": job_id, "threshold": job.match_threshold}


@router.patch("/{job_id}/settings")
def update_job_settings(job_id: int, payload: dict, db: Session = Depends(get_db), actor=Depends(require_roles("admin", "recruiter", "hiring_manager"))):
    job = _require_job(db, job_id, actor)
    job.match_threshold = max(0, min(100, int(payload.get("threshold", 50))))
    db.commit()
    return {"job_id": job_id, "threshold": job.match_threshold}


@router.post("/{job_id}/applications")
def add_candidate_to_job(job_id: int, payload: dict, db: Session = Depends(get_db), actor=Depends(require_roles("admin", "recruiter", "hiring_manager"))):
    job = _require_job(db, job_id, actor)
    candidate = db.get(Candidate, int(payload.get("candidate_id", 0)))
    if not candidate or candidate.organization_id != job.organization_id or not can_manage_candidate(actor, candidate):
        raise HTTPException(status_code=404, detail="Candidate not found")
    application = create_application(db, candidate=candidate, job=job, owner_user_id=actor.id, source=str(payload.get("source") or candidate.acquisition_source))
    if payload.get("match_score") is not None:
        application.match_score = max(0, min(100, int(payload["match_score"])))
        application.match_explanation = str(payload.get("match_explanation") or "")[:5000] or None
        application.match_metadata = {
            "method": "rule",
            "provider": "local_rule_engine",
            "model": "rule-v2",
            "matched_at": datetime.utcnow().isoformat(),
            "job_input_sha256": hashlib.sha256(f"{job.title}\n{job.requirements}".encode()).hexdigest(),
            "human_reviewed": True,
            "reviewed_by_user_id": actor.id,
        }
    db.commit()
    db.refresh(application)
    return {"id": application.id, "candidate_id": candidate.id, "job_id": job.id, "stage": application.stage}


@router.get("/{job_id}/candidates")
def list_job_candidates(job_id: int, db: Session = Depends(get_db), actor=Depends(require_roles("admin", "recruiter", "hiring_manager", "interviewer"))):
    job = _require_job(db, job_id, actor)
    rows = db.execute(select(Application, Candidate).join(Candidate, Candidate.id == Application.candidate_id).where(Application.job_id == job.id)).all()
    return {"job_id": job_id, "candidates": [
        {"id": c.id, "application_id": app.id, "name": c.name, "status": app.stage, "email": c.email, "source": app.source, "match_score": app.match_score, "applied_at": app.applied_at, "stage_changed_at": app.stage_changed_at}
        for app, c in rows if c.deleted_at is None
    ]}
