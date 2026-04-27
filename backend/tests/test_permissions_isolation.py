from types import SimpleNamespace

from app.routers.candidates import _can_access_candidate, _can_manage_candidate
from app.routers.jobs import _can_access_job


def user(id: int, email: str, role: str = "recruiter"):
    return SimpleNamespace(id=id, email=email, role=role)


def candidate(owner_id: int, owner_email: str, *, collab_ids=None, collab_emails=None):
    parsed_json = {
        "owner_user_id": owner_id,
        "owner_email": owner_email,
        "collaborator_user_ids": collab_ids or [],
        "collaborator_emails": collab_emails or [],
    }
    return SimpleNamespace(parsed_json=parsed_json)


def test_recruiter_only_accesses_owned_candidate_by_default():
    c = candidate(1, "a@example.com")
    assert _can_access_candidate(user(1, "a@example.com"), c)
    assert not _can_access_candidate(user(2, "b@example.com"), c)


def test_collaborator_can_access_but_cannot_manage_candidate():
    c = candidate(1, "a@example.com", collab_ids=[2], collab_emails=["b@example.com"])
    u = user(2, "b@example.com")
    assert _can_access_candidate(u, c)
    assert not _can_manage_candidate(u, c)


def test_recruiter_access_job_only_when_owner_matches():
    j = SimpleNamespace(id=7)
    settings = {"7": {"owner_user_id": 3, "owner_email": "owner@example.com"}}
    assert _can_access_job(user(3, "owner@example.com"), j, settings)
    assert not _can_access_job(user(4, "other@example.com"), j, settings)
