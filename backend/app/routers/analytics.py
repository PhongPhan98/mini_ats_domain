from collections import Counter

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Candidate
from app.schemas import AnalyticsSummary

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/summary", response_model=AnalyticsSummary)
def summary(db: Session = Depends(get_db)):
    candidates = list(db.execute(select(Candidate)).scalars().all())

    skill_counter = Counter()
    exp_distribution = Counter()
    status_distribution = Counter()

    for c in candidates:
        for skill in c.skills or []:
            if skill:
                skill_counter[skill.strip().lower()] += 1

        bucket = c.years_of_experience or 0
        if bucket < 2:
            exp_distribution["0-1 years"] += 1
        elif bucket < 5:
            exp_distribution["2-4 years"] += 1
        elif bucket < 8:
            exp_distribution["5-7 years"] += 1
        else:
            exp_distribution["8+ years"] += 1

        status_distribution[(c.status or "new").strip().lower()] += 1

    top_skills = [{"skill": k, "count": v} for k, v in skill_counter.most_common(10)]
    experience_distribution = [{"range": k, "count": v} for k, v in exp_distribution.items()]
    status_order = ["new", "shortlisted", "interview", "rejected"]
    status_summary = [{"status": s, "count": status_distribution.get(s, 0)} for s in status_order]

    return AnalyticsSummary(
        top_skills=top_skills,
        experience_distribution=experience_distribution,
        status_distribution=status_summary,
        total_candidates=len(candidates),
    )
