from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.rbac import get_current_user, require_roles
from app.schemas import UserOut
from app.services import user_access

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("/me", response_model=UserOut)
def me(user=Depends(get_current_user)):
    return user


@router.get("", response_model=list[UserOut])
def list_users(
    db: Session = Depends(get_db),
    _=Depends(require_roles("admin", "hiring_manager")),
):
    return list(db.execute(select(User).order_by(User.created_at.desc())).scalars().all())


@router.patch("/{user_id}/role", response_model=UserOut)
def update_user_role(
    user_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    _=Depends(require_roles("admin")),
):
    user = db.get(User, user_id)
    if not user:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="User not found")

    role = str(payload.get("role", "")).strip().lower()
    if role not in {"admin", "recruiter", "interviewer", "hiring_manager"}:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Invalid role")

    user.role = role
    db.commit()
    db.refresh(user)
    return user


@router.patch("/{user_id}/disable")
def disable_user(
    user_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    _=Depends(require_roles("admin")),
):
    user = db.get(User, user_id)
    if not user:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="User not found")

    disabled = bool(payload.get("disabled", True))
    user_access.set_disabled(user.id, user.email, disabled)
    return {"ok": True, "user_id": user.id, "disabled": disabled}


@router.get("/access/disabled")
def list_disabled(
    _=Depends(require_roles("admin")),
):
    ids = sorted(list(user_access.list_disabled_ids()))
    return {"disabled_user_ids": ids}
