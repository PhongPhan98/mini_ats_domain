from fastapi import APIRouter, Depends, Query

from app.rbac import require_roles
from app.services.audit import read_events

router = APIRouter(prefix="/api/audit", tags=["audit"])


@router.get("")
def list_audit_events(
    limit: int = Query(default=200, ge=1, le=1000),
    _=Depends(require_roles("admin")),
):
    return {"events": read_events(limit=limit)}
