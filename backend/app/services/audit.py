from app.database import SessionLocal
from app.models import AuditEvent, User


def log_event(actor_email: str, action: str, target: str, metadata: dict | None = None):
    with SessionLocal() as db:
        user = db.query(User).filter(User.email == actor_email.lower()).first() if actor_email != "public" else None
        db.add(AuditEvent(
            organization_id=user.organization_id if user else (metadata or {}).get("organization_id"),
            actor_email=actor_email,
            action=action,
            target=target,
            metadata_json=metadata or {},
        ))
        db.commit()


def read_events(limit: int = 200, organization_id: int | None = None) -> list[dict]:
    with SessionLocal() as db:
        query = db.query(AuditEvent)
        if organization_id is not None:
            query = query.filter(AuditEvent.organization_id == organization_id)
        rows = query.order_by(AuditEvent.created_at.desc()).limit(limit).all()
        return [{
            "timestamp": row.created_at.isoformat(), "actor_email": row.actor_email,
            "action": row.action, "target": row.target, "metadata": row.metadata_json or {},
        } for row in rows]
