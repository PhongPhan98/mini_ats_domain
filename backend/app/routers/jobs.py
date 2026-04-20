from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Candidate, Job
from app.schemas import JobCreate, JobOut, MatchItem, MatchResponse
from app.services.rule_based import match_candidate_rule_based

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.post("", response_model=JobOut)
def create_job(payload: JobCreate, db: Session = Depends(get_db)):
    job = Job(title=payload.title, requirements=payload.requirements)
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


@router.get("", response_model=list[JobOut])
def list_jobs(db: Session = Depends(get_db)):
    stmt = select(Job).order_by(Job.created_at.desc())
    return list(db.execute(stmt).scalars().all())


@router.post("/{job_id}/match", response_model=MatchResponse)
def match_job(job_id: int, db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    candidates = list(db.execute(select(Candidate)).scalars().all())
    results: list[MatchItem] = []

    for candidate in candidates:
        candidate_payload = {
            "name": candidate.name,
            "skills": candidate.skills,
            "years_of_experience": candidate.years_of_experience,
            "education": candidate.education,
            "previous_companies": candidate.previous_companies,
            "summary": candidate.summary,
        }
        matched = match_candidate_rule_based(job.title, job.requirements, candidate_payload)

        results.append(
            MatchItem(
                candidate_id=candidate.id,
                candidate_name=candidate.name,
                match_score=matched["match_score"],
                explanation=matched["explanation"],
            )
        )

    ranked = sorted(results, key=lambda x: x.match_score, reverse=True)
    return MatchResponse(job_id=job.id, job_title=job.title, results=ranked)
