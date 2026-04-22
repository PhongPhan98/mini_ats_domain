from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Candidate, Job
from app.rbac import require_roles
from app.schemas import JobCreate, JobOut, MatchItem, MatchResponse
from app.services.rule_based import match_candidate_rule_based
from pathlib import Path
import json

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


_TRASH_PATH = Path(__file__).resolve().parents[1] / "data" / "jobs_deleted.json"


def _load_deleted_ids() -> set[int]:
    try:
        data = json.loads(_TRASH_PATH.read_text(encoding="utf-8"))
        return {int(x) for x in (data or [])}
    except Exception:
        return set()


def _save_deleted_ids(ids: set[int]):
    _TRASH_PATH.parent.mkdir(parents=True, exist_ok=True)
    _TRASH_PATH.write_text(json.dumps(sorted(list(ids))), encoding="utf-8")


def _to_candidate_payload(c: Candidate) -> dict:
    parsed = c.parsed_json or {}
    return {
        "name": c.name,
        "email": c.email,
        "phone": c.phone,
        "skills": c.skills or [],
        "years_of_experience": c.years_of_experience,
        "education": c.education or [],
        "previous_companies": c.previous_companies or [],
        "summary": c.summary,
        "current_title": parsed.get("current_title"),
        "projects": parsed.get("projects", []),
        "certifications": parsed.get("certifications", []),
        "languages": parsed.get("languages", []),
    }


@router.post("", response_model=JobOut)
def create_job(
    payload: JobCreate,
    db: Session = Depends(get_db),
    _=Depends(require_roles("admin", "recruiter", "hiring_manager")),
):
    job = Job(title=payload.title, requirements=payload.requirements)
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


@router.get("", response_model=list[JobOut])
def list_jobs(
    include_deleted: bool = Query(default=False),
    db: Session = Depends(get_db),
    _=Depends(require_roles("admin", "recruiter", "interviewer", "hiring_manager")),
):
    jobs = list(db.execute(select(Job).order_by(Job.created_at.desc())).scalars().all())
    deleted = _load_deleted_ids()
    if include_deleted:
        return [j for j in jobs if j.id in deleted]
    return [j for j in jobs if j.id not in deleted]


@router.post("/{job_id}/match", response_model=MatchResponse)
def match_candidates(
    job_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_roles("admin", "recruiter", "hiring_manager")),
):
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    candidates = list(db.execute(select(Candidate)).scalars().all())
    results = []
    for c in candidates:
        payload = _to_candidate_payload(c)
        m = match_candidate_rule_based(job.title, job.requirements, payload)
        if m["match_score"] >= 50:
            results.append(
                MatchItem(
                    candidate_id=c.id,
                    candidate_name=c.name,
                    match_score=m["match_score"],
                    explanation=m["explanation"],
                )
            )

    results.sort(key=lambda x: x.match_score, reverse=True)

    return MatchResponse(
        job_id=job.id,
        job_title=job.title,
        results=results,
    )


@router.patch("/{job_id}", response_model=JobOut)
def update_job(
    job_id: int,
    payload: JobCreate,
    db: Session = Depends(get_db),
    _=Depends(require_roles("admin", "recruiter", "hiring_manager")),
):
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    job.title = payload.title
    job.requirements = payload.requirements
    db.commit()
    db.refresh(job)
    return job


@router.delete("/{job_id}")
def soft_delete_job(
    job_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_roles("admin", "recruiter", "hiring_manager")),
):
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    deleted = _load_deleted_ids()
    deleted.add(job_id)
    _save_deleted_ids(deleted)
    return {"ok": True}


@router.post("/{job_id}/restore")
def restore_job(
    job_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_roles("admin", "recruiter", "hiring_manager")),
):
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    deleted = _load_deleted_ids()
    if job_id in deleted:
        deleted.remove(job_id)
        _save_deleted_ids(deleted)
    return {"ok": True}
