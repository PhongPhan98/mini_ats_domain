from typing import Any

from fastapi import APIRouter, Depends, Query

from app.rbac import require_roles
from app.services.automation import load_rules, read_events, save_rules

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
