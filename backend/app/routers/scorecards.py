from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Candidate, InterviewScorecard
from app.rbac import get_current_user, require_roles
from app.schemas import InterviewScorecardCreate, InterviewScorecardOut

router = APIRouter(prefix="/api/candidates", tags=["scorecards"])


def _append_timeline_event(candidate: Candidate, event_type: str, value: str):
    parsed_json = dict(candidate.parsed_json or {})
    timeline = list(parsed_json.get("timeline", []))
    timeline.append(
        {
            "type": event_type,
            "value": value,
            "timestamp": datetime.utcnow().isoformat(),
        }
    )
    parsed_json["timeline"] = timeline
    parsed_json["manual_reviewed"] = True
    candidate.parsed_json = parsed_json


@router.get("/{candidate_id}/scorecards", response_model=list[InterviewScorecardOut])
def list_scorecards(
    candidate_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_roles("admin", "recruiter", "interviewer", "hiring_manager")),
):
    candidate = db.get(Candidate, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

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
    _=Depends(require_roles("admin", "interviewer", "hiring_manager")),
):
    candidate = db.get(Candidate, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    scorecard = InterviewScorecard(
        candidate_id=candidate_id,
        interviewer_user_id=user.id,
        interview_stage=payload.interview_stage,
        criteria_scores=payload.criteria_scores,
        overall_score=payload.overall_score,
        recommendation=payload.recommendation,
        summary=payload.summary,
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
