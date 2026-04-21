from typing import Iterable

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User

ALLOWED_ROLES = {"admin", "recruiter", "interviewer", "hiring_manager"}


def get_current_user(
    db: Session = Depends(get_db),
    x_user_email: str | None = Header(default=None),
    x_user_role: str | None = Header(default=None),
):
    """
    Dev-mode auth: reads identity from headers.
    If email doesn't exist, auto-provisions user.
    """
    email = (x_user_email or "demo@mini-ats.local").strip().lower()
    role = (x_user_role or "admin").strip().lower()
    if role not in ALLOWED_ROLES:
        raise HTTPException(status_code=403, detail=f"Invalid role '{role}'")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(email=email, full_name=email.split("@")[0], role=role)
        db.add(user)
        db.commit()
        db.refresh(user)
    elif user.role != role:
        user.role = role
        db.commit()
        db.refresh(user)

    return user


def require_roles(*roles: str):
    required = set(roles)

    def _dep(user=Depends(get_current_user)):
        if required and user.role not in required:
            raise HTTPException(status_code=403, detail=f"Role '{user.role}' not allowed")
        return user

    return _dep
