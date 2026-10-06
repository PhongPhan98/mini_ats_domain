from datetime import datetime
from typing import Any
import json
import hashlib

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile
from starlette.concurrency import run_in_threadpool
from app.services.cv_parsing import parse_cv_document, clean_reviewed_profile
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models import Application, Candidate, CandidateAccess, CandidateFile, User, CandidateComment, InterviewSchedule, InterviewScorecard
from app.rbac import require_roles
from app.schemas import CandidateOut, CandidateUpdate
from app.services.automation import run_stage_change_automations
from app.services.rule_based import SKILL_ALIASES
from app.services.storage import get_storage_service
from app.services.audit import log_event
from app.services.emailer import send_email
from app.services.candidate_access import (
    can_access_candidate as _can_access_candidate,
    can_manage_candidate as _can_manage_candidate,
)
from app.services.candidate_workflow import (
    append_timeline_event as _append_timeline_event,
    normalize_candidate_status as normalize_status,
)
from app.services.tenancy import ensure_user_organization
from app.services.applications import change_application_stage
from app.services.file_validation import MAX_CV_BYTES, validate_cv_file
from app.services.rich_text import clean_rich_text

router = APIRouter(prefix="/api/candidates", tags=["candidates"])
storage = get_storage_service()

ALLOWED_STATUSES = {"applied", "screening", "interview", "offer", "hired", "rejected"}
async def _read_cv_upload(file: UploadFile) -> tuple[str, bytes]:
    filename = file.filename or ""
    content = await file.read(MAX_CV_BYTES + 1)
    try:
        validate_cv_file(filename, content)
    except OverflowError as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=415, detail=str(exc)) from exc
    return filename, content


@router.post("/parse")
async def parse_cv_preview(
    file: UploadFile = File(...),
    _actor=Depends(require_roles("admin", "recruiter", "hiring_manager")),
):
    filename, content = await _read_cv_upload(file)

    parsed, source_text = await run_in_threadpool(parse_cv_document, filename, content)
    parsed["owner_user_id"] = _actor.id
    parsed["owner_email"] = _actor.email
    return {"filename": filename, "parsed": parsed, "source_text": source_text}



def _has_mention_access(db: Session, user, candidate_id: int) -> bool:
    candidate = db.get(Candidate, candidate_id)
    if not candidate or getattr(candidate, "organization_id", None) != getattr(user, "organization_id", None):
        return False
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
    return candidate.deleted_at is not None or bool(parsed.get("deleted"))


@router.post("/upload", response_model=CandidateOut)
async def upload_cv(
    file: UploadFile = File(...),
    edited_json: str | None = Form(default=None),
    reviewed: bool = Form(default=False),
    db: Session = Depends(get_db),
    _actor=Depends(require_roles("admin", "recruiter", "hiring_manager")),
):
    filename, content = await _read_cv_upload(file)

    edited: dict[str, Any] | None = None
    if edited_json:
        try:
            decoded = json.loads(edited_json)
            if isinstance(decoded, dict):
                edited = decoded
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid edited_json")

    if reviewed and edited is not None:
        parsed = clean_reviewed_profile(edited)
        parsed["manual_reviewed"] = True
        parsed.setdefault("source", "reviewed_preview")
    else:
        parsed, _ = await run_in_threadpool(parse_cv_document, filename, content)
        if edited is not None:
            parsed.update(clean_reviewed_profile(edited))

    # Ownership always comes from the authenticated actor, never client input.
    parsed["owner_user_id"] = _actor.id
    parsed["owner_email"] = _actor.email

    org_id = ensure_user_organization(db, _actor)
    clean_email = str(parsed.get("email") or "").strip().lower() or None
    existing = None
    if clean_email:
        existing = db.execute(select(Candidate).where(
            Candidate.organization_id == org_id,
            Candidate.email == clean_email,
            Candidate.deleted_at.is_(None),
        )).scalar_one_or_none()

    candidate = existing or Candidate(
        organization_id=org_id,
        owner_user_id=_actor.id,
        name=parsed.get("name"),
        email=clean_email,
        phone=parsed.get("phone"),
        status="applied",
        skills=parsed.get("skills", []),
        years_of_experience=parsed.get("years_of_experience"),
        education=parsed.get("education", []),
        previous_companies=parsed.get("previous_companies", []),
        summary=parsed.get("summary"),
        acquisition_source="direct_upload",
        consent_status="unknown",
        parsed_json=parsed,
    )
    if existing:
        # A person is stored once. A newer CV enriches the same profile.
        if not _can_manage_candidate(_actor, existing):
            raise HTTPException(status_code=403, detail="Not allowed to update this candidate")
        for key in ("name", "phone", "years_of_experience", "summary"):
            value = parsed.get(key)
            if value not in (None, ""):
                setattr(candidate, key, value)
        for key in ("skills", "education", "previous_companies"):
            if parsed.get(key):
                setattr(candidate, key, parsed[key])
        previous = dict(candidate.parsed_json or {})
        enrichment = {key: value for key, value in parsed.items()
            if value not in (None, "", []) and key not in {"owner_user_id", "owner_email"}}
        candidate.parsed_json = {**previous, **enrichment}
    db.add(candidate)
    db.flush()

    digest = hashlib.sha256(content).hexdigest()
    duplicate_file = db.execute(select(CandidateFile).where(CandidateFile.candidate_id == candidate.id, CandidateFile.content_sha256 == digest)).scalar_one_or_none()
    if not duplicate_file:
        file_url = storage.save_bytes(filename, content)
        db.add(CandidateFile(
            candidate_id=candidate.id,
            file_url=file_url,
            original_filename=filename,
            content_sha256=digest,
            content_type=file.content_type,
            size_bytes=len(content),
        ))

    _append_timeline_event(candidate, "note" if existing else "created", "CV imported" if existing else "Candidate profile created")

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
    org_id = ensure_user_organization(db, _actor)
    conditions: list[Any] = [Candidate.organization_id == org_id]

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


@router.get("/pipeline")
def list_pipeline(
    job_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    actor=Depends(require_roles("admin", "recruiter", "interviewer", "hiring_manager")),
):
    """Return a distinct card for every application, including in All jobs."""
    org_id = ensure_user_organization(db, actor)
    candidates = list(db.execute(
        select(Candidate).options(selectinload(Candidate.files)).where(
            Candidate.organization_id == org_id,
            Candidate.deleted_at.is_(None),
        )
    ).scalars())
    from app.models import Job
    applications = db.execute(
        select(Application, Job.title, Job.deleted_at).join(Job, Job.id == Application.job_id).where(
            Application.organization_id == org_id,
            Job.organization_id == org_id,
        ).order_by(Application.applied_at.desc())
    ).all()
    by_candidate: dict[int, list] = {}
    for application, title, deleted_at in applications:
        by_candidate.setdefault(application.candidate_id, []).append((application, title, deleted_at))

    cards = []
    for candidate in candidates:
        if _is_candidate_deleted(candidate) or not _can_access_candidate(actor, candidate):
            continue
        profile = CandidateOut.model_validate(candidate).model_dump(mode="json")
        entries = by_candidate.get(candidate.id, [])
        if not entries and not job_id:
            cards.append({**profile, "board_key": f"candidate:{candidate.id}", "job_title": None,
                "can_move": actor.role != "interviewer" and _can_manage_candidate(actor, candidate)})
        for application, title, deleted_at in entries:
            if deleted_at or application.withdrawn_at or (job_id and application.job_id != job_id):
                continue
            if actor.role == "recruiter" and application.owner_user_id != actor.id:
                continue
            cards.append({**profile,
                "board_key": f"application:{application.id}",
                "application_id": application.id, "job_id": application.job_id,
                "job_title": title, "status": application.stage,
                "applied_at": application.applied_at, "stage_changed_at": application.stage_changed_at,
                "match_score": application.match_score, "can_move": actor.role != "interviewer",
            })
    return cards


@router.get("/{candidate_id}", response_model=CandidateOut)
def get_candidate(
    candidate_id: int,
    db: Session = Depends(get_db),
    _actor=Depends(require_roles("admin", "recruiter", "interviewer", "hiring_manager")),
):
    org_id = ensure_user_organization(db, _actor)
    stmt = select(Candidate).options(selectinload(Candidate.files)).where(Candidate.id == candidate_id, Candidate.organization_id == org_id)
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
    org_id = ensure_user_organization(db, _actor)
    if not candidate or candidate.organization_id != org_id:
        raise HTTPException(status_code=404, detail="Candidate not found")
    if not _can_manage_candidate(_actor, candidate):
        raise HTTPException(status_code=403, detail="Not allowed to update this candidate")

    update_data = payload.model_dump(exclude_unset=True)
    if "rich_text" in update_data:
        update_data["rich_text"] = clean_rich_text(update_data["rich_text"])
    if "email" in update_data and update_data["email"]:
        update_data["email"] = str(update_data["email"]).strip().lower()
    if "consent_status" in update_data and update_data["consent_status"] not in {"unknown", "granted", "withdrawn"}:
        raise HTTPException(status_code=422, detail="consent_status must be unknown, granted, or withdrawn")

    # Prevent privilege escalation / ownership tampering via generic PATCH payload.
    protected_fields = {
        "owner_user_id", "owner_email",
        "collaborator_user_ids", "collaborator_emails",
        "share_invitations", "ownership_requests",
        "deleted", "deleted_at",
    }
    for k in list(update_data.keys()):
        if k in protected_fields:
            update_data.pop(k, None)

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


@router.get("/{candidate_id}/files/{file_id}/preview")
def preview_candidate_file(
    candidate_id: int,
    file_id: int,
    db: Session = Depends(get_db),
    _actor=Depends(require_roles("admin", "recruiter", "interviewer", "hiring_manager")),
):
    candidate = db.get(Candidate, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    if not _can_access_candidate(_actor, candidate) and not _has_mention_access(db, _actor, candidate_id):
        raise HTTPException(status_code=403, detail="Not allowed to access this candidate")

    file = db.get(CandidateFile, file_id)
    if not file or file.candidate_id != candidate_id:
        raise HTTPException(status_code=404, detail="File not found")
    if file.file_url.startswith("suppressed://"):
        raise HTTPException(status_code=404, detail="Raw CV content is not available")

    content = storage.read_by_url(file.file_url)
    if content is None:
        raise HTTPException(status_code=404, detail="Raw CV content is not available")

    suffix = Path(file.original_filename or "").suffix.lower()
    media_type = {
        ".pdf": "application/pdf",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }.get(suffix, "application/octet-stream")
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'inline; filename="{file.original_filename}"'},
    )


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
    candidate.deleted_at = datetime.utcnow()
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
    candidate.deleted_at = None
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
    invited_user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if not invited_user or invited_user.organization_id != candidate.organization_id:
        raise HTTPException(status_code=400, detail="Invite an existing user in this workspace")

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
        access = db.execute(select(CandidateAccess).where(CandidateAccess.candidate_id == candidate.id, CandidateAccess.user_id == user.id)).scalar_one_or_none()
        if access:
            db.delete(access)

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
    org_id = ensure_user_organization(db, actor)
    candidates = list(db.execute(select(Candidate).where(Candidate.organization_id == org_id)).scalars().all())
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
        existing_access = db.execute(select(CandidateAccess).where(
            CandidateAccess.candidate_id == candidate.id,
            CandidateAccess.user_id == actor.id,
        )).scalar_one_or_none()
        if not existing_access:
            db.add(CandidateAccess(candidate_id=candidate.id, user_id=actor.id, permission="view"))
        collab_emails = {str(x).lower() for x in parsed.get("collaborator_emails", [])}
        collab_ids = {int(x) for x in parsed.get("collaborator_user_ids", []) if str(x).isdigit()}
        collab_emails.add(actor.email.lower())
        collab_ids.add(int(actor.id))
        parsed["collaborator_emails"] = sorted(collab_emails)
        parsed["collaborator_user_ids"] = sorted(collab_ids)
        _append_timeline_event(candidate, "share", f"share_approved_by:{actor.email.lower()}")
    else:
        _append_timeline_event(candidate, "share", f"share_rejected_by:{actor.email.lower()}")

    parsed["share_invitations"] = invitations
    candidate.parsed_json = parsed
    db.commit()
    return {"ok": True, "invitation": target, "clone_candidate_id": clone_candidate_id}


@router.delete("/admin/{candidate_id}/permanent")
def permanently_delete_candidate(
    candidate_id: int,
    db: Session = Depends(get_db),
    actor=Depends(require_roles("admin")),
):
    candidate = db.get(Candidate, candidate_id)
    if not candidate or not _can_manage_candidate(actor, candidate):
        raise HTTPException(status_code=404, detail="Candidate not found")
    for file in list(candidate.files):
        storage.delete_by_url(file.file_url)
    db.delete(candidate)
    db.commit()
    log_event(actor.email, "candidate.permanent_delete", f"candidate:{candidate_id}", {})
    return {"ok": True}


@router.get("/{candidate_id}/privacy-export")
def export_candidate_privacy_data(
    candidate_id: int,
    db: Session = Depends(get_db),
    actor=Depends(require_roles("admin", "recruiter", "hiring_manager")),
):
    candidate = db.get(Candidate, candidate_id)
    if not candidate or not _can_manage_candidate(actor, candidate):
        raise HTTPException(status_code=404, detail="Candidate not found")
    applications = list(db.execute(select(Application).where(Application.candidate_id == candidate.id)).scalars().all())
    return {
        "exported_at": datetime.utcnow().isoformat(),
        "candidate": {"id": candidate.id, "name": candidate.name, "email": candidate.email, "phone": candidate.phone, "summary": candidate.summary, "skills": candidate.skills, "education": candidate.education, "previous_companies": candidate.previous_companies, "source": candidate.acquisition_source, "consent_status": candidate.consent_status, "created_at": candidate.created_at},
        "applications": [{"id": app.id, "job_id": app.job_id, "stage": app.stage, "source": app.source, "applied_at": app.applied_at, "rejection_reason": app.rejection_reason, "withdrawn_at": app.withdrawn_at} for app in applications],
        "files": [{"filename": file.original_filename, "uploaded_at": file.uploaded_at} for file in candidate.files],
    }


@router.post("/{candidate_id}/anonymize")
def anonymize_candidate(
    candidate_id: int,
    db: Session = Depends(get_db),
    actor=Depends(require_roles("admin")),
):
    candidate = db.get(Candidate, candidate_id)
    if not candidate or not _can_manage_candidate(actor, candidate):
        raise HTTPException(status_code=404, detail="Candidate not found")
    for file in list(candidate.files):
        storage.delete_by_url(file.file_url)
        db.delete(file)
    candidate.name = f"Anonymized candidate {candidate.id}"
    candidate.email = None
    candidate.phone = None
    candidate.summary = None
    candidate.education = []
    candidate.previous_companies = []
    candidate.skills = []
    candidate.parsed_json = {"anonymized_at": datetime.utcnow().isoformat()}
    candidate.consent_status = "withdrawn"
    db.commit()
    log_event(actor.email, "candidate.anonymize", f"candidate:{candidate_id}", {})
    return {"ok": True}


@router.post("/admin/retention/purge")
def purge_expired_candidate_data(
    db: Session = Depends(get_db),
    actor=Depends(require_roles("admin")),
):
    org_id = ensure_user_organization(db, actor)
    expired = list(db.execute(select(Candidate).where(
        Candidate.organization_id == org_id,
        Candidate.retention_until.is_not(None),
        Candidate.retention_until < datetime.utcnow(),
    )).scalars().all())
    for candidate in expired:
        for file in list(candidate.files):
            storage.delete_by_url(file.file_url)
            db.delete(file)
        candidate.name = f"Anonymized candidate {candidate.id}"
        candidate.email = None
        candidate.phone = None
        candidate.summary = None
        candidate.education = []
        candidate.previous_companies = []
        candidate.skills = []
        candidate.parsed_json = {"anonymized_at": datetime.utcnow().isoformat(), "reason": "retention_expired"}
        candidate.consent_status = "withdrawn"
        candidate.retention_until = None
    db.commit()
    log_event(actor.email, "candidate.retention.purge", "candidates", {"count": len(expired)})
    return {"ok": True, "anonymized": len(expired)}


@router.post("/{candidate_id}/merge")
def merge_duplicate_candidate(
    candidate_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    actor=Depends(require_roles("admin", "recruiter", "hiring_manager")),
):
    duplicate = db.get(Candidate, candidate_id)
    target = db.get(Candidate, int(payload.get("target_candidate_id", 0)))
    if not duplicate or not target or duplicate.id == target.id:
        raise HTTPException(status_code=400, detail="Choose two different candidates")
    if duplicate.organization_id != target.organization_id or not _can_manage_candidate(actor, duplicate) or not _can_manage_candidate(actor, target):
        raise HTTPException(status_code=403, detail="Not allowed to merge these candidates")
    target_jobs = {app.job_id for app in db.execute(select(Application).where(Application.candidate_id == target.id)).scalars().all()}
    for application in list(db.execute(select(Application).where(Application.candidate_id == duplicate.id)).scalars().all()):
        if application.job_id in target_jobs:
            db.delete(application)
        else:
            application.candidate_id = target.id
    for model in (CandidateFile, CandidateComment, InterviewSchedule, InterviewScorecard):
        for row in list(db.execute(select(model).where(model.candidate_id == duplicate.id)).scalars().all()):
            row.candidate_id = target.id
    target_access_users = {row.user_id for row in db.execute(select(CandidateAccess).where(CandidateAccess.candidate_id == target.id)).scalars().all()}
    for row in list(db.execute(select(CandidateAccess).where(CandidateAccess.candidate_id == duplicate.id)).scalars().all()):
        if row.user_id in target_access_users:
            db.delete(row)
        else:
            row.candidate_id = target.id
    target.skills = sorted(set(target.skills or []) | set(duplicate.skills or []))
    target.parsed_json = {**(duplicate.parsed_json or {}), **(target.parsed_json or {})}
    db.delete(duplicate)
    db.commit()
    log_event(actor.email, "candidate.merge", f"candidate:{target.id}", {"merged_candidate_id": candidate_id})
    return {"ok": True, "candidate_id": target.id}

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
    # Allow ownership request from recruiter/admin/hiring_manager even without current access.
    # This supports explicit handover workflows discovered in tests.
    if not (_can_access_candidate(actor, candidate) or _has_mention_access(db, actor, candidate_id) or getattr(actor, "role", "") in {"admin", "recruiter", "hiring_manager"}):
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
    org_id = ensure_user_organization(db, actor)
    candidates = list(db.execute(select(Candidate).where(Candidate.organization_id == org_id)).scalars().all())
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
        candidate.owner_user_id = int(target.get("from_user_id"))
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


@router.post("/{candidate_id}/email/interview")
def send_interview_email(
    candidate_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    _actor=Depends(require_roles("admin", "recruiter", "hiring_manager")),
):
    candidate = db.get(Candidate, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    if not _can_manage_candidate(_actor, candidate):
        raise HTTPException(status_code=403, detail="Not allowed")
    to_email = payload.get("to_email") or candidate.email
    subject = payload.get("subject") or f"Interview Invitation - {candidate.name or 'Candidate'}"
    body = payload.get("body") or ("Hello " + (candidate.name or "") + "\n\nYou are invited to interview.\n\nBest regards.")
    ok = send_email(to_email, subject, body)
    _append_timeline_event(candidate, "note", f"email_interview_sent:{to_email}:{'ok' if ok else 'skipped'}")
    log_event(_actor.email, "candidate.email.interview", f"candidate:{candidate_id}", {"to": to_email, "ok": ok})
    db.commit()
    return {"ok": ok}


@router.post("/{candidate_id}/email/rejection")
def send_rejection_email(
    candidate_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    _actor=Depends(require_roles("admin", "recruiter", "hiring_manager")),
):
    candidate = db.get(Candidate, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    if not _can_manage_candidate(_actor, candidate):
        raise HTTPException(status_code=403, detail="Not allowed")
    to_email = payload.get("to_email") or candidate.email
    subject = payload.get("subject") or f"Application Update - {candidate.name or 'Candidate'}"
    body = payload.get("body") or ("Hello " + (candidate.name or "") + "\n\nThank you for your application. We will not proceed this time.\n\nBest regards.")
    ok = send_email(to_email, subject, body)
    _append_timeline_event(candidate, "note", f"email_rejection_sent:{to_email}:{'ok' if ok else 'skipped'}")
    log_event(_actor.email, "candidate.email.rejection", f"candidate:{candidate_id}", {"to": to_email, "ok": ok})
    db.commit()
    return {"ok": ok}


@router.patch("/{candidate_id}/stage", response_model=CandidateOut)
def update_candidate_stage(
    candidate_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    _actor=Depends(require_roles("admin", "recruiter", "hiring_manager")),
):
    candidate = db.get(Candidate, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    if not _can_manage_candidate(_actor, candidate):
        raise HTTPException(status_code=403, detail="Not allowed to update this candidate")

    stage = normalize_status(str(payload.get("status") or payload.get("stage") or ""))
    if stage not in ALLOWED_STATUSES:
        raise HTTPException(status_code=400, detail=f"Invalid status '{stage}'")

    application_id = payload.get("application_id")
    job_id = payload.get("job_id")
    application = None
    if application_id:
        application = db.get(Application, int(application_id))
    elif job_id:
        application = db.execute(select(Application).where(
            Application.candidate_id == candidate.id,
            Application.job_id == int(job_id),
        )).scalar_one_or_none()
    if (application_id or job_id) and not application:
        raise HTTPException(status_code=404, detail="Application not found")
    if not application and db.execute(select(Application.id).where(
        Application.candidate_id == candidate.id,
    ).limit(1)).scalar_one_or_none():
        raise HTTPException(status_code=409, detail="This candidate has job applications. Refresh the pipeline and move the relevant application card.")
    if application:
        if application.candidate_id != candidate.id or application.organization_id != candidate.organization_id:
            raise HTTPException(status_code=404, detail="Application not found")
        change_application_stage(
            db, application, stage, actor_user_id=_actor.id,
            note=str(payload.get("note") or "") or None,
            rejection_reason=str(payload.get("rejection_reason") or "") or None,
        )
    elif stage != normalize_status(candidate.status):
        candidate.status = stage
        _append_timeline_event(candidate, "status", stage)
    db.commit()
    stmt = select(Candidate).options(selectinload(Candidate.files)).where(Candidate.id == candidate.id)
    return db.execute(stmt).scalar_one()
