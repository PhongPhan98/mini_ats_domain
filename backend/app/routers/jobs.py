from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Candidate, Job
from app.rbac import require_roles
from app.schemas import JobCreate, JobOut, MatchItem, MatchResponse
from app.services.llm import llm_match_candidates

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


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
    db: Session = Depends(get_db),
    _=Depends(require_roles("admin", "recruiter", "interviewer", "hiring_manager")),
):
    return list(db.execute(select(Job).order_by(Job.created_at.desc())).scalars().all())


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
    results = llm_match_candidates(job, candidates)

    return MatchResponse(
        job_id=job.id,
        job_title=job.title,
        results=[
            MatchItem(
                candidate_id=r["candidate_id"],
                candidate_name=r.get("candidate_name"),
                match_score=r["match_score"],
                explanation=r["explanation"],
            )
            for r in results
        ],
    )
