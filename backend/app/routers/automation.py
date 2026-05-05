from typing import Any

from fastapi import APIRouter, Depends, Query

from app.rbac import require_roles
from app.services.automation import load_rules, read_events, save_rules, clear_events

router = APIRouter(prefix="/api/automation", tags=["automation"])


@router.get("/rules")
def get_rules(actor=Depends(require_roles("admin", "recruiter", "hiring_manager"))):
    key = actor.email if getattr(actor, "role", "") == "recruiter" else "*"
    return load_rules(key)


@router.put("/rules")
def put_rules(payload: dict[str, Any], actor=Depends(require_roles("admin", "recruiter", "hiring_manager"))):
    key = actor.email if getattr(actor, "role", "") == "recruiter" else "*"
    return save_rules(payload, key)


@router.post("/rules")
def post_rules(payload: dict[str, Any], actor=Depends(require_roles("admin", "recruiter", "hiring_manager"))):
    key = actor.email if getattr(actor, "role", "") == "recruiter" else "*"
    return save_rules(payload, key)


@router.get("/events")
def get_events(
    limit: int = Query(default=100, ge=1, le=500),
    _=Depends(require_roles("admin", "recruiter", "interviewer", "hiring_manager")),
):
    return {"events": read_events(limit=limit)}


@router.post("/events/clear")
def clear_automation_events(actor=Depends(require_roles("admin", "recruiter", "hiring_manager"))):
    clear_events()
    return {"ok": True}


@router.post("/rules/test-run")
def test_run_rule(payload: dict, actor=Depends(require_roles("admin", "recruiter", "hiring_manager"))):
    from datetime import datetime
    from app.services.automation import append_event
    rid = payload.get("rule_id") or "manual-test"
    append_event({"timestamp": datetime.utcnow().isoformat(), "candidate_id": 0, "candidate_name": "TEST", "stage": payload.get("stage") or "interview", "rule_id": rid, "action": {"type": "log"}, "result": "test_run_ok"})
    return {"ok": True}

from datetime import datetime
from app.services.emailer import send_email
from app.database import get_db
from sqlalchemy.orm import Session
from app.models import EmailSchedule

@router.get("/email/schedules")
def list_simple_email_schedules(actor=Depends(require_roles("admin","recruiter","hiring_manager")), db: Session = Depends(get_db)):
    rows = db.query(EmailSchedule).order_by(EmailSchedule.created_at.desc()).limit(500).all()
    return {"items": [{"id": f"sch-{r.id}", "to": r.to_email, "subject": r.subject, "body": r.body, "send_at": (r.send_at.isoformat() if r.send_at else ""), "status": r.status} for r in rows]}

@router.post("/email/send-now")
def send_now(payload: dict, actor=Depends(require_roles("admin","recruiter","hiring_manager"))):
    try:
        ok = send_email(payload.get("to",""), payload.get("subject","Interview update"), payload.get("body",""))
        return {"ok": bool(ok), "message": "sent" if ok else "smtp_not_configured_or_failed"}
    except Exception as e:
        return {"ok": False, "message": f"send_failed:{e}"}

@router.post("/email/schedules")
def create_simple_email_schedule(payload: dict, actor=Depends(require_roles("admin","recruiter","hiring_manager")), db: Session = Depends(get_db)):
    send_at = payload.get("send_at")
    dt = None
    if send_at:
        try:
            dt = datetime.fromisoformat(str(send_at))
        except Exception:
            dt = None
    row = EmailSchedule(created_by_user_id=getattr(actor, "id", None), to_email=payload.get("to",""), subject=payload.get("subject","Interview update"), body=payload.get("body",""), send_at=dt, status="scheduled")
    db.add(row)
    db.commit()
    return {"ok": True}
