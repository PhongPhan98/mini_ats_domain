from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models import Candidate, CandidateFile
from app.schemas import CandidateOut, CandidateUpdate
from app.services.parser import CVTextParser
from app.services.rule_based import SKILL_ALIASES, parse_candidate_from_cv
from app.services.storage import LocalStorageService

router = APIRouter(prefix="/api/candidates", tags=["candidates"])
storage = LocalStorageService()

ALLOWED_STATUSES = {"new", "shortlisted", "interview", "rejected"}


@router.post("/upload", response_model=CandidateOut)
async def upload_cv(file: UploadFile = File(...), db: Session = Depends(get_db)):
    ext = Path(file.filename).suffix.lower()
    if ext not in {".pdf", ".docx"}:
        raise HTTPException(status_code=400, detail="Only PDF/DOCX supported")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file")

    text = CVTextParser.parse(file.filename, content)
    if not text:
        raise HTTPException(status_code=400, detail="Could not extract text from CV")

    parsed = parse_candidate_from_cv(text)

    candidate = Candidate(
        name=parsed.get("name"),
        email=parsed.get("email"),
        phone=parsed.get("phone"),
        status="new",
        skills=parsed.get("skills", []),
        years_of_experience=parsed.get("years_of_experience"),
        education=parsed.get("education", []),
        previous_companies=parsed.get("previous_companies", []),
        summary=parsed.get("summary"),
        parsed_json=parsed,
    )
    db.add(candidate)
    db.flush()

    file_url = storage.save_bytes(file.filename, content)
    candidate_file = CandidateFile(
        candidate_id=candidate.id,
        file_url=file_url,
        original_filename=file.filename,
    )
    db.add(candidate_file)

    db.commit()

    stmt = select(Candidate).options(selectinload(Candidate.files)).where(Candidate.id == candidate.id)
    return db.execute(stmt).scalar_one()


@router.get("", response_model=list[CandidateOut])
def list_candidates(
    skills: list[str] = Query(default=[]),
    min_experience: int | None = Query(default=None),
    keyword: str | None = Query(default=None),
    status: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    conditions: list[Any] = []

    if min_experience is not None:
        conditions.append(Candidate.years_of_experience >= min_experience)

    if keyword:
        kw = f"%{keyword.lower()}%"
        conditions.append(
            or_(
                func.lower(Candidate.name).like(kw),
                func.lower(Candidate.summary).like(kw),
                func.lower(Candidate.email).like(kw),
            )
        )

    if status:
        status = status.lower().strip()
        if status not in ALLOWED_STATUSES:
            raise HTTPException(status_code=400, detail=f"Invalid status '{status}'")
        conditions.append(Candidate.status == status)

    if skills:
        for skill in skills:
            conditions.append(Candidate.skills.contains([skill]))

    stmt = select(Candidate).options(selectinload(Candidate.files)).order_by(Candidate.created_at.desc())
    if conditions:
        stmt = stmt.where(and_(*conditions))

    return list(db.execute(stmt).scalars().all())


@router.get("/skills/catalog")
def get_skill_catalog():
    return {
        "total": len(SKILL_ALIASES),
        "skills": sorted(SKILL_ALIASES.keys()),
        "path": "backend/app/data/skills_vn_en.json",
    }


@router.get("/{candidate_id}", response_model=CandidateOut)
def get_candidate(candidate_id: int, db: Session = Depends(get_db)):
    stmt = select(Candidate).options(selectinload(Candidate.files)).where(Candidate.id == candidate_id)
    candidate = db.execute(stmt).scalar_one_or_none()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return candidate


@router.patch("/{candidate_id}", response_model=CandidateOut)
def update_candidate(candidate_id: int, payload: CandidateUpdate, db: Session = Depends(get_db)):
    candidate = db.get(Candidate, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    update_data = payload.model_dump(exclude_unset=True)

    if "status" in update_data:
        normalized_status = (update_data["status"] or "").strip().lower()
        if normalized_status not in ALLOWED_STATUSES:
            raise HTTPException(status_code=400, detail=f"Invalid status '{normalized_status}'")
        update_data["status"] = normalized_status

    for key, value in update_data.items():
        setattr(candidate, key, value)

    parsed_json = dict(candidate.parsed_json or {})
    parsed_json.update(update_data)
    parsed_json["manual_reviewed"] = True
    candidate.parsed_json = parsed_json

    db.commit()

    stmt = select(Candidate).options(selectinload(Candidate.files)).where(Candidate.id == candidate.id)
    return db.execute(stmt).scalar_one()
