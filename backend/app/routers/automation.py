from typing import Any

from fastapi import APIRouter, Depends, Query

from app.rbac import require_roles
from app.services.automation import load_rules, read_events, save_rules

router = APIRouter(prefix="/api/automation", tags=["automation"])


@router.get("/rules")
def get_rules(_=Depends(require_roles("admin", "recruiter", "hiring_manager"))):
    return load_rules()


@router.put("/rules")
def put_rules(payload: dict[str, Any], _=Depends(require_roles("admin", "recruiter", "hiring_manager"))):
    return save_rules(payload)


@router.post("/rules")
def post_rules(payload: dict[str, Any], _=Depends(require_roles("admin", "recruiter", "hiring_manager"))):
    return save_rules(payload)


@router.get("/events")
def get_events(
    limit: int = Query(default=100, ge=1, le=500),
    _=Depends(require_roles("admin", "recruiter", "interviewer", "hiring_manager")),
):
    return {"events": read_events(limit=limit)}
