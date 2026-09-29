from datetime import datetime, timedelta, timezone
import logging
import secrets
from urllib.parse import urlencode

import httpx
import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import User
from app.services import user_access
from app.services.tenancy import ensure_user_organization
from app.rbac import get_current_user

router = APIRouter(prefix="/api/auth", tags=["auth"])
logger = logging.getLogger(__name__)

logger.info(
    "OAuth configuration loaded frontend_base_url=%s google_redirect_uri=%s",
    settings.frontend_base_url,
    settings.google_redirect_uri,
)


GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"


def _issue_token(user: User) -> str:
    now = datetime.now(timezone.utc)
    exp = now + timedelta(hours=settings.auth_jwt_exp_hours)
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "role": user.role,
        "name": user.full_name,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }
    return jwt.encode(payload, settings.auth_jwt_secret, algorithm="HS256")


def _set_auth_cookie(resp: Response, token: str):
    is_production = settings.frontend_base_url.lower().startswith("https://")
    resp.set_cookie(
        key=settings.auth_cookie_name,
        value=token,
        httponly=True,
        secure=is_production,
        samesite="none" if is_production else "lax",
        max_age=settings.auth_jwt_exp_hours * 3600,
        path="/",
    )


@router.get("/config")
def auth_config():
    """Return only the public settings needed to render the sign-in screen."""
    return {
        "google_enabled": bool(
            settings.google_client_id and settings.google_client_secret
        ),
        "allowed_domain": settings.google_allowed_domain or None,
    }


@router.get("/google/login")
def google_login():
    if not settings.google_client_id:
        raise HTTPException(status_code=400, detail="Google OAuth is not configured")

    state = secrets.token_urlsafe(32)
    query = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "online",
        "prompt": "select_account",
        "state": state,
    }
    response = RedirectResponse(f"{GOOGLE_AUTH_URL}?{urlencode(query)}")
    response.set_cookie(
        "miniats_oauth_state", state, httponly=True,
        secure=settings.frontend_base_url.lower().startswith("https://"),
        samesite="lax", max_age=600, path="/api/auth/google/callback",
    )
    return response


@router.get("/google/callback")
async def google_callback(code: str, state: str, request: Request, db: Session = Depends(get_db)):
    if not settings.google_client_id or not settings.google_client_secret:
        raise HTTPException(status_code=400, detail="Google OAuth is not configured")
    expected_state = request.cookies.get("miniats_oauth_state")
    if not expected_state or not secrets.compare_digest(expected_state, state):
        raise HTTPException(status_code=400, detail="Invalid OAuth state")

    async with httpx.AsyncClient(timeout=15) as client:
        token_resp = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "redirect_uri": settings.google_redirect_uri,
                "grant_type": "authorization_code",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        if token_resp.status_code >= 400:
            raise HTTPException(status_code=400, detail="Google token exchange failed")

        access_token = token_resp.json().get("access_token")
        if not access_token:
            raise HTTPException(status_code=400, detail="Missing Google access token")

        info_resp = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if info_resp.status_code >= 400:
            raise HTTPException(status_code=400, detail="Google userinfo failed")

    info = info_resp.json()
    email = (info.get("email") or "").strip().lower()
    name = (info.get("name") or email.split("@")[0]).strip()

    if not email:
        raise HTTPException(status_code=400, detail="Email not found in Google profile")

    allowed = (settings.google_allowed_domain or "").strip().lower()
    if allowed and not email.endswith("@" + allowed):
        raise HTTPException(status_code=403, detail="Email domain not allowed")

    user = db.query(User).filter(User.email == email).first()
    if not user:
        bootstrap_admin = (settings.auth_bootstrap_admin_email or "").strip().lower()
        role = "admin" if bootstrap_admin and email == bootstrap_admin else "recruiter"
        user = User(email=email, full_name=name, role=role)
        db.add(user)
        db.commit()
        db.refresh(user)

    if not user.organization_id:
        ensure_user_organization(db, user)
        db.commit()
        db.refresh(user)

    if user_access.is_disabled(user.id, user.email):
        raise HTTPException(status_code=403, detail="User is disabled")

    token = _issue_token(user)
    redirect_url = f"{settings.frontend_base_url.rstrip('/')}/dashboard"
    logger.info(
        "Google OAuth success user_id=%s frontend_base_url=%s redirect_url=%s",
        user.id,
        settings.frontend_base_url,
        redirect_url,
    )
    resp = RedirectResponse(url=redirect_url)
    resp.delete_cookie("miniats_oauth_state", path="/api/auth/google/callback")
    _set_auth_cookie(resp, token)
    return resp


@router.get("/me")
def me(user=Depends(get_current_user)):
    if user_access.is_disabled(user.id, user.email):
        raise HTTPException(status_code=403, detail="User is disabled")

    logger.info("Authenticated session user_id=%s", user.id)
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
        "organization_id": user.organization_id,
    }


@router.post("/logout")
def logout(response: Response):
    is_production = settings.frontend_base_url.lower().startswith("https://")
    response.set_cookie(
        key=settings.auth_cookie_name,
        value="",
        max_age=0,
        expires=0,
        httponly=True,
        secure=is_production,
        samesite="none" if is_production else "lax",
        path="/",
    )
    logger.info("Auth logout cookie cleared")
    return {"ok": True}
