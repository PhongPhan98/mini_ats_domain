from fastapi import APIRouter, Depends, Query

from app.rbac import require_roles
from app.services.audit import read_events
from app.services.tenancy import ensure_user_organization
from app.database import get_db
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/audit", tags=["audit"])


@router.get("")
def list_audit_events(
    limit: int = Query(default=200, ge=1, le=1000),
    db: Session = Depends(get_db),
    actor=Depends(require_roles("admin")),
):
    return {"events": read_events(limit=limit, organization_id=ensure_user_organization(db, actor))}
