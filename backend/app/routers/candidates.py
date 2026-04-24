from datetime import datetime
from pathlib import Path
from typing import Any
import json
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models import Candidate, CandidateFile, User, CandidateComment
from app.rbac import require_roles
from app.schemas import CandidateOut, CandidateUpdate
from app.services.automation import run_stage_change_automations
from app.services.parser import CVTextParser
from app.services.rule_based import SKILL_ALIASES, parse_candidate_from_cv
from app.services.storage import LocalStorageService
from app.services.audit import log_event
from app.services.llm import LLMService
from app.config import settings

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






def _parse_ai_with_timeout(text: str) -> dict[str, Any] | None:
    if not settings.parse_use_ai:
        return None
    timeout_s = max(2, int(settings.parse_ai_timeout_seconds or 10))

    def _run():
        return LLMService.parse_cv(text)

    try:
        with ThreadPoolExecutor(max_workers=1) as ex:
            future = ex.submit(_run)
            data = future.result(timeout=timeout_s)
        if isinstance(data, dict):
            return data
    except FuturesTimeoutError:
        return {"_ai_timeout": True}
    except Exception:
        return None
    return None

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
            "parse_warning": "Could not extract text from CV file. This file may be scanned/image-based. Please upload a text-based PDF or DOCX, or fill fields manually.",
            "scanned_suspected": True,
            "confidence": {},
            "confidence_score": 0,
            "source": "fallback",
            "ai_provider": settings.llm_provider,
            "ai_parse_status": "no_text_fallback_rule",
        }

    parsed_rule = parse_candidate_from_cv(text)

    # Try AI parsing with timeout, then fallback to rule-based if AI is slow/unavailable.
    ai_data = _parse_ai_with_timeout(text)
    parsed = dict(parsed_rule)
    if isinstance(ai_data, dict):
        if ai_data.get("_ai_timeout"):
            parsed["parse_warning"] = "AI parsing timed out. Continued with local parser." 
            parsed["ai_parse_status"] = "timeout_fallback_rule"
            parsed["ai_provider"] = settings.llm_provider
        else:
            merge_keys = [
                "name", "email", "phone", "skills", "years_of_experience", "education",
                "previous_companies", "summary", "linkedin_url", "github_url", "location",
                "current_title", "certifications", "languages", "projects"
            ]
            for k in merge_keys:
                v = ai_data.get(k)
                if v not in (None, "", [], {}):
                    parsed[k] = v
            parsed["ai_parse_status"] = "used"
            parsed["ai_provider"] = settings.llm_provider
            parsed["source"] = "ai_plus_rule"

    if "ai_parse_status" not in parsed:
        parsed["ai_parse_status"] = "rule_only"

    if len((text or "").strip()) < 160:
        parsed["parse_warning"] = "Very little extractable text detected. CV may be scanned/image-based; AI can only parse extracted text in current mode, so please review fields manually."
        parsed["scanned_suspected"] = True
    return parsed


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



def _can_manage_candidate(user, candidate: Candidate) -> bool:
    if getattr(user, "role", "") != "recruiter":
        return True
    parsed = candidate.parsed_json or {}
    owner_id = parsed.get("owner_user_id")
    owner_email = (parsed.get("owner_email") or "").lower()
    return (owner_id is not None and int(owner_id) == int(user.id)) or (owner_email and owner_email == user.email.lower())


def _can_access_candidate(user, candidate: Candidate) -> bool:
    # recruiter can only access candidates they own or are shared with.
    if getattr(user, "role", "") != "recruiter":
        return True
    parsed = candidate.parsed_json or {}
    owner_id = parsed.get("owner_user_id")
    owner_email = (parsed.get("owner_email") or "").lower()
    collab_ids = {int(x) for x in parsed.get("collaborator_user_ids", []) if str(x).isdigit()}
    collab_emails = {str(x).lower() for x in parsed.get("collaborator_emails", [])}
    invited_emails = {
        str(inv.get("to_email", "")).lower()
        for inv in parsed.get("share_invitations", [])
        if inv.get("status") == "pending"
    }

    return (
        (owner_id is not None and int(owner_id) == int(user.id))
        or (owner_email and owner_email == user.email.lower())
        or (int(user.id) in collab_ids)
        or (user.email.lower() in collab_emails)
        or (user.email.lower() in invited_emails)
    )



def _has_mention_access(db: Session, user, candidate_id: int) -> bool:
    me_email = (getattr(user, "email", "") or "").lower()
    me_local = me_email.split("@")[0] if me_email else ""
    me_name = (getattr(user, "full_name", "") or "").lower()
    comments = list(db.execute(select(CandidateComment).where(CandidateComment.candidate_id == candidate_id)).scalars().all())
    for c in comments:
        mentions = [str(x).lower() for x in (c.mentions or [])]
        if any(m in {me_email, me_local, me_name} for m in mentions):
            return True
    return False

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
    parsed["owner_user_id"] = _actor.id
    parsed["owner_email"] = _actor.email

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
    if not _can_access_candidate(_actor, candidate) and not _has_mention_access(db, _actor, candidate_id):
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
    if not _can_manage_candidate(_actor, candidate):
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
                owner_key=str((candidate.parsed_json or {}).get("owner_email") or _actor.email),
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
    if not _can_manage_candidate(_actor, candidate):
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
    if not _can_manage_candidate(_actor, candidate):
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
    if not _can_manage_candidate(_actor, candidate):
        raise HTTPException(status_code=403, detail="Not allowed to restore this candidate")

    parsed = dict(candidate.parsed_json or {})
    parsed["deleted"] = False
    parsed.pop("deleted_at", None)
    candidate.parsed_json = parsed
    _append_timeline_event(candidate, "note", "candidate_restored")
    db.commit()
    log_event(_actor.email, "candidate.restore", f"candidate:{candidate_id}", {})
    return {"ok": True}


@router.post("/{candidate_id}/share")
def share_candidate(
    candidate_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    actor=Depends(require_roles("admin", "recruiter", "hiring_manager")),
):
    candidate = db.get(Candidate, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    if not _can_manage_candidate(actor, candidate):
        raise HTTPException(status_code=403, detail="Not allowed to share this candidate")

    email = str(payload.get("email", "")).strip().lower()
    if not email:
        raise HTTPException(status_code=400, detail="email is required")
    if email == actor.email.lower():
        raise HTTPException(status_code=400, detail="Cannot share to yourself")

    parsed = dict(candidate.parsed_json or {})
    invitations = list(parsed.get("share_invitations", []))
    if any(str(i.get("to_email", "")).lower() == email and i.get("status") == "pending" for i in invitations):
        raise HTTPException(status_code=400, detail="Pending invitation already exists")

    invite_id = str(__import__("uuid").uuid4())
    now = datetime.utcnow().isoformat()
    reason = str(payload.get("reason", "")).strip()[:500]
    invitations.append({
        "id": invite_id,
        "candidate_id": candidate.id,
        "candidate_name": candidate.name,
        "from_user_id": actor.id,
        "from_email": actor.email.lower(),
        "to_email": email,
        "reason": reason,
        "status": "pending",
        "created_at": now,
        "updated_at": now,
    })
    parsed["share_invitations"] = invitations
    candidate.parsed_json = parsed
    _append_timeline_event(candidate, "share", f"share_invited:{email}")
    db.commit()
    return {"ok": True, "invite_id": invite_id}


@router.post("/{candidate_id}/unshare")
def unshare_candidate(
    candidate_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    actor=Depends(require_roles("admin", "recruiter", "hiring_manager")),
):
    candidate = db.get(Candidate, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    if not _can_manage_candidate(actor, candidate):
        raise HTTPException(status_code=403, detail="Not allowed to unshare this candidate")

    email = str(payload.get("email", "")).strip().lower()
    if not email:
        raise HTTPException(status_code=400, detail="email is required")

    parsed = dict(candidate.parsed_json or {})
    collab_emails = {str(x).lower() for x in parsed.get("collaborator_emails", [])}
    collab_ids = {int(x) for x in parsed.get("collaborator_user_ids", []) if str(x).isdigit()}

    collab_emails.discard(email)
    user = db.query(__import__("app.models", fromlist=["User"]).User).filter_by(email=email).first()
    if user:
        collab_ids.discard(int(user.id))

    parsed["collaborator_emails"] = sorted(collab_emails)
    parsed["collaborator_user_ids"] = sorted(collab_ids)
    candidate.parsed_json = parsed
    _append_timeline_event(candidate, "share", f"unshared_with:{email}")
    db.commit()
    return {"ok": True, "collaborator_emails": parsed["collaborator_emails"]}




@router.get("/share/invitations")
def list_share_invitations(
    scope: str = Query(default="inbox"),
    db: Session = Depends(get_db),
    actor=Depends(require_roles("admin", "recruiter", "hiring_manager")),
):
    candidates = list(db.execute(select(Candidate)).scalars().all())
    out = []
    for c in candidates:
        parsed = c.parsed_json or {}
        for inv in parsed.get("share_invitations", []):
            if scope == "sent" and str(inv.get("from_email", "")).lower() != actor.email.lower():
                continue
            if scope != "sent" and str(inv.get("to_email", "")).lower() != actor.email.lower():
                continue
            out.append({**inv, "candidate_id": c.id, "candidate_name": c.name})
    out.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return {"invitations": out}


@router.post("/{candidate_id}/share/invitations/{invite_id}/decision")
def decide_share_invitation(
    candidate_id: int,
    invite_id: str,
    payload: dict,
    db: Session = Depends(get_db),
    actor=Depends(require_roles("admin", "recruiter", "hiring_manager")),
):
    decision = str(payload.get("decision", "")).lower()
    if decision not in {"approve", "reject"}:
        raise HTTPException(status_code=400, detail="decision must be approve|reject")

    candidate = db.get(Candidate, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    parsed = dict(candidate.parsed_json or {})
    invitations = list(parsed.get("share_invitations", []))
    target = None
    for inv in invitations:
        if str(inv.get("id")) == invite_id:
            target = inv
            break
    if not target:
        raise HTTPException(status_code=404, detail="Invitation not found")
    if str(target.get("to_email", "")).lower() != actor.email.lower() and actor.role != "admin":
        raise HTTPException(status_code=403, detail="Not allowed to decide this invitation")
    if target.get("status") != "pending":
        raise HTTPException(status_code=400, detail="Invitation already resolved")

    now = datetime.utcnow().isoformat()
    target["status"] = "approved" if decision == "approve" else "rejected"
    target["updated_at"] = now

    clone_candidate_id = None
    if decision == "approve":
        clone_parsed = dict(candidate.parsed_json or {})
        clone_parsed["owner_user_id"] = actor.id
        clone_parsed["owner_email"] = actor.email.lower()
        clone_parsed["deleted"] = False
        clone_parsed.pop("deleted_at", None)
        clone_parsed["source_candidate_id"] = candidate.id
        clone_parsed.pop("collaborator_emails", None)
        clone_parsed.pop("collaborator_user_ids", None)
        clone_parsed.pop("share_invitations", None)
        clone_parsed.pop("ownership_requests", None)

        clone = Candidate(
            name=candidate.name,
            email=candidate.email,
            phone=candidate.phone,
            status=normalize_status(candidate.status),
            skills=list(candidate.skills or []),
            years_of_experience=candidate.years_of_experience,
            education=list(candidate.education or []),
            previous_companies=list(candidate.previous_companies or []),
            summary=candidate.summary,
            parsed_json=clone_parsed,
        )
        db.add(clone)
        db.flush()
        clone_candidate_id = clone.id

        source_files = db.execute(select(CandidateFile).where(CandidateFile.candidate_id == candidate.id)).scalars().all()
        for f in source_files:
            db.add(CandidateFile(candidate_id=clone.id, file_url=f.file_url, original_filename=f.original_filename))

        _append_timeline_event(clone, "created", f"cloned_from:{candidate.id}")
        _append_timeline_event(candidate, "share", f"share_approved_by:{actor.email.lower()}")
    else:
        _append_timeline_event(candidate, "share", f"share_rejected_by:{actor.email.lower()}")

    parsed["share_invitations"] = invitations
    candidate.parsed_json = parsed
    db.commit()
    return {"ok": True, "invitation": target, "clone_candidate_id": clone_candidate_id}

@router.post("/{candidate_id}/ownership/request")
def request_candidate_ownership(
    candidate_id: int,
    payload: dict | None = None,
    db: Session = Depends(get_db),
    actor=Depends(require_roles("admin", "recruiter", "hiring_manager")),
):
    candidate = db.get(Candidate, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    if not _can_access_candidate(actor, candidate):
        raise HTTPException(status_code=403, detail="Not allowed to access this candidate")

    parsed = dict(candidate.parsed_json or {})
    owner_email = str(parsed.get("owner_email") or "")
    if owner_email.lower() == actor.email.lower():
        raise HTTPException(status_code=400, detail="You already own this candidate")

    requests = list(parsed.get("ownership_requests", []))
    rid = str(__import__("uuid").uuid4())
    now = __import__("datetime").datetime.utcnow().isoformat()
    reason = str((payload or {}).get("reason") or "").strip()
    expires_at = (__import__("datetime").datetime.utcnow() + __import__("datetime").timedelta(days=14)).isoformat()
    req = {
        "id": rid,
        "candidate_id": candidate_id,
        "from_user_id": actor.id,
        "from_email": actor.email,
        "to_email": owner_email,
        "reason": reason[:500],
        "status": "pending",
        "created_at": now,
        "updated_at": now,
        "expires_at": expires_at,
    }
    requests.append(req)
    parsed["ownership_requests"] = requests
    candidate.parsed_json = parsed
    _append_timeline_event(candidate, "share", f"ownership_request:{actor.email}")
    db.commit()
    return {"ok": True, "request": req}


@router.get("/ownership/requests")
def list_ownership_requests(
    scope: str = Query(default="inbox"),
    db: Session = Depends(get_db),
    actor=Depends(require_roles("admin", "recruiter", "hiring_manager")),
):
    candidates = list(db.execute(select(Candidate)).scalars().all())
    out = []
    now = __import__("datetime").datetime.utcnow().isoformat()
    changed = False
    for c in candidates:
        parsed = c.parsed_json or {}
        reqs = list(parsed.get("ownership_requests", []))
        for r in reqs:
            if r.get("status") == "pending" and r.get("expires_at") and str(r.get("expires_at")) < now:
                r["status"] = "expired"
                r["updated_at"] = now
                changed = True
        if changed:
            parsed["ownership_requests"] = reqs
            c.parsed_json = parsed
        for r in reqs:
            if scope == "sent" and str(r.get("from_email", "")).lower() != actor.email.lower():
                continue
            if scope != "sent" and str(r.get("to_email", "")).lower() != actor.email.lower():
                continue
            out.append({**r, "candidate_name": c.name})
    if changed:
        db.commit()
    out.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return {"requests": out}


@router.post("/{candidate_id}/ownership/requests/{request_id}/decision")
def decide_ownership_request(
    candidate_id: int,
    request_id: str,
    payload: dict,
    db: Session = Depends(get_db),
    actor=Depends(require_roles("admin", "recruiter", "hiring_manager")),
):
    decision = str(payload.get("decision", "")).lower()
    if decision not in {"approve", "reject"}:
        raise HTTPException(status_code=400, detail="decision must be approve|reject")

    candidate = db.get(Candidate, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    parsed = dict(candidate.parsed_json or {})
    if str(parsed.get("owner_email", "")).lower() != actor.email.lower() and actor.role != "admin":
        raise HTTPException(status_code=403, detail="Only owner/admin can decide")

    requests = list(parsed.get("ownership_requests", []))
    target = None
    for r in requests:
        if str(r.get("id")) == request_id:
            target = r
            break
    if not target:
        raise HTTPException(status_code=404, detail="Request not found")
    if target.get("status") != "pending":
        raise HTTPException(status_code=400, detail="Request is already resolved")

    target["status"] = "approved" if decision == "approve" else "rejected"
    target["updated_at"] = __import__("datetime").datetime.utcnow().isoformat()

    if decision == "approve":
        parsed["owner_user_id"] = target.get("from_user_id")
        parsed["owner_email"] = target.get("from_email")
        # keep old owner as collaborator for continuity
        collab_emails = {str(x).lower() for x in parsed.get("collaborator_emails", [])}
        collab_ids = {int(x) for x in parsed.get("collaborator_user_ids", []) if str(x).isdigit()}
        collab_emails.add(actor.email.lower())
        collab_ids.add(int(actor.id))
        parsed["collaborator_emails"] = sorted(collab_emails)
        parsed["collaborator_user_ids"] = sorted(collab_ids)

    parsed["ownership_requests"] = requests
    candidate.parsed_json = parsed
    _append_timeline_event(candidate, "share", f"ownership_{decision}:{target.get('from_email')}")
    db.commit()
    return {"ok": True, "request": target}
