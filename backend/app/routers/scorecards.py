from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Application, Candidate, InterviewScorecard
from app.rbac import get_current_user, require_roles
from app.schemas import InterviewScorecardCreate, InterviewScorecardOut
from app.services.candidate_workflow import append_timeline_event as _append_timeline_event
from app.services.candidate_access import can_access_candidate

router = APIRouter(prefix="/api/candidates", tags=["scorecards"])


@router.get("/{candidate_id}/scorecards", response_model=list[InterviewScorecardOut])
def list_scorecards(
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
        select(InterviewScorecard)
        .where(InterviewScorecard.candidate_id == candidate_id)
        .order_by(InterviewScorecard.created_at.desc())
    )
    return list(db.execute(stmt).scalars().all())


@router.post("/{candidate_id}/scorecards", response_model=InterviewScorecardOut)
def create_scorecard(
    candidate_id: int,
    payload: InterviewScorecardCreate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
    _=Depends(require_roles("admin", "recruiter", "interviewer", "hiring_manager")),
):
    candidate = db.get(Candidate, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    if not can_access_candidate(user, candidate):
        raise HTTPException(status_code=403, detail="Not allowed")
    if any(int(score) < 1 or int(score) > 5 for score in payload.criteria_scores.values()):
        raise HTTPException(status_code=422, detail="Criteria scores must be between 1 and 5")
    application = db.get(Application, payload.application_id) if payload.application_id else None
    if application and application.candidate_id != candidate.id:
        raise HTTPException(status_code=400, detail="Application does not belong to candidate")

    scorecard = InterviewScorecard(
        candidate_id=candidate_id,
        application_id=application.id if application else None,
        interviewer_user_id=user.id,
        interview_stage=payload.interview_stage,
        criteria_scores=payload.criteria_scores,
        overall_score=payload.overall_score,
        recommendation=payload.recommendation,
        summary=payload.summary,
        submitted_at=datetime.utcnow(),
    )
    db.add(scorecard)

    _append_timeline_event(
        candidate,
        "scorecard",
        f"Scorecard added by {user.full_name} (overall={payload.overall_score or 'n/a'})",
    )

    db.commit()
    db.refresh(scorecard)
    return scorecard
