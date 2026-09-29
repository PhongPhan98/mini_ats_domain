from app.database import SessionLocal
from app.models import User


def is_disabled(user_id: int, email: str) -> bool:
    with SessionLocal() as db:
        user = db.get(User, user_id) or db.query(User).filter(User.email == email.lower()).first()
        return bool(user and user.disabled)


def set_disabled(user_id: int, email: str, disabled: bool):
    with SessionLocal() as db:
        user = db.get(User, user_id) or db.query(User).filter(User.email == email.lower()).first()
        if user:
            user.disabled = disabled
            db.commit()


def list_disabled_ids() -> set[int]:
    with SessionLocal() as db:
        return {row.id for row in db.query(User).filter(User.disabled.is_(True)).all()}
