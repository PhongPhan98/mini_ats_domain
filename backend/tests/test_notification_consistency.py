from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Candidate, CandidateComment, User
from app.routers.comments import my_mentions
from app.routers.candidates import list_ownership_requests


def _db():
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    return Session()


def test_mentions_endpoint_returns_only_items_tagging_current_user():
    db = _db()
    owner = User(email="owner@x.com", full_name="owner", role="recruiter")
    target = User(email="target@x.com", full_name="target", role="recruiter")
    other = User(email="other@x.com", full_name="other", role="recruiter")
    db.add_all([owner, target, other])
    db.commit()
    db.refresh(owner)
    db.refresh(target)
    db.refresh(other)

    c = Candidate(name="N1", status="applied", parsed_json={"owner_user_id": owner.id, "owner_email": owner.email})
    db.add(c)
    db.commit()
    db.refresh(c)

    db.add(CandidateComment(candidate_id=c.id, author_user_id=owner.id, body="@target please review", mentions=["target@x.com"]))
    db.add(CandidateComment(candidate_id=c.id, author_user_id=owner.id, body="@other ping", mentions=["other@x.com"]))
    db.commit()

    out = my_mentions(db=db, user=target)
    items = out.get("mentions", [])
    assert len(items) == 1
    assert items[0]["candidate_id"] == c.id


def test_ownership_inbox_returns_pending_requests_for_receiver():
    db = _db()
    owner = User(email="owner@x.com", full_name="owner", role="recruiter")
    receiver = User(email="recv@x.com", full_name="recv", role="recruiter")
    db.add_all([owner, receiver])
    db.commit()
    db.refresh(owner)
    db.refresh(receiver)

    c = Candidate(
        name="N2",
        status="applied",
        parsed_json={
            "owner_user_id": owner.id,
            "owner_email": owner.email,
            "ownership_requests": [
                {
                    "id": "req-1",
                    "candidate_id": 1,
                    "from_user_id": receiver.id,
                    "from_email": receiver.email,
                    "to_email": owner.email,
                    "status": "pending",
                    "created_at": "2026-01-01T00:00:00",
                    "updated_at": "2026-01-01T00:00:00",
                }
            ],
        },
    )
    db.add(c)
    db.commit()

    inbox = list_ownership_requests(scope="inbox", db=db, actor=owner)
    sent = list_ownership_requests(scope="sent", db=db, actor=receiver)

    assert len(inbox.get("requests", [])) == 1
    assert inbox["requests"][0]["status"] == "pending"
    assert len(sent.get("requests", [])) == 1
