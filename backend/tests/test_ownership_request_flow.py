from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Candidate, User
from app.routers.candidates import (
    decide_ownership_request,
    request_candidate_ownership,
    _can_manage_candidate,
)


def _db():
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    return Session()


def _seed():
    db = _db()
    owner = User(email="owner@x.com", full_name="owner", role="recruiter")
    req = User(email="req@x.com", full_name="req", role="recruiter")
    db.add_all([owner, req])
    db.commit()
    db.refresh(owner)
    db.refresh(req)
    c = Candidate(name="Bob", status="applied", parsed_json={"owner_user_id": owner.id, "owner_email": owner.email, "timeline": []})
    db.add(c)
    db.commit()
    db.refresh(c)
    return db, owner, req, c


def test_ownership_request_approve_transfers_manage_access():
    db, owner, req, c = _seed()

    out = request_candidate_ownership(c.id, payload={"reason": "need for my pipeline"}, db=db, actor=req)
    assert out["ok"] is True

    c2 = db.get(Candidate, c.id)
    reqs = (c2.parsed_json or {}).get("ownership_requests", [])
    assert len(reqs) == 1
    rid = reqs[0]["id"]

    rs = decide_ownership_request(c.id, rid, {"decision": "approve"}, db=db, actor=owner)
    assert rs["ok"] is True
    c3 = db.get(Candidate, c.id)
    assert (c3.parsed_json or {}).get("owner_email") == req.email
    assert _can_manage_candidate(req, c3)
    assert not _can_manage_candidate(owner, c3)


def test_ownership_request_reject_keeps_original_owner():
    db, owner, req, c = _seed()

    out = request_candidate_ownership(c.id, payload={"reason": "test reject"}, db=db, actor=req)
    assert out["ok"] is True

    c2 = db.get(Candidate, c.id)
    rid = (c2.parsed_json or {}).get("ownership_requests", [])[0]["id"]

    rs = decide_ownership_request(c.id, rid, {"decision": "reject"}, db=db, actor=owner)
    assert rs["ok"] is True

    c3 = db.get(Candidate, c.id)
    assert (c3.parsed_json or {}).get("owner_email") == owner.email
    assert _can_manage_candidate(owner, c3)
    assert not _can_manage_candidate(req, c3)
