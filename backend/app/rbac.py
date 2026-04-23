from fastapi import Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session
import jwt

from app.config import settings
from app.database import get_db
from app.models import User

ALLOWED_ROLES = {"admin", "recruiter", "interviewer", "hiring_manager"}


def _get_user_by_email(db: Session, email: str, fallback_role: str = "recruiter"):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(email=email, full_name=email.split("@")[0], role=fallback_role)
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
    x_user_email: str | None = Header(default=None),
    x_user_role: str | None = Header(default=None),
):
    token = request.cookies.get(settings.auth_cookie_name)
    if token:
        try:
            payload = jwt.decode(token, settings.auth_jwt_secret, algorithms=["HS256"])
            uid = int(payload.get("sub", 0))
            user = db.query(User).filter(User.id == uid).first()
            if user:
                return user
        except Exception:
            raise HTTPException(status_code=401, detail="Invalid auth session")

    # optional fallback for local development only
    if settings.auth_allow_dev_headers:
        email = (x_user_email or "demo@mini-ats.local").strip().lower()
        role = (x_user_role or "admin").strip().lower()
        if role not in ALLOWED_ROLES:
            raise HTTPException(status_code=403, detail=f"Invalid role '{role}'")

        user = _get_user_by_email(db, email, fallback_role=role)
        if user.role != role:
            user.role = role
            db.commit()
            db.refresh(user)
        return user

    raise HTTPException(status_code=401, detail="Authentication required")


def require_roles(*roles: str):
    required = set(roles)

    def _dep(user=Depends(get_current_user)):
        if required and user.role not in required:
            raise HTTPException(status_code=403, detail=f"Role '{user.role}' not allowed")
        return user

    return _dep
