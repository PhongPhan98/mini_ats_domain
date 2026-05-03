from datetime import datetime
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Job, Candidate, CandidateFile
from app.services.storage import LocalStorageService

router = APIRouter(prefix="/api/public/jobs", tags=["public-jobs"])
storage = LocalStorageService()


def _slug(title: str) -> str:
    return "-".join((title or "job").strip().lower().split())


@router.get("/{slug}")
def get_public_job(slug: str, db: Session = Depends(get_db)):
    jobs = list(db.execute(select(Job)).scalars().all())
    for j in jobs:
        if _slug(j.title) == slug:
            return {"id": j.id, "title": j.title, "requirements": j.requirements, "slug": slug}
    raise HTTPException(status_code=404, detail="Job not found")


@router.post("/{slug}/apply")
async def apply_public_job(
    slug: str,
    name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(default=""),
    file: UploadFile | None = File(default=None),
    db: Session = Depends(get_db),
):
    jobs = list(db.execute(select(Job)).scalars().all())
    job = next((j for j in jobs if _slug(j.title) == slug), None)
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

    return {"ok": True, "candidate_id": c.id, "job_id": job.id}
