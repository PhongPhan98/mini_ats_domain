import re

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Candidate, CandidateComment, User
from app.rbac import get_current_user, require_roles
from app.schemas import CandidateCommentCreate, CandidateCommentOut

router = APIRouter(prefix="/api/candidates", tags=["comments"])

MENTION_RE = re.compile(r"@([a-zA-Z0-9._-]+)")


def _append_timeline_event(candidate: Candidate, event_type: str, value: str):
    parsed_json = dict(candidate.parsed_json or {})
    timeline = list(parsed_json.get("timeline", []))
    timeline.append(
        {
            "type": event_type,
            "value": value,
            "timestamp": __import__("datetime").datetime.utcnow().isoformat(),
        }
    )
    parsed_json["timeline"] = timeline
    parsed_json["manual_reviewed"] = True
    candidate.parsed_json = parsed_json


@router.get("/{candidate_id}/comments", response_model=list[CandidateCommentOut])
def list_comments(
    candidate_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_roles("admin", "recruiter", "interviewer", "hiring_manager")),
):
    candidate = db.get(Candidate, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    stmt = (
        select(CandidateComment)
        .where(CandidateComment.candidate_id == candidate_id)
        .order_by(CandidateComment.created_at.desc())
    )
    return list(db.execute(stmt).scalars().all())


@router.post("/{candidate_id}/comments", response_model=CandidateCommentOut)
def create_comment(
    candidate_id: int,
    payload: CandidateCommentCreate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    candidate = db.get(Candidate, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    body = (payload.body or "").strip()
    if not body:
        raise HTTPException(status_code=400, detail="Comment body is required")

    mentions_raw = MENTION_RE.findall(body)
    mentions: list[str] = []
    if mentions_raw:
        known_users = list(db.execute(select(User.email, User.full_name)).all())
        name_index = {n.lower(): e for e, n in known_users if n}
        email_local_index = {e.split("@")[0].lower(): e for e, _ in known_users}
        for token in mentions_raw:
            t = token.lower()
            resolved = name_index.get(t) or email_local_index.get(t) or token
            mentions.append(resolved)

    comment = CandidateComment(
        candidate_id=candidate_id,
        author_user_id=user.id,
        body=body,
        mentions=mentions,
    )
    db.add(comment)

    _append_timeline_event(candidate, "comment", f"{user.full_name}: {body}")
    for m in mentions:
        _append_timeline_event(candidate, "mention", f"Mentioned @{m} in comment")

    db.commit()
    db.refresh(comment)
    return comment
