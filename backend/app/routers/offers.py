from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Application, Candidate, Job, Offer
from app.rbac import require_roles
from app.schemas import OfferCreate, OfferOut
from app.services.applications import change_application_stage
from app.services.audit import log_event
from app.services.tenancy import ensure_user_organization

router = APIRouter(prefix="/api/offers", tags=["offers"])
TRANSITIONS = {
    "draft": {"pending_approval"},
    "pending_approval": {"approved", "rejected"},
    "approved": {"sent"},
    "sent": {"accepted", "declined"},
    "rejected": {"draft"},
    "accepted": set(),
    "declined": set(),
}


def _get_offer(db: Session, offer_id: int, actor) -> Offer:
    offer = db.get(Offer, offer_id)
    org_id = ensure_user_organization(db, actor)
    if not offer or offer.organization_id != org_id:
        raise HTTPException(status_code=404, detail="Offer not found")
    application = db.get(Application, offer.application_id)
    if actor.role == "recruiter" and application and application.owner_user_id != actor.id:
        raise HTTPException(status_code=403, detail="Not allowed")
    return offer


@router.get("")
def list_offers(db: Session = Depends(get_db), actor=Depends(require_roles("admin", "recruiter", "hiring_manager"))):
    org_id = ensure_user_organization(db, actor)
    stmt = select(Offer, Application, Candidate, Job).join(Application, Application.id == Offer.application_id).join(Candidate, Candidate.id == Application.candidate_id).join(Job, Job.id == Application.job_id).where(Offer.organization_id == org_id)
    if actor.role == "recruiter":
        stmt = stmt.where(Application.owner_user_id == actor.id)
    rows = db.execute(stmt.order_by(Offer.created_at.desc())).all()
    return [{
        "id": offer.id, "application_id": app.id, "candidate_name": candidate.name,
        "job_title": job.title, "title": offer.title, "salary_amount": offer.salary_amount,
        "currency": offer.currency, "start_date": offer.start_date, "notes": offer.notes,
        "status": offer.status, "created_at": offer.created_at,
    } for offer, app, candidate, job in rows]


@router.post("", response_model=OfferOut)
def create_offer(payload: OfferCreate, db: Session = Depends(get_db), actor=Depends(require_roles("admin", "recruiter", "hiring_manager"))):
    org_id = ensure_user_organization(db, actor)
    application = db.get(Application, payload.application_id)
    if not application or application.organization_id != org_id:
        raise HTTPException(status_code=404, detail="Application not found")
    if actor.role == "recruiter" and application.owner_user_id != actor.id:
        raise HTTPException(status_code=403, detail="Not allowed")
    if db.execute(select(Offer).where(Offer.application_id == application.id)).scalar_one_or_none():
        raise HTTPException(status_code=409, detail="This application already has an offer")
    offer = Offer(organization_id=org_id, created_by_user_id=actor.id, **payload.model_dump())
    db.add(offer)
    change_application_stage(db, application, "offer", actor_user_id=actor.id, note="Offer drafted")
    db.commit()
    db.refresh(offer)
    return offer


@router.patch("/{offer_id}/status", response_model=OfferOut)
def update_offer_status(offer_id: int, payload: dict, db: Session = Depends(get_db), actor=Depends(require_roles("admin", "recruiter", "hiring_manager"))):
    offer = _get_offer(db, offer_id, actor)
    next_status = str(payload.get("status") or "").lower()
    if next_status not in TRANSITIONS.get(offer.status, set()):
        raise HTTPException(status_code=400, detail=f"Cannot move offer from {offer.status} to {next_status}")
    if next_status in {"approved", "rejected"} and actor.role not in {"admin", "hiring_manager"}:
        raise HTTPException(status_code=403, detail="A hiring manager or admin must approve offers")
    offer.status = next_status
    if next_status == "approved":
        offer.approved_by_user_id = actor.id
    application = db.get(Application, offer.application_id)
    if application and next_status == "accepted":
        change_application_stage(db, application, "hired", actor_user_id=actor.id, note="Offer accepted")
    elif application and next_status == "declined":
        change_application_stage(db, application, "rejected", actor_user_id=actor.id, rejection_reason="Offer declined")
    db.commit()
    db.refresh(offer)
    log_event(actor.email, "offer.status.update", f"offer:{offer.id}", {"status": next_status})
    return offer
