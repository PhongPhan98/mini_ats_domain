import re
import hashlib
import hmac
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Application, Candidate, CandidateFile, Job, PublicApplicationAttempt
from app.services.applications import create_application
from app.services.audit import log_event
from app.services.storage import get_storage_service
from app.services.file_validation import MAX_CV_BYTES, validate_cv_file
from app.config import settings

router = APIRouter(prefix="/api/public/jobs", tags=["public-jobs"])
storage = get_storage_service()
ALLOWED_EXTENSIONS = {".pdf", ".docx"}
ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/octet-stream",
}


def _ip_digest(ip: str) -> str:
    return hmac.new(settings.auth_jwt_secret.encode(), ip.encode(), hashlib.sha256).hexdigest()


def _check_rate_limit(db: Session, ip: str, window_s: int = 60, max_hits: int = 8) -> bool:
    from datetime import timedelta
    digest = _ip_digest(ip)
    cutoff = datetime.utcnow() - timedelta(seconds=window_s)
    db.query(PublicApplicationAttempt).filter(PublicApplicationAttempt.created_at < datetime.utcnow() - timedelta(days=1)).delete(synchronize_session=False)
    count = db.query(PublicApplicationAttempt).filter(PublicApplicationAttempt.ip_hash == digest, PublicApplicationAttempt.created_at >= cutoff).count()
    if count >= max_hits:
        return False
    db.add(PublicApplicationAttempt(ip_hash=digest))
    db.commit()
    return True


def _find_job_by_slug(db: Session, slug: str) -> Job | None:
    job = db.execute(select(Job).where(Job.slug == slug, Job.status == "published", Job.deleted_at.is_(None))).scalar_one_or_none()
    if job and job.closes_at and job.closes_at < datetime.utcnow():
        return None
    return job


def _public_payload(job: Job) -> dict:
    return {
        "id": job.id, "title": job.title, "slug": job.slug, "description": job.description,
        "requirements": job.requirements, "department": job.department, "location": job.location,
        "employment_type": job.employment_type, "salary_min": job.salary_min,
        "salary_max": job.salary_max, "currency": job.currency, "closes_at": job.closes_at,
    }


@router.get("")
def list_public_jobs(db: Session = Depends(get_db)):
    now = datetime.utcnow()
    jobs = list(db.execute(select(Job).where(Job.status == "published", Job.deleted_at.is_(None)).order_by(Job.published_at.desc())).scalars().all())
    return [_public_payload(job) for job in jobs if not job.closes_at or job.closes_at >= now]


@router.get("/{slug}")
def get_public_job(slug: str, db: Session = Depends(get_db)):
    job = _find_job_by_slug(db, slug)
    if not job:
        raise HTTPException(status_code=404, detail="This job is unavailable or closed")
    return _public_payload(job)


@router.post("/{slug}/apply")
async def apply_public_job(
    slug: str,
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(default=""),
    source: str = Form(default="career_site"),
    consent: bool = Form(default=False),
    file: UploadFile | None = File(default=None),
    db: Session = Depends(get_db),
):
    ip = request.client.host if request.client else "unknown"
    if not _check_rate_limit(db, ip):
        raise HTTPException(status_code=429, detail="Too many applications. Please retry later.")
    job = _find_job_by_slug(db, slug)
    if not job:
        raise HTTPException(status_code=404, detail="This job is unavailable or closed")

    clean_name = name.strip()
    clean_email = email.strip().lower()
    if len(clean_name) < 2 or len(clean_name) > 255:
        raise HTTPException(status_code=422, detail="Please enter your full name")
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", clean_email):
        raise HTTPException(status_code=422, detail="Please enter a valid email address")
    if not consent:
        raise HTTPException(status_code=422, detail="Consent is required to process your application")
    source = source.strip().lower()
    if source not in {"career_site", "linkedin", "referral", "job_board", "other"}:
        source = "other"

    content: bytes | None = None
    filename = ""
    if file:
        filename = Path(file.filename or "cv").name
        suffix = Path(filename).suffix.lower()
        if suffix not in ALLOWED_EXTENSIONS or (file.content_type or "application/octet-stream") not in ALLOWED_CONTENT_TYPES:
            raise HTTPException(status_code=415, detail="CV must be a PDF or DOCX file")
        content = await file.read(MAX_CV_BYTES + 1)
        try:
            validate_cv_file(filename, content)
        except OverflowError as exc:
            raise HTTPException(status_code=413, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=415, detail=str(exc)) from exc

    candidate = db.execute(select(Candidate).where(
        Candidate.organization_id == job.organization_id,
        Candidate.email == clean_email,
        Candidate.deleted_at.is_(None),
    )).scalar_one_or_none()
    if not candidate:
        candidate = Candidate(
            organization_id=job.organization_id,
            owner_user_id=job.owner_user_id,
            name=clean_name,
            email=clean_email,
            phone=phone.strip() or None,
            status="applied",
            acquisition_source=source.strip().lower() or "career_site",
            consent_status="granted",
            parsed_json={"source": "public_apply", "owner_user_id": job.owner_user_id, "applied_job_id": job.id},
        )
        db.add(candidate)
        db.flush()
    else:
        candidate.consent_status = "granted"
        candidate.name = candidate.name or clean_name
        candidate.phone = candidate.phone or (phone.strip() or None)

    duplicate = db.execute(select(Application).where(Application.candidate_id == candidate.id, Application.job_id == job.id)).scalar_one_or_none()
    if duplicate:
        raise HTTPException(status_code=409, detail="An application for this email and job already exists")

    application = create_application(db, candidate=candidate, job=job, owner_user_id=job.owner_user_id, source=source)
    if content is not None:
        digest = hashlib.sha256(content).hexdigest()
        existing_file = db.execute(select(CandidateFile).where(CandidateFile.candidate_id == candidate.id, CandidateFile.content_sha256 == digest)).scalar_one_or_none()
        if not existing_file:
            file_url = storage.save_bytes(filename, content) if hasattr(storage, "save_bytes") else await storage.save(file)
            db.add(CandidateFile(candidate_id=candidate.id, file_url=file_url, original_filename=filename, content_sha256=digest, content_type=file.content_type, size_bytes=len(content)))
    db.commit()
    log_event("public", "public_apply.create", f"application:{application.id}", {"organization_id": job.organization_id, "job_id": job.id, "candidate_id": candidate.id, "ip_hash": _ip_digest(ip)})
    return {"ok": True, "candidate_id": candidate.id, "application_id": application.id, "job_id": job.id}
