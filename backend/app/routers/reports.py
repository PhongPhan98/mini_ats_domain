import csv
import io
import smtplib
from datetime import datetime
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from openpyxl import Workbook
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import Candidate, ReportSchedule
from app.rbac import require_roles
from app.routers.analytics import build_summary
from app.services.tenancy import ensure_user_organization

router = APIRouter(prefix="/api/reports", tags=["reports"])


def _candidate_rows(db: Session, actor):
    org_id = ensure_user_organization(db, actor)
    stmt = select(Candidate).where(Candidate.organization_id == org_id, Candidate.deleted_at.is_(None))
    if actor.role == "recruiter":
        stmt = stmt.where(Candidate.owner_user_id == actor.id)
    rows = list(db.execute(stmt.order_by(Candidate.created_at.desc())).scalars().all())
    return [{
        "id": item.id, "name": item.name or "", "email": item.email or "", "phone": item.phone or "",
        "status": item.status, "years_of_experience": item.years_of_experience or "",
        "skills": ", ".join(item.skills or []), "source": item.acquisition_source,
        "consent_status": item.consent_status, "created_at": item.created_at.isoformat() if item.created_at else "",
    } for item in rows]


def _build_xlsx_bytes(db: Session, actor) -> bytes:
    analytics = build_summary(db, actor)
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Candidates"
    columns = ["id", "name", "email", "phone", "status", "years_of_experience", "skills", "source", "consent_status", "created_at"]
    sheet.append(columns)
    for row in _candidate_rows(db, actor):
        sheet.append([row[column] for column in columns])
    summary = workbook.create_sheet("Summary")
    summary.append(["metric", "value"])
    summary.append(["total_candidates", analytics.total_candidates])
    summary.append(["hired_count", analytics.hired_count])
    summary.append(["avg_time_to_hire_days", analytics.avg_time_to_hire_days])
    conversions = workbook.create_sheet("Conversions")
    conversions.append(["stage", "rate_pct"])
    for item in analytics.conversion_rates:
        conversions.append([item["stage"], item["rate_pct"]])
    output = io.BytesIO()
    workbook.save(output)
    return output.getvalue()


def _build_pdf_bytes(db: Session, actor) -> bytes:
    analytics = build_summary(db, actor)
    output = io.BytesIO()
    document = canvas.Canvas(output, pagesize=A4)
    _, height = A4
    y = height - 40
    document.setFont("Helvetica-Bold", 16)
    document.drawString(40, y, "Mini ATS Recruitment Report")
    document.setFont("Helvetica", 10)
    for text in [
        f"Generated: {datetime.utcnow().isoformat()} UTC",
        f"Candidates: {analytics.total_candidates}",
        f"Hired: {analytics.hired_count}",
        f"Average time to hire: {analytics.avg_time_to_hire_days} days",
    ]:
        y -= 20
        document.drawString(40, y, text)
    y -= 20
    document.setFont("Helvetica-Bold", 12)
    document.drawString(40, y, "Conversion rates")
    document.setFont("Helvetica", 10)
    for item in analytics.conversion_rates:
        y -= 16
        document.drawString(50, y, f"{item['stage']}: {item['rate_pct']}%")
    document.save()
    return output.getvalue()


def _send_email(to_email: str, attachments: list[tuple[str, bytes, str]]) -> tuple[bool, str]:
    if not settings.smtp_enabled or not settings.smtp_host or not settings.smtp_from_email:
        return False, "smtp_not_configured"
    message = MIMEMultipart()
    message["Subject"] = "Mini ATS Recruitment Report"
    message["From"] = settings.smtp_from_email
    message["To"] = to_email
    message.attach(MIMEText("Your requested ATS report is attached.", "plain", "utf-8"))
    for filename, data, subtype in attachments:
        part = MIMEApplication(data, _subtype=subtype)
        part.add_header("Content-Disposition", "attachment", filename=filename)
        message.attach(part)
    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=12) as server:
            if settings.smtp_use_tls:
                server.starttls()
            if settings.smtp_username:
                server.login(settings.smtp_username, settings.smtp_password)
            server.sendmail(settings.smtp_from_email, [to_email], message.as_string())
        return True, "email_sent"
    except Exception as exc:
        return False, f"email_error:{exc}"


def _actor_dependency():
    return require_roles("admin", "recruiter", "hiring_manager")


@router.get("/candidates.csv")
def export_candidates_csv(db: Session = Depends(get_db), actor=Depends(_actor_dependency())):
    rows = _candidate_rows(db, actor)
    output = io.StringIO()
    columns = ["id", "name", "email", "phone", "status", "years_of_experience", "skills", "source", "consent_status", "created_at"]
    writer = csv.DictWriter(output, fieldnames=columns)
    writer.writeheader()
    writer.writerows(rows)
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv", headers={"Content-Disposition": f"attachment; filename=ats_candidates_{datetime.utcnow().date()}.csv"})


@router.get("/analytics.csv")
def export_analytics_csv(db: Session = Depends(get_db), actor=Depends(_actor_dependency())):
    analytics = build_summary(db, actor)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["section", "key", "value"])
    writer.writerow(["overview", "total_candidates", analytics.total_candidates])
    writer.writerow(["overview", "hired_count", analytics.hired_count])
    writer.writerow(["overview", "avg_time_to_hire_days", analytics.avg_time_to_hire_days])
    for item in analytics.conversion_rates:
        writer.writerow(["conversion", item["stage"], item["rate_pct"]])
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv", headers={"Content-Disposition": f"attachment; filename=ats_analytics_{datetime.utcnow().date()}.csv"})


@router.get("/reports.xlsx")
def export_reports_xlsx(db: Session = Depends(get_db), actor=Depends(_actor_dependency())):
    return StreamingResponse(io.BytesIO(_build_xlsx_bytes(db, actor)), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": f"attachment; filename=ats_report_{datetime.utcnow().date()}.xlsx"})


@router.get("/report.pdf")
def export_report_pdf(db: Session = Depends(get_db), actor=Depends(_actor_dependency())):
    return StreamingResponse(io.BytesIO(_build_pdf_bytes(db, actor)), media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename=ats_report_{datetime.utcnow().date()}.pdf"})


@router.get("/pdf-snapshot")
def export_pdf_snapshot_json(db: Session = Depends(get_db), actor=Depends(_actor_dependency())):
    analytics = build_summary(db, actor)
    return JSONResponse({"generated_at": datetime.utcnow().isoformat(), "summary": analytics.model_dump()})


@router.get("/schedules")
def list_report_schedules(db: Session = Depends(get_db), actor=Depends(require_roles("admin", "hiring_manager"))):
    org_id = ensure_user_organization(db, actor)
    rows = list(db.execute(select(ReportSchedule).where(ReportSchedule.organization_id == org_id).order_by(ReportSchedule.created_at.desc())).scalars().all())
    return {"schedules": [{"id": row.id, "name": row.name, "cadence": row.cadence, "formats": row.formats, "delivery": row.delivery, "enabled": row.enabled} for row in rows]}


@router.post("/schedules")
def upsert_report_schedule(payload: dict, db: Session = Depends(get_db), actor=Depends(require_roles("admin", "hiring_manager"))):
    org_id = ensure_user_organization(db, actor)
    schedule_id = payload.get("id")
    schedule = db.get(ReportSchedule, int(schedule_id)) if schedule_id else None
    if schedule and schedule.organization_id != org_id:
        raise HTTPException(status_code=404, detail="Schedule not found")
    if not schedule:
        schedule = ReportSchedule(organization_id=org_id, created_by_user_id=actor.id)
        db.add(schedule)
    schedule.name = str(payload.get("name") or "Recruitment report")[:255]
    schedule.cadence = str(payload.get("cadence") or "weekly")[:32]
    schedule.formats = [value for value in payload.get("formats", ["pdf"]) if value in {"pdf", "xlsx"}]
    schedule.delivery = payload.get("delivery") if isinstance(payload.get("delivery"), dict) else {}
    schedule.enabled = bool(payload.get("enabled", True))
    db.commit()
    db.refresh(schedule)
    return {"ok": True, "schedule_id": schedule.id}


@router.post("/schedules/{schedule_id}/run")
def run_report_schedule(schedule_id: int, db: Session = Depends(get_db), actor=Depends(require_roles("admin", "hiring_manager"))):
    org_id = ensure_user_organization(db, actor)
    schedule = db.get(ReportSchedule, schedule_id)
    if not schedule or schedule.organization_id != org_id:
        raise HTTPException(status_code=404, detail="Schedule not found")
    attachments = []
    if "pdf" in schedule.formats:
        attachments.append(("report.pdf", _build_pdf_bytes(db, actor), "pdf"))
    if "xlsx" in schedule.formats:
        attachments.append(("report.xlsx", _build_xlsx_bytes(db, actor), "vnd.openxmlformats-officedocument.spreadsheetml.sheet"))
    delivery = schedule.delivery or {}
    if delivery.get("mode", "email") == "email":
        if not delivery.get("to"):
            raise HTTPException(status_code=400, detail="Missing delivery email")
        ok, result = _send_email(str(delivery["to"]), attachments)
        return {"ok": ok, "result": result, "schedule_id": schedule.id}
    raise HTTPException(status_code=400, detail="Only email delivery is supported")
