from collections import Counter, defaultdict
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Candidate
from app.rbac import get_current_user, require_roles
from app.schemas import AnalyticsSummary

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


def normalize_status(value: str | None) -> str:
    if not value:
        return "applied"
    v = value.strip().lower()
    legacy = {"new": "applied", "shortlisted": "screening"}
    return legacy.get(v, v)


def _candidate_source(candidate: Candidate) -> str:
    source = (candidate.parsed_json or {}).get("source")
    if source:
        return str(source).strip().lower()
    return "direct"


def _first_timeline_ts(candidate: Candidate, event_type: str):
    timeline = (candidate.parsed_json or {}).get("timeline", [])
    for ev in timeline:
        if str(ev.get("type", "")).lower() == event_type:
            ts = ev.get("timestamp")
            if ts:
                try:
                    return datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
                except Exception:
                    pass
    return None


@router.get("/summary", response_model=AnalyticsSummary)
def summary(
    db: Session = Depends(get_db),
    _=Depends(require_roles("admin", "recruiter", "interviewer", "hiring_manager")),
    actor=Depends(get_current_user),
):
    candidates = [c for c in list(db.execute(select(Candidate)).scalars().all()) if not (c.parsed_json or {}).get("deleted")]

    # Personal management mode for recruiters: only candidates they own.
    if getattr(actor, "role", "") == "recruiter":
        owned = []
        for c in candidates:
            parsed = c.parsed_json or {}
            owner_id = parsed.get("owner_user_id")
            owner_email = str(parsed.get("owner_email") or "").lower()
            if (owner_id is not None and int(owner_id) == int(actor.id)) or (owner_email and owner_email == actor.email.lower()):
                owned.append(c)
        candidates = owned

    skill_counter = Counter()
    exp_distribution = Counter()
    status_distribution = Counter()
    source_counter = Counter()
    source_hired_counter = Counter()
    stage_age_days: dict[str, list[float]] = defaultdict(list)

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

        normalized_status = normalize_status(c.status)
        status_distribution[normalized_status] += 1

        source = _candidate_source(c)
        source_counter[source] += 1
        if normalized_status == "hired":
            source_hired_counter[source] += 1

        if c.created_at:
            stage_age_days[normalized_status].append((datetime.utcnow() - c.created_at).total_seconds() / 86400)

    top_skills = [{"skill": k, "count": v} for k, v in skill_counter.most_common(10)]
    experience_distribution = [{"range": k, "count": v} for k, v in exp_distribution.items()]
    status_order = ["applied", "screening", "interview", "offer", "hired", "rejected"]
    status_summary = [{"status": s, "count": status_distribution.get(s, 0)} for s in status_order]

    total = len(candidates) or 1
    source_effectiveness = [
        {"source": s, "count": c, "share_pct": round(c * 100 / total, 2)}
        for s, c in source_counter.most_common()
    ]

    applied = status_distribution.get("applied", 0) or 1
    screening = status_distribution.get("screening", 0)
    interview = status_distribution.get("interview", 0)
    offer = status_distribution.get("offer", 0)
    hired = status_distribution.get("hired", 0)

    conversion_rates = [
        {"stage": "applied_to_screening", "rate_pct": round(screening * 100 / applied, 2)},
        {"stage": "screening_to_interview", "rate_pct": round(interview * 100 / max(screening, 1), 2)},
        {"stage": "interview_to_offer", "rate_pct": round(offer * 100 / max(interview, 1), 2)},
        {"stage": "offer_to_hired", "rate_pct": round(hired * 100 / max(offer, 1), 2)},
    ]

    tth_days = []
    for c in candidates:
        if normalize_status(c.status) != "hired":
            continue
        start = c.created_at
        hired_ts = _first_timeline_ts(c, "status")
        if start and hired_ts:
            tth_days.append((hired_ts - start).total_seconds() / 86400)

    avg_time_to_hire_days = round(sum(tth_days) / len(tth_days), 2) if tth_days else 0.0

    stage_age_summary = [
        {
            "status": s,
            "count": len(stage_age_days.get(s, [])),
            "avg_days_in_stage": round(sum(stage_age_days.get(s, [])) / max(len(stage_age_days.get(s, [])), 1), 2),
        }
        for s in status_order
    ]

    source_hire_effectiveness = [
        {
            "source": s,
            "total": source_counter.get(s, 0),
            "hired": source_hired_counter.get(s, 0),
            "hire_rate_pct": round(source_hired_counter.get(s, 0) * 100 / max(source_counter.get(s, 1), 1), 2),
        }
        for s, _ in source_counter.most_common()
    ]

    now = datetime.utcnow()
    weekly_buckets: dict[str, int] = {}
    for i in range(7, -1, -1):
        week_start = (now - timedelta(days=now.weekday())) - timedelta(weeks=i)
        key = week_start.date().isoformat()
        weekly_buckets[key] = 0

    for c in candidates:
        if normalize_status(c.status) != "hired" or not c.created_at:
            continue
        week_start = (c.created_at - timedelta(days=c.created_at.weekday())).date().isoformat()
        if week_start in weekly_buckets:
            weekly_buckets[week_start] += 1

    hiring_trend = [{"week_start": k, "hired_count": v} for k, v in weekly_buckets.items()]

    return AnalyticsSummary(
        top_skills=top_skills,
        experience_distribution=experience_distribution,
        status_distribution=status_summary,
        source_effectiveness=source_effectiveness,
        conversion_rates=conversion_rates,
        avg_time_to_hire_days=avg_time_to_hire_days,
        hired_count=status_distribution.get("hired", 0),
        total_candidates=len(candidates),
        stage_age_summary=stage_age_summary,
        source_hire_effectiveness=source_hire_effectiveness,
        hiring_trend=hiring_trend,
    )
