from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Candidate, Job
from app.rbac import require_roles
from app.schemas import JobCreate, JobOut, MatchItem, MatchResponse
from app.services.rule_based import match_candidate_rule_based
from app.services.audit import log_event
from pathlib import Path
import json

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


_TRASH_PATH = Path(__file__).resolve().parents[1] / "data" / "jobs_deleted.json"

_SETTINGS_PATH = Path(__file__).resolve().parents[1] / "data" / "jobs_settings.json"


def _load_job_settings() -> dict[str, dict]:
    try:
        data = json.loads(_SETTINGS_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_job_settings(data: dict[str, dict]):
    _SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    _SETTINGS_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")




def _job_owner_meta(job_id: int) -> dict:
    return _load_job_settings().get(str(job_id), {})


def _set_job_owner(job_id: int, user_id: int, email: str):
    settings = _load_job_settings()
    cur = settings.get(str(job_id), {})
    cur["owner_user_id"] = int(user_id)
    cur["owner_email"] = str(email).lower()
    settings[str(job_id)] = cur
    _save_job_settings(settings)


def _can_access_job(user, job_id: int) -> bool:
    if getattr(user, "role", "") != "recruiter":
        return True
    meta = _job_owner_meta(job_id)
    owner_id = meta.get("owner_user_id")
    owner_email = str(meta.get("owner_email") or "").lower()
    return (owner_id is not None and int(owner_id) == int(user.id)) or (owner_email and owner_email == user.email.lower())

def _job_threshold(job_id: int) -> int:
    cfg = _load_job_settings().get(str(job_id), {})
    v = cfg.get("threshold", 50)
    try:
        iv = int(v)
    except Exception:
        iv = 50
    return max(0, min(100, iv))



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
    _actor=Depends(require_roles("admin", "recruiter", "hiring_manager")),
):
    job = Job(title=payload.title, requirements=payload.requirements)
    db.add(job)
    db.commit()
    db.refresh(job)
    _set_job_owner(job.id, _actor.id, _actor.email)
    log_event(_actor.email, "job.create", f"job:{job.id}", {"title": job.title})
    return job


@router.get("", response_model=list[JobOut])
def list_jobs(
    include_deleted: bool = Query(default=False),
    db: Session = Depends(get_db),
    _actor=Depends(require_roles("admin", "recruiter", "interviewer", "hiring_manager")),
):
    jobs = list(db.execute(select(Job).order_by(Job.created_at.desc())).scalars().all())
    deleted = _load_deleted_ids()
    if include_deleted:
        jobs = [j for j in jobs if j.id in deleted]
    else:
        jobs = [j for j in jobs if j.id not in deleted]

    jobs = [j for j in jobs if _can_access_job(_actor, j.id)]
    return jobs


@router.post("/{job_id}/match", response_model=MatchResponse)
def match_candidates(
    job_id: int,
    threshold: int | None = Query(default=None),
    lang: str = Query(default="en"),
    db: Session = Depends(get_db),
    _actor=Depends(require_roles("admin", "recruiter", "hiring_manager")),
):
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if not _can_access_job(_actor, job.id):
        raise HTTPException(status_code=403, detail="Not allowed to access this job")

    candidates = [c for c in list(db.execute(select(Candidate)).scalars().all()) if not (c.parsed_json or {}).get("deleted")]
    min_threshold = max(0, min(100, int(threshold))) if threshold is not None else _job_threshold(job_id)
    results = []
    for c in candidates:
        payload = _to_candidate_payload(c)
        m = match_candidate_rule_based(job.title, job.requirements, payload, lang=lang)
        if m["match_score"] >= min_threshold:
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
    _actor=Depends(require_roles("admin", "recruiter", "hiring_manager")),
):
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if not _can_access_job(_actor, job.id):
        raise HTTPException(status_code=403, detail="Not allowed to update this job")
    job.title = payload.title
    job.requirements = payload.requirements
    db.commit()
    db.refresh(job)
    _set_job_owner(job.id, _actor.id, _actor.email)
    return job


@router.delete("/{job_id}")
def soft_delete_job(
    job_id: int,
    db: Session = Depends(get_db),
    _actor=Depends(require_roles("admin", "recruiter", "hiring_manager")),
):
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if not _can_access_job(_actor, job.id):
        raise HTTPException(status_code=403, detail="Not allowed to delete this job")
    deleted = _load_deleted_ids()
    deleted.add(job_id)
    _save_deleted_ids(deleted)
    log_event(_actor.email, "job.soft_delete", f"job:{job_id}", {})
    return {"ok": True}


@router.post("/{job_id}/restore")
def restore_job(
    job_id: int,
    db: Session = Depends(get_db),
    _actor=Depends(require_roles("admin", "recruiter", "hiring_manager")),
):
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if not _can_access_job(_actor, job.id):
        raise HTTPException(status_code=403, detail="Not allowed to restore this job")
    deleted = _load_deleted_ids()
    if job_id in deleted:
        deleted.remove(job_id)
        _save_deleted_ids(deleted)
    log_event(_actor.email, "job.restore", f"job:{job_id}", {})
    return {"ok": True}


@router.get("/{job_id}/settings")
def get_job_settings(
    job_id: int,
    db: Session = Depends(get_db),
    _actor=Depends(require_roles("admin", "recruiter", "hiring_manager")),
):
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if not _can_access_job(_actor, job.id):
        raise HTTPException(status_code=403, detail="Not allowed to access this job")
    threshold = _job_threshold(job_id)
    return {"job_id": job_id, "threshold": threshold}


@router.patch("/{job_id}/settings")
def update_job_settings(
    job_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    _actor=Depends(require_roles("admin", "recruiter", "hiring_manager")),
):
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if not _can_access_job(_actor, job.id):
        raise HTTPException(status_code=403, detail="Not allowed to update this job")

    threshold = int(payload.get("threshold", 50))
    threshold = max(0, min(100, threshold))

    settings = _load_job_settings()
    cur = settings.get(str(job_id), {})
    cur["threshold"] = threshold
    cur.setdefault("owner_user_id", _job_owner_meta(job_id).get("owner_user_id"))
    cur.setdefault("owner_email", _job_owner_meta(job_id).get("owner_email"))
    settings[str(job_id)] = cur
    _save_job_settings(settings)
    return {"job_id": job_id, "threshold": threshold}
