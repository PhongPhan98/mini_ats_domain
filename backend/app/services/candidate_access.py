from typing import Any


def _identity(user: Any) -> tuple[int, str]:
    return int(getattr(user, "id", 0) or 0), str(getattr(user, "email", "") or "").lower()


def is_candidate_owner(user: Any, candidate: Any) -> bool:
    direct_owner_id = getattr(candidate, "owner_user_id", None)
    if direct_owner_id is not None:
        return int(direct_owner_id) == int(getattr(user, "id", 0) or 0)
    parsed = candidate.parsed_json or {}
    user_id, user_email = _identity(user)
    owner_id = parsed.get("owner_user_id")
    owner_email = str(parsed.get("owner_email") or "").lower()
    return (
        (owner_id is not None and int(owner_id) == user_id)
        or (bool(owner_email) and owner_email == user_email)
    )


def can_manage_candidate(user: Any, candidate: Any) -> bool:
    user_org = getattr(user, "organization_id", None)
    candidate_org = getattr(candidate, "organization_id", None)
    if user_org is not None and candidate_org is not None and int(user_org) != int(candidate_org):
        return False
    return getattr(user, "role", "") != "recruiter" or is_candidate_owner(user, candidate)


def can_access_candidate(user: Any, candidate: Any) -> bool:
    user_org = getattr(user, "organization_id", None)
    candidate_org = getattr(candidate, "organization_id", None)
    if user_org is not None and candidate_org is not None and int(user_org) != int(candidate_org):
        return False
    if getattr(user, "role", "") != "recruiter" or is_candidate_owner(user, candidate):
        return True

    parsed = candidate.parsed_json or {}
    user_id, user_email = _identity(user)
    collaborator_ids = {
        int(value)
        for value in parsed.get("collaborator_user_ids", [])
        if str(value).isdigit()
    }
    collaborator_emails = {
        str(value).lower() for value in parsed.get("collaborator_emails", [])
    }
    invited_emails = {
        str(invitation.get("to_email", "")).lower()
        for invitation in parsed.get("share_invitations", [])
        if invitation.get("status") == "pending"
    }
    return (
        user_id in collaborator_ids
        or user_email in collaborator_emails
        or user_email in invited_emails
    )
