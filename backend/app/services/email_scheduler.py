from datetime import datetime, timedelta, timezone

from sqlalchemy import or_, select

from app.database import SessionLocal
from app.models import EmailSchedule
from app.services.emailer import send_email


def process_due_email_schedules(organization_id: int | None = None, owner_user_id: int | None = None) -> dict:
    now = datetime.now(timezone.utc)
    sent = failed = 0
    with SessionLocal() as db:
        stmt = select(EmailSchedule).where(
            EmailSchedule.status.in_(["scheduled", "retrying"]),
            or_(EmailSchedule.send_at.is_(None), EmailSchedule.send_at <= now),
            or_(EmailSchedule.next_attempt_at.is_(None), EmailSchedule.next_attempt_at <= now),
        )
        if organization_id is not None:
            stmt = stmt.where(EmailSchedule.organization_id == organization_id)
        if owner_user_id is not None:
            stmt = stmt.where(EmailSchedule.created_by_user_id == owner_user_id)
        if db.bind and db.bind.dialect.name == "postgresql":
            stmt = stmt.with_for_update(skip_locked=True)
        rows = list(db.execute(stmt.limit(100)).scalars().all())
        for row in rows:
            row.status = "processing"
        db.commit()

        for row in rows:
            row.last_attempt_at = now
            row.attempts = int(row.attempts or 0) + 1
            try:
                ok = bool(send_email(row.to_email, row.subject, row.body))
                error = None if ok else "smtp_not_configured_or_failed"
            except Exception as exc:
                ok, error = False, str(exc)[:2000]
            if ok:
                row.status = "sent"
                row.error_message = None
                row.next_attempt_at = None
                sent += 1
            else:
                row.error_message = error
                if row.attempts < int(row.max_attempts or 3):
                    row.status = "retrying"
                    row.next_attempt_at = now + timedelta(minutes=2 ** row.attempts)
                else:
                    row.status = "failed"
                failed += 1
        db.commit()
    return {"ok": True, "sent": sent, "failed": failed}
