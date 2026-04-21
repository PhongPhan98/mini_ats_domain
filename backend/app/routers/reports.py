import csv
import io
from datetime import datetime

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse, StreamingResponse
from openpyxl import Workbook
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
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


def _candidate_rows(db: Session):
    rows = list(db.execute(select(Candidate)).scalars().all())
    return [
        {
            "id": c.id,
            "name": c.name or "",
            "email": c.email or "",
            "phone": c.phone or "",
            "status": _normalize_status(c.status),
            "years_of_experience": c.years_of_experience or "",
            "skills": ", ".join(c.skills or []),
            "source": (c.parsed_json or {}).get("source", "direct"),
            "created_at": c.created_at.isoformat() if c.created_at else "",
        }
        for c in rows
    ]


@router.get("/candidates.csv")
def export_candidates_csv(
    db: Session = Depends(get_db),
    _=Depends(require_roles("admin", "recruiter", "hiring_manager")),
):
    rows = _candidate_rows(db)

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

    for r in rows:
        writer.writerow(
            [
                r["id"],
                r["name"],
                r["email"],
                r["phone"],
                r["status"],
                r["years_of_experience"],
                r["skills"],
                r["source"],
                r["created_at"],
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
    analytics = analytics_summary(db=db, _=None)
    candidate_rows = _candidate_rows(db)

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


@router.get("/reports.xlsx")
def export_reports_xlsx(
    db: Session = Depends(get_db),
    _=Depends(require_roles("admin", "recruiter", "hiring_manager")),
):
    analytics = analytics_summary(db=db, _=None)
    candidates = _candidate_rows(db)

    wb = Workbook()

    ws = wb.active
    ws.title = "Candidates"
    ws.append(["id", "name", "email", "phone", "status", "years_of_experience", "skills", "source", "created_at"])
    for r in candidates:
        ws.append([
            r["id"],
            r["name"],
            r["email"],
            r["phone"],
            r["status"],
            r["years_of_experience"],
            r["skills"],
            r["source"],
            r["created_at"],
        ])

    ws2 = wb.create_sheet("Summary")
    ws2.append(["metric", "value"])
    ws2.append(["total_candidates", analytics.total_candidates])
    ws2.append(["hired_count", analytics.hired_count])
    ws2.append(["avg_time_to_hire_days", analytics.avg_time_to_hire_days])

    ws3 = wb.create_sheet("Conversions")
    ws3.append(["stage", "rate_pct"])
    for x in analytics.conversion_rates:
        ws3.append([x["stage"], x["rate_pct"]])

    ws4 = wb.create_sheet("Sources")
    ws4.append(["source", "count", "share_pct"])
    for x in analytics.source_effectiveness:
        ws4.append([x["source"], x["count"], x["share_pct"]])

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    filename = f"mini_ats_reports_{datetime.utcnow().date().isoformat()}.xlsx"
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/report.pdf")
def export_report_pdf(
    db: Session = Depends(get_db),
    _=Depends(require_roles("admin", "recruiter", "hiring_manager")),
):
    analytics = analytics_summary(db=db, _=None)

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    width, height = A4

    y = height - 40
    c.setFont("Helvetica-Bold", 16)
    c.drawString(40, y, "Mini ATS Recruitment Report")
    y -= 24
    c.setFont("Helvetica", 10)
    c.drawString(40, y, f"Generated at: {datetime.utcnow().isoformat()} UTC")

    y -= 28
    c.setFont("Helvetica-Bold", 12)
    c.drawString(40, y, "Highlights")
    y -= 18
    c.setFont("Helvetica", 10)
    c.drawString(50, y, f"Total candidates: {analytics.total_candidates}")
    y -= 14
    c.drawString(50, y, f"Hired count: {analytics.hired_count}")
    y -= 14
    c.drawString(50, y, f"Average time-to-hire (days): {analytics.avg_time_to_hire_days}")

    y -= 24
    c.setFont("Helvetica-Bold", 12)
    c.drawString(40, y, "Conversion Rates")
    y -= 18
    c.setFont("Helvetica", 10)
    for row in analytics.conversion_rates:
        c.drawString(50, y, f"{row['stage']}: {row['rate_pct']}%")
        y -= 14
        if y < 60:
            c.showPage()
            y = height - 40

    y -= 12
    c.setFont("Helvetica-Bold", 12)
    c.drawString(40, y, "Source Effectiveness")
    y -= 18
    c.setFont("Helvetica", 10)
    for row in analytics.source_effectiveness[:15]:
        c.drawString(50, y, f"{row['source']}: {row['count']} ({row['share_pct']}%)")
        y -= 14
        if y < 60:
            c.showPage()
            y = height - 40

    c.save()
    buf.seek(0)
    filename = f"mini_ats_report_{datetime.utcnow().date().isoformat()}.pdf"
    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/pdf-snapshot")
def export_pdf_snapshot_json(
    db: Session = Depends(get_db),
    _=Depends(require_roles("admin", "recruiter", "hiring_manager")),
):
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
