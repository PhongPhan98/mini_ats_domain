import csv
import io
from datetime import datetime

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Candidate
from app.rbac import require_roles
from app.routers.analytics import summary as analytics_summary

router = APIRouter(prefix="/api/reports", tags=["reports"])


def _normalize_status(value: str | None) -> str:
    if not value:
        return "applied"
    v = value.strip().lower()
    return {"new": "applied", "shortlisted": "screening"}.get(v, v)


@router.get("/candidates.csv")
def export_candidates_csv(
    db: Session = Depends(get_db),
    _=Depends(require_roles("admin", "recruiter", "hiring_manager")),
):
    rows = list(db.execute(select(Candidate)).scalars().all())

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "id",
        "name",
        "email",
        "phone",
        "status",
        "years_of_experience",
        "skills",
        "source",
        "created_at",
    ])

    for c in rows:
        writer.writerow(
            [
                c.id,
                c.name or "",
                c.email or "",
                c.phone or "",
                _normalize_status(c.status),
                c.years_of_experience or "",
                "|".join(c.skills or []),
                (c.parsed_json or {}).get("source", "direct"),
                c.created_at.isoformat() if c.created_at else "",
            ]
        )

    output.seek(0)
    filename = f"mini_ats_candidates_{datetime.utcnow().date().isoformat()}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/analytics.csv")
def export_analytics_csv(
    db: Session = Depends(get_db),
    _=Depends(require_roles("admin", "recruiter", "hiring_manager")),
):
    analytics = analytics_summary(db=db, _=None)

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(["section", "key", "value"])
    writer.writerow(["overview", "total_candidates", analytics.total_candidates])
    writer.writerow(["overview", "hired_count", analytics.hired_count])
    writer.writerow(["overview", "avg_time_to_hire_days", analytics.avg_time_to_hire_days])

    for x in analytics.conversion_rates:
        writer.writerow(["conversion", x["stage"], x["rate_pct"]])
    for x in analytics.source_effectiveness:
        writer.writerow(["source", x["source"], x["count"]])
    for x in analytics.status_distribution:
        writer.writerow(["status", x["status"], x["count"]])

    output.seek(0)
    filename = f"mini_ats_analytics_{datetime.utcnow().date().isoformat()}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/excel-pack")
def export_excel_pack(
    db: Session = Depends(get_db),
    _=Depends(require_roles("admin", "recruiter", "hiring_manager")),
):
    """
    Excel-ready response: client can generate multiple sheets using returned arrays.
    """
    analytics = analytics_summary(db=db, _=None)
    candidates = list(db.execute(select(Candidate)).scalars().all())

    candidate_rows = [
        {
            "id": c.id,
            "name": c.name,
            "email": c.email,
            "phone": c.phone,
            "status": _normalize_status(c.status),
            "years_of_experience": c.years_of_experience,
            "skills": ", ".join(c.skills or []),
            "source": (c.parsed_json or {}).get("source", "direct"),
            "created_at": c.created_at.isoformat() if c.created_at else None,
        }
        for c in candidates
    ]

    return JSONResponse(
        {
            "workbook_name": f"mini_ats_reports_{datetime.utcnow().date().isoformat()}",
            "sheets": {
                "candidates": candidate_rows,
                "status_distribution": analytics.status_distribution,
                "conversion_rates": analytics.conversion_rates,
                "source_effectiveness": analytics.source_effectiveness,
                "top_skills": analytics.top_skills,
                "experience_distribution": analytics.experience_distribution,
            },
        }
    )


@router.get("/pdf-snapshot")
def export_pdf_snapshot_json(
    db: Session = Depends(get_db),
    _=Depends(require_roles("admin", "recruiter", "hiring_manager")),
):
    """
    PDF-ready structured payload (server-side PDF generation can be added later).
    """
    analytics = analytics_summary(db=db, _=None)
    return {
        "title": "Mini ATS Recruitment Report",
        "generated_at": datetime.utcnow().isoformat(),
        "highlights": {
            "total_candidates": analytics.total_candidates,
            "hired_count": analytics.hired_count,
            "avg_time_to_hire_days": analytics.avg_time_to_hire_days,
        },
        "charts": {
            "funnel": analytics.status_distribution,
            "conversion_rates": analytics.conversion_rates,
            "source_effectiveness": analytics.source_effectiveness,
            "top_skills": analytics.top_skills,
        },
    }
