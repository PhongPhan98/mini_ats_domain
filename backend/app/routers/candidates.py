from datetime import datetime
from pathlib import Path
from typing import Any
import json

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models import Candidate, CandidateFile
from app.rbac import require_roles
from app.schemas import CandidateOut, CandidateUpdate
from app.services.automation import run_stage_change_automations
from app.services.parser import CVTextParser
from app.services.rule_based import SKILL_ALIASES, parse_candidate_from_cv
from app.services.storage import LocalStorageService
from app.services.audit import log_event

router = APIRouter(prefix="/api/candidates", tags=["candidates"])
storage = LocalStorageService()

ALLOWED_STATUSES = {"applied", "screening", "interview", "offer", "hired", "rejected"}


def normalize_status(value: str | None) -> str:
    if not value:
        return "applied"
    value = value.strip().lower()
    legacy_map = {
        "new": "applied",
        "shortlisted": "screening",
    }
    return legacy_map.get(value, value)




def _parse_or_fallback(filename: str, content: bytes) -> dict[str, Any]:
    text = CVTextParser.parse(filename, content)
    if not text:
        fallback_name = Path(filename).stem.replace("_", " ").replace("-", " ").strip() or "Unknown Candidate"
        return {
            "name": fallback_name,
            "summary": "Imported with limited parsing (manual review needed).",
            "skills": [],
            "education": [],
            "previous_companies": [],
            "parse_warning": "Could not extract text from CV file",
            "confidence": {},
            "confidence_score": 0,
            "source": "fallback",
        }
    return parse_candidate_from_cv(text)


@router.post("/parse")
async def parse_cv_preview(
    file: UploadFile = File(...),
    _actor=Depends(require_roles("admin", "recruiter", "hiring_manager")),
):
    ext = Path(file.filename).suffix.lower()
    if ext not in {".pdf", ".docx"}:
        raise HTTPException(status_code=400, detail="Only PDF/DOCX supported")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file")

    parsed = _parse_or_fallback(file.filename, content)
    parsed["owner_user_id"] = _actor.id
    parsed["owner_email"] = _actor.email
    return {"filename": file.filename, "parsed": parsed}



def _can_access_candidate(user, candidate: Candidate) -> bool:
    # recruiter can only access candidates they uploaded/own
    if getattr(user, "role", "") != "recruiter":
        return True
    parsed = candidate.parsed_json or {}
    owner_id = parsed.get("owner_user_id")
    owner_email = (parsed.get("owner_email") or "").lower()
    return (owner_id is not None and int(owner_id) == int(user.id)) or (owner_email and owner_email == user.email.lower())

def _is_candidate_deleted(candidate: Candidate) -> bool:
    parsed = candidate.parsed_json or {}
    return bool(parsed.get("deleted"))


def _append_timeline_event(candidate: Candidate, event_type: str, value: str):
    parsed_json = dict(candidate.parsed_json or {})
    timeline = list(parsed_json.get("timeline", []))
    timeline.append(
        {
            "type": event_type,
            "value": value,
            "timestamp": datetime.utcnow().isoformat(),
        }
    )
    parsed_json["timeline"] = timeline
    parsed_json["manual_reviewed"] = True
    candidate.parsed_json = parsed_json


@router.post("/upload", response_model=CandidateOut)
async def upload_cv(
    file: UploadFile = File(...),
    edited_json: str | None = Form(default=None),
    db: Session = Depends(get_db),
    _actor=Depends(require_roles("admin", "recruiter", "hiring_manager")),
):
    ext = Path(file.filename).suffix.lower()
    if ext not in {".pdf", ".docx"}:
        raise HTTPException(status_code=400, detail="Only PDF/DOCX supported")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file")

    parsed = _parse_or_fallback(file.filename, content)

    if edited_json:
        try:
            edited = json.loads(edited_json)
            if isinstance(edited, dict):
                for k, v in edited.items():
                    parsed[k] = v
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid edited_json")

    candidate = Candidate(
        name=parsed.get("name"),
        email=parsed.get("email"),
        phone=parsed.get("phone"),
        status="applied",
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

    _append_timeline_event(candidate, "created", "Candidate profile created")

    db.commit()

    stmt = select(Candidate).options(selectinload(Candidate.files)).where(Candidate.id == candidate.id)
    return db.execute(stmt).scalar_one()


@router.get("", response_model=list[CandidateOut])
def list_candidates(
    skills: list[str] = Query(default=[]),
    min_experience: int | None = Query(default=None),
    keyword: str | None = Query(default=None),
    status: str | None = Query(default=None),
    include_deleted: bool = Query(default=False),
    db: Session = Depends(get_db),
    _actor=Depends(require_roles("admin", "recruiter", "interviewer", "hiring_manager")),
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
        status = normalize_status(status)
        if status not in ALLOWED_STATUSES:
            raise HTTPException(status_code=400, detail=f"Invalid status '{status}'")
        conditions.append(Candidate.status == status)

    if skills:
        for skill in skills:
            conditions.append(Candidate.skills.contains([skill]))

    stmt = select(Candidate).options(selectinload(Candidate.files)).order_by(Candidate.created_at.desc())
    if conditions:
        stmt = stmt.where(and_(*conditions))

    result = list(db.execute(stmt).scalars().all())
    if not include_deleted:
        result = [c for c in result if not _is_candidate_deleted(c)]
    else:
        result = [c for c in result if _is_candidate_deleted(c)]

    result = [c for c in result if _can_access_candidate(_actor, c)]

    changed = False
    for c in result:
        normalized = normalize_status(c.status)
        if normalized != (c.status or ""):
            c.status = normalized
            changed = True
    if changed:
        db.commit()

    return result


@router.get("/skills/catalog")
def get_skill_catalog():
    return {
        "total": len(SKILL_ALIASES),
        "skills": sorted(SKILL_ALIASES.keys()),
        "path": "backend/app/data/skills_vn_en.json",
    }


@router.get("/{candidate_id}", response_model=CandidateOut)
def get_candidate(
    candidate_id: int,
    db: Session = Depends(get_db),
    _actor=Depends(require_roles("admin", "recruiter", "interviewer", "hiring_manager")),
):
    stmt = select(Candidate).options(selectinload(Candidate.files)).where(Candidate.id == candidate_id)
    candidate = db.execute(stmt).scalar_one_or_none()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    if not _can_access_candidate(_actor, candidate):
        raise HTTPException(status_code=403, detail="Not allowed to access this candidate")

    candidate.status = normalize_status(candidate.status)
    db.commit()
    return candidate


@router.patch("/{candidate_id}", response_model=CandidateOut)
def update_candidate(
    candidate_id: int,
    payload: CandidateUpdate,
    db: Session = Depends(get_db),
    _actor=Depends(require_roles("admin", "recruiter", "hiring_manager")),
):
    candidate = db.get(Candidate, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    if not _can_access_candidate(_actor, candidate):
        raise HTTPException(status_code=403, detail="Not allowed to update this candidate")

    update_data = payload.model_dump(exclude_unset=True)

    note_text = None
    if "notes" in update_data:
        note_text = (update_data.pop("notes") or "").strip() or None

    if "status" in update_data:
        normalized_status = normalize_status(update_data["status"])
        if normalized_status not in ALLOWED_STATUSES:
            raise HTTPException(status_code=400, detail=f"Invalid status '{normalized_status}'")
        if normalized_status != normalize_status(candidate.status):
            _append_timeline_event(candidate, "status", normalized_status)
            _append_timeline_event(candidate, "automation", f"auto_action:notify_on_stage_change:{normalized_status}")
            run_stage_change_automations(
                candidate_id=candidate.id,
                candidate_name=candidate.name or f"Candidate #{candidate.id}",
                stage=normalized_status,
                email=candidate.email,
            )
        update_data["status"] = normalized_status

    parsed_json = dict(candidate.parsed_json or {})
    for key, value in update_data.items():
        if hasattr(candidate, key):
            setattr(candidate, key, value)
        else:
            parsed_json[key] = value

    parsed_json.update({k: v for k, v in update_data.items() if not hasattr(candidate, k)})
    parsed_json["manual_reviewed"] = True
    candidate.parsed_json = parsed_json

    if note_text:
        _append_timeline_event(candidate, "note", note_text)

    db.commit()

    stmt = select(Candidate).options(selectinload(Candidate.files)).where(Candidate.id == candidate.id)
    return db.execute(stmt).scalar_one()


@router.delete("/{candidate_id}/files/{file_id}")
def delete_candidate_file(
    candidate_id: int,
    file_id: int,
    db: Session = Depends(get_db),
    _actor=Depends(require_roles("admin", "recruiter", "hiring_manager")),
):
    candidate = db.get(Candidate, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    if not _can_access_candidate(_actor, candidate):
        raise HTTPException(status_code=403, detail="Not allowed to update this candidate")

    file = db.get(CandidateFile, file_id)
    if not file or file.candidate_id != candidate_id:
        raise HTTPException(status_code=404, detail="File not found")

    storage.delete_by_url(file.file_url)
    db.delete(file)
    _append_timeline_event(candidate, "note", f"deleted_cv_file:{file.original_filename}")
    db.commit()
    log_event(_actor.email, "candidate.file.delete", f"candidate:{candidate_id}", {"file_id": file_id, "filename": file.original_filename})
    return {"ok": True}


@router.delete("/{candidate_id}")
def soft_delete_candidate(
    candidate_id: int,
    db: Session = Depends(get_db),
    _actor=Depends(require_roles("admin", "recruiter", "hiring_manager")),
):
    candidate = db.get(Candidate, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    if not _can_access_candidate(_actor, candidate):
        raise HTTPException(status_code=403, detail="Not allowed to delete this candidate")

    parsed = dict(candidate.parsed_json or {})
    parsed["deleted"] = True
    parsed["deleted_at"] = datetime.utcnow().isoformat()
    candidate.parsed_json = parsed
    _append_timeline_event(candidate, "note", "candidate_soft_deleted")
    db.commit()
    log_event(_actor.email, "candidate.soft_delete", f"candidate:{candidate_id}", {})
    return {"ok": True}


@router.post("/{candidate_id}/restore")
def restore_candidate(
    candidate_id: int,
    db: Session = Depends(get_db),
    _actor=Depends(require_roles("admin", "recruiter", "hiring_manager")),
):
    candidate = db.get(Candidate, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    if not _can_access_candidate(_actor, candidate):
        raise HTTPException(status_code=403, detail="Not allowed to restore this candidate")

    parsed = dict(candidate.parsed_json or {})
    parsed["deleted"] = False
    parsed.pop("deleted_at", None)
    candidate.parsed_json = parsed
    _append_timeline_event(candidate, "note", "candidate_restored")
    db.commit()
    log_event(_actor.email, "candidate.restore", f"candidate:{candidate_id}", {})
    return {"ok": True}
