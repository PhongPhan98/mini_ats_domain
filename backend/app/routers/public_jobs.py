import time
from datetime import datetime
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Job, Candidate, CandidateFile
from app.services.storage import LocalStorageService
from app.services.audit import log_event

router = APIRouter(prefix="/api/public/jobs", tags=["public-jobs"])
storage = LocalStorageService()
_RATE_LIMIT: dict[str, list[float]] = {}


def _slug(title: str) -> str:
    return "-".join((title or "job").strip().lower().split())

def _find_job_by_slug(db: Session, slug: str):
    jobs = list(db.execute(select(Job)).scalars().all())
    exact = [j for j in jobs if _slug(j.title) == slug]
    if not exact:
        return None
    exact.sort(key=lambda j: int(j.id), reverse=True)
    return exact[0]

def _check_rate_limit(ip: str, window_s: int = 60, max_hits: int = 8):
    now = time.time()
    arr = [x for x in _RATE_LIMIT.get(ip, []) if now - x < window_s]
    if len(arr) >= max_hits:
        return False
    arr.append(now)
    _RATE_LIMIT[ip] = arr
    return True


@router.get("/{slug}")
def get_public_job(slug: str, db: Session = Depends(get_db)):
    j = _find_job_by_slug(db, slug)
    if j:
        return {"id": j.id, "title": j.title, "requirements": j.requirements, "slug": slug}
    raise HTTPException(status_code=404, detail="Job not found")


@router.post("/{slug}/apply")
async def apply_public_job(
    slug: str,
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(default=""),
    file: UploadFile | None = File(default=None),
    db: Session = Depends(get_db),
):
    ip = (request.client.host if request.client else "unknown")
    if not _check_rate_limit(ip):
        raise HTTPException(status_code=429, detail="Too many applications. Please retry later.")

    job = _find_job_by_slug(db, slug)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    parsed = {
        "source": "public_apply",
        "applied_job_id": job.id,
        "applied_job_title": job.title,
        "timeline": [{"type": "created", "value": "public_application", "timestamp": datetime.utcnow().isoformat()}],
    }
    c = Candidate(name=name, email=email, phone=phone or None, status="applied", parsed_json=parsed)
    db.add(c)
    db.commit()
    db.refresh(c)

    if file is not None:
        content = await file.read()
        if content:
            saved = storage.save(file.filename or "cv.pdf", content)
            db.add(CandidateFile(candidate_id=c.id, file_url=saved["file_url"], file_path=saved["file_path"], original_filename=file.filename or "cv.pdf"))
            db.commit()

    log_event("public", "public_apply.create", f"candidate:{c.id}", {"job_id": job.id, "email": email, "ip": ip})
    return {"ok": True, "candidate_id": c.id, "job_id": job.id}
