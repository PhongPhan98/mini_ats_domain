from collections import Counter, defaultdict
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Application, ApplicationStageHistory, Candidate
from app.rbac import get_current_user, require_roles
from app.schemas import AnalyticsSummary
from app.services.tenancy import ensure_user_organization

router = APIRouter(prefix="/api/analytics", tags=["analytics"])
STAGES = ["applied", "screening", "interview", "offer", "hired", "rejected"]
FUNNEL = ["applied", "screening", "interview", "offer", "hired"]


def build_summary(db: Session, actor) -> AnalyticsSummary:
    org_id = ensure_user_organization(db, actor)
    stmt = select(Application).where(Application.organization_id == org_id, Application.withdrawn_at.is_(None))
    if actor.role == "recruiter":
        stmt = stmt.where(Application.owner_user_id == actor.id)
    applications = list(db.execute(stmt).scalars().all())

    candidate_stmt = select(Candidate).where(Candidate.organization_id == org_id, Candidate.deleted_at.is_(None))
    if actor.role == "recruiter":
        candidate_stmt = candidate_stmt.where(Candidate.owner_user_id == actor.id)
    candidates = list(db.execute(candidate_stmt).scalars().all())
    skill_counter = Counter(skill.strip().lower() for c in candidates for skill in (c.skills or []) if skill)
    exp_distribution = Counter()
    for candidate in candidates:
        years = candidate.years_of_experience or 0
        exp_distribution["0-1 years" if years < 2 else "2-4 years" if years < 5 else "5-7 years" if years < 8 else "8+ years"] += 1

    status_counter = Counter(app.stage for app in applications)
    source_counter = Counter((app.source or "direct").strip().lower() for app in applications)
    source_hired = Counter((app.source or "direct").strip().lower() for app in applications if app.stage == "hired")

    application_ids = [app.id for app in applications]
    history = list(db.execute(select(ApplicationStageHistory).where(ApplicationStageHistory.application_id.in_(application_ids))).scalars().all()) if application_ids else []
    history_by_application = defaultdict(list)
    for event in history:
        history_by_application[event.application_id].append(event)

    reached = Counter()
    time_to_hire = []
    weekly_hires = Counter()
    for app in applications:
        reached_stages = {"applied", app.stage} | {event.to_stage for event in history_by_application[app.id]}
        for stage in FUNNEL:
            if stage in reached_stages:
                reached[stage] += 1
        hired_events = [event for event in history_by_application[app.id] if event.to_stage == "hired"]
        if hired_events:
            hired_at = min(event.changed_at for event in hired_events)
            time_to_hire.append((hired_at - app.applied_at).total_seconds() / 86400)
            week = (hired_at - timedelta(days=hired_at.weekday())).date().isoformat()
            weekly_hires[week] += 1

    conversion_rates = []
    for previous, current in zip(FUNNEL, FUNNEL[1:]):
        conversion_rates.append({"stage": f"{previous}_to_{current}", "rate_pct": round(reached[current] * 100 / max(reached[previous], 1), 2)})

    now = datetime.utcnow()
    stage_ages = defaultdict(list)
    for app in applications:
        stage_ages[app.stage].append((now - (app.stage_changed_at or app.applied_at)).total_seconds() / 86400)

    weekly_buckets = {}
    for offset in range(7, -1, -1):
        week_start = (now - timedelta(days=now.weekday()) - timedelta(weeks=offset)).date().isoformat()
        weekly_buckets[week_start] = weekly_hires.get(week_start, 0)

    total_applications = len(applications) or 1
    return AnalyticsSummary(
        top_skills=[{"skill": name, "count": count} for name, count in skill_counter.most_common(10)],
        experience_distribution=[{"range": name, "count": count} for name, count in exp_distribution.items()],
        status_distribution=[{"status": stage, "count": status_counter.get(stage, 0)} for stage in STAGES],
        source_effectiveness=[{"source": source, "count": count, "share_pct": round(count * 100 / total_applications, 2)} for source, count in source_counter.most_common()],
        conversion_rates=conversion_rates,
        avg_time_to_hire_days=round(sum(time_to_hire) / len(time_to_hire), 2) if time_to_hire else 0.0,
        hired_count=status_counter.get("hired", 0),
        total_candidates=len(candidates),
        stage_age_summary=[{"status": stage, "count": len(stage_ages[stage]), "avg_days_in_stage": round(sum(stage_ages[stage]) / max(len(stage_ages[stage]), 1), 2)} for stage in STAGES],
        source_hire_effectiveness=[{"source": source, "total": count, "hired": source_hired.get(source, 0), "hire_rate_pct": round(source_hired.get(source, 0) * 100 / max(count, 1), 2)} for source, count in source_counter.most_common()],
        hiring_trend=[{"week_start": week, "hired_count": count} for week, count in weekly_buckets.items()],
        funnel_counts=[{"stage": stage, "count": reached.get(stage, 0)} for stage in FUNNEL],
    )


@router.get("/summary", response_model=AnalyticsSummary)
def summary(
    db: Session = Depends(get_db),
    _role=Depends(require_roles("admin", "recruiter", "interviewer", "hiring_manager")),
    actor=Depends(get_current_user),
):
    return build_summary(db, actor)
