from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Candidate, CandidateComment, User
from app.routers.candidates import _can_access_candidate, _can_manage_candidate, _has_mention_access


def _db():
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    return Session()


def test_mentioned_user_gets_view_access_but_not_manage_access():
    db = _db()
    owner = User(email="owner@x.com", full_name="owner", role="recruiter")
    mentioned = User(email="reviewer@x.com", full_name="reviewer", role="recruiter")
    db.add_all([owner, mentioned])
    db.commit()
    db.refresh(owner)
    db.refresh(mentioned)

    cand = Candidate(name="C1", status="applied", parsed_json={"owner_user_id": owner.id, "owner_email": owner.email, "timeline": []})
    db.add(cand)
    db.commit()
    db.refresh(cand)

    # baseline: cannot access/manage before mention
    assert not _can_access_candidate(mentioned, cand)
    assert not _can_manage_candidate(mentioned, cand)

    cm = CandidateComment(
        candidate_id=cand.id,
        author_user_id=owner.id,
        body="@reviewer please check",
        mentions=["reviewer", mentioned.email],
    )
    db.add(cm)
    db.commit()

    assert _has_mention_access(db, mentioned, cand.id)
    # manage must still be denied
    assert not _can_manage_candidate(mentioned, cand)
