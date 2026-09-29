import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import ApplicationStageHistory, Candidate, Job, Organization, User
from app.services.applications import change_application_stage, create_application
from app.services.file_validation import validate_cv_file


def _db():
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, future=True)()


def test_one_candidate_has_independent_stages_for_two_jobs():
    db = _db()
    org = Organization(name="Example", slug="example")
    db.add(org)
    db.flush()
    owner = User(organization_id=org.id, email="owner@example.com", full_name="Owner", role="recruiter")
    db.add(owner)
    db.flush()
    candidate = Candidate(organization_id=org.id, owner_user_id=owner.id, name="Alice", status="applied")
    first_job = Job(organization_id=org.id, owner_user_id=owner.id, title="Engineer", slug="engineer", requirements="Python")
    second_job = Job(organization_id=org.id, owner_user_id=owner.id, title="Lead", slug="lead", requirements="Leadership")
    db.add_all([candidate, first_job, second_job])
    db.flush()

    first = create_application(db, candidate=candidate, job=first_job, owner_user_id=owner.id, source="career_site")
    second = create_application(db, candidate=candidate, job=second_job, owner_user_id=owner.id, source="referral")
    change_application_stage(db, first, "interview", actor_user_id=owner.id)
    db.commit()

    assert first.stage == "interview"
    assert second.stage == "applied"
    history = list(db.execute(select(ApplicationStageHistory).where(ApplicationStageHistory.application_id == first.id)).scalars())
    assert [event.to_stage for event in history] == ["applied", "interview"]


def test_cv_content_must_match_declared_extension():
    with pytest.raises(ValueError, match="valid PDF"):
        validate_cv_file("resume.pdf", b"not a pdf")
    with pytest.raises(ValueError, match="valid DOCX"):
        validate_cv_file("resume.docx", b"not a zip")
