import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Organization, User
from app.config import settings


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "workspace"


def ensure_user_organization(db: Session, user: User) -> int:
    if user.organization_id:
        return int(user.organization_id)
    domain = (user.email.split("@", 1)[1] if "@" in user.email else "mini-ats.local").lower()
    configured_domain = (settings.google_allowed_domain or "").strip().lower()
    workspace_key = domain if configured_domain and domain == configured_domain else user.email.lower()
    slug = _slug(workspace_key)
    organization = db.execute(select(Organization).where(Organization.slug == slug)).scalar_one_or_none()
    if not organization:
        organization = Organization(name=domain if workspace_key == domain else f"{user.full_name}'s workspace", slug=slug)
        db.add(organization)
        db.flush()
    user.organization_id = organization.id
    db.flush()
    return int(organization.id)


def same_organization(actor: User, resource) -> bool:
    actor_org = getattr(actor, "organization_id", None)
    resource_org = getattr(resource, "organization_id", None)
    return actor_org is not None and resource_org is not None and int(actor_org) == int(resource_org)
