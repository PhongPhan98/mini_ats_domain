from datetime import datetime, timedelta, timezone
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

router = APIRouter(prefix="/api/auth", tags=["auth"])


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
    resp.set_cookie(
        key=settings.auth_cookie_name,
        value=token,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=settings.auth_jwt_exp_hours * 3600,
        path="/",
    )


@router.get("/google/login")
def google_login():
    if not settings.google_client_id:
        raise HTTPException(status_code=400, detail="Google OAuth is not configured")

    query = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "online",
        "prompt": "select_account",
    }
    return RedirectResponse(f"{GOOGLE_AUTH_URL}?{urlencode(query)}")


@router.get("/google/callback")
async def google_callback(code: str, db: Session = Depends(get_db)):
    if not settings.google_client_id or not settings.google_client_secret:
        raise HTTPException(status_code=400, detail="Google OAuth is not configured")

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

    if user_access.is_disabled(user.id, user.email):
        raise HTTPException(status_code=403, detail="User is disabled")

    token = _issue_token(user)
    resp = RedirectResponse(url="http://localhost:3000")
    _set_auth_cookie(resp, token)
    return resp


@router.get("/me")
def me(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get(settings.auth_cookie_name)
    if not token:
        raise HTTPException(status_code=401, detail="Not logged in")

    try:
        payload = jwt.decode(token, settings.auth_jwt_secret, algorithms=["HS256"])
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid session")

    user = db.query(User).filter(User.id == int(payload.get("sub", 0))).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    if user_access.is_disabled(user.id, user.email):
        raise HTTPException(status_code=403, detail="User is disabled")

    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
    }


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(settings.auth_cookie_name, path="/")
    return {"ok": True}
