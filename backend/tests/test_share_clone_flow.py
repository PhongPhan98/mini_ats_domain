from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Candidate, User
from app.routers.candidates import (
    _can_manage_candidate,
    decide_share_invitation,
    share_candidate,
)


def _db():
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    return Session()


def test_share_invite_approve_creates_owned_clone_for_recipient():
    db = _db()
    owner = User(email="owner@example.com", full_name="owner", role="recruiter")
    receiver = User(email="receiver@example.com", full_name="receiver", role="recruiter")
    db.add_all([owner, receiver])
    db.commit()
    db.refresh(owner)
    db.refresh(receiver)

    c = Candidate(
        name="Alice",
        status="applied",
        parsed_json={"owner_user_id": owner.id, "owner_email": owner.email, "timeline": []},
    )
    db.add(c)
    db.commit()
    db.refresh(c)

    rs = share_candidate(c.id, {"email": receiver.email, "reason": "please take this"}, db=db, actor=owner)
    assert rs["ok"] is True

    updated = db.get(Candidate, c.id)
    invitations = (updated.parsed_json or {}).get("share_invitations", [])
    assert len(invitations) == 1
    invite_id = invitations[0]["id"]

    out = decide_share_invitation(c.id, invite_id, {"decision": "approve"}, db=db, actor=receiver)
    assert out["ok"] is True
    clone_id = out.get("clone_candidate_id")
    assert clone_id

    clone = db.get(Candidate, clone_id)
    assert clone is not None
    assert (clone.parsed_json or {}).get("owner_email") == receiver.email
    assert (clone.parsed_json or {}).get("source_candidate_id") == c.id

    assert _can_manage_candidate(owner, c)
    assert not _can_manage_candidate(receiver, c)
    assert _can_manage_candidate(receiver, clone)

    all_candidates = list(db.execute(select(Candidate)).scalars().all())
    assert len(all_candidates) == 2
