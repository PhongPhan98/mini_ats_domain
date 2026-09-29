"""Add organizations, applications, privacy fields, and database backed job settings.

This migration is deliberately additive so existing candidate data remains usable.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "20260929_01"
down_revision = None
branch_labels = None
depends_on = None


def _add_column(table: str, column: sa.Column) -> None:
    bind = op.get_bind()
    if table in inspect(bind).get_table_names() and column.name not in {c["name"] for c in inspect(bind).get_columns(table)}:
        op.add_column(table, column)


def upgrade():
    bind = op.get_bind()
    tables = set(inspect(bind).get_table_names())
    if "users" not in tables:
        from app.database import Base
        from app import models  # noqa: F401
        Base.metadata.create_all(bind)
        tables = set(inspect(bind).get_table_names())
    if "organizations" not in tables:
        op.create_table(
            "organizations",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.String(255), nullable=False),
            sa.Column("slug", sa.String(120), nullable=False, unique=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )

    _add_column("users", sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=True))
    _add_column("users", sa.Column("disabled", sa.Boolean(), nullable=False, server_default=sa.false()))
    _add_column("candidates", sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=True))
    _add_column("candidates", sa.Column("owner_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True))
    _add_column("candidates", sa.Column("acquisition_source", sa.String(80), nullable=False, server_default="direct"))
    _add_column("candidates", sa.Column("consent_status", sa.String(32), nullable=False, server_default="unknown"))
    _add_column("candidates", sa.Column("retention_until", sa.DateTime(), nullable=True))
    _add_column("candidates", sa.Column("deleted_at", sa.DateTime(), nullable=True))
    _add_column("candidate_files", sa.Column("content_sha256", sa.String(64), nullable=True))
    _add_column("candidate_files", sa.Column("content_type", sa.String(120), nullable=True))
    _add_column("candidate_files", sa.Column("size_bytes", sa.Integer(), nullable=True))

    for name, col in [
        ("organization_id", sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=True)),
        ("owner_user_id", sa.Column("owner_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True)),
        ("slug", sa.Column("slug", sa.String(255), nullable=True)),
        ("requisition_code", sa.Column("requisition_code", sa.String(80), nullable=True)),
        ("department", sa.Column("department", sa.String(120), nullable=True)),
        ("location", sa.Column("location", sa.String(255), nullable=True)),
        ("employment_type", sa.Column("employment_type", sa.String(50), nullable=True)),
        ("hiring_manager", sa.Column("hiring_manager", sa.String(255), nullable=True)),
        ("headcount", sa.Column("headcount", sa.Integer(), nullable=False, server_default="1")),
        ("salary_min", sa.Column("salary_min", sa.Integer(), nullable=True)),
        ("salary_max", sa.Column("salary_max", sa.Integer(), nullable=True)),
        ("currency", sa.Column("currency", sa.String(8), nullable=True)),
        ("description", sa.Column("description", sa.Text(), nullable=True)),
        ("criteria", sa.Column("criteria", sa.JSON(), nullable=True)),
        ("pipeline_stages", sa.Column("pipeline_stages", sa.JSON(), nullable=True)),
        ("status", sa.Column("status", sa.String(32), nullable=False, server_default="draft")),
        ("match_threshold", sa.Column("match_threshold", sa.Integer(), nullable=False, server_default="50")),
        ("published_at", sa.Column("published_at", sa.DateTime(), nullable=True)),
        ("closes_at", sa.Column("closes_at", sa.DateTime(), nullable=True)),
        ("deleted_at", sa.Column("deleted_at", sa.DateTime(), nullable=True)),
        ("updated_at", sa.Column("updated_at", sa.DateTime(), nullable=True)),
    ]:
        _add_column("jobs", col)

    # Create the new normalized tables from current ORM metadata after additive columns exist.
    from app.database import Base
    from app import models  # noqa: F401
    for table_name in ["candidate_access", "candidate_timeline", "applications", "application_stage_history", "audit_events", "report_schedules", "automation_rules", "automation_events", "offers", "public_application_attempts"]:
        Base.metadata.tables[table_name].create(bind, checkfirst=True)

    _add_column("interview_scorecards", sa.Column("application_id", sa.Integer(), sa.ForeignKey("applications.id", ondelete="CASCADE"), nullable=True))
    _add_column("interview_scorecards", sa.Column("submitted_at", sa.DateTime(), nullable=True))
    _add_column("interview_schedules", sa.Column("application_id", sa.Integer(), sa.ForeignKey("applications.id", ondelete="CASCADE"), nullable=True))
    _add_column("interview_schedules", sa.Column("status", sa.String(32), nullable=False, server_default="scheduled"))
    _add_column("email_schedules", sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=True))
    _add_column("email_schedules", sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"))
    _add_column("email_schedules", sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="3"))
    _add_column("email_schedules", sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True))
    _add_column("email_schedules", sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True))

    # Backfill a safe default workspace and preserve the old implicit public jobs.
    now = __import__("datetime").datetime.utcnow()
    organization_id = bind.execute(sa.text("SELECT id FROM organizations ORDER BY id LIMIT 1")).scalar()
    if organization_id is None:
        result = bind.execute(sa.text("INSERT INTO organizations (name, slug, created_at) VALUES (:name, :slug, :created_at) RETURNING id"), {"name": "Default workspace", "slug": "default-workspace", "created_at": now})
        organization_id = result.scalar()
    bind.execute(sa.text("UPDATE users SET organization_id = :org WHERE organization_id IS NULL"), {"org": organization_id})
    first_user_id = bind.execute(sa.text("SELECT id FROM users ORDER BY id LIMIT 1")).scalar()
    bind.execute(sa.text("UPDATE candidates SET organization_id = :org, owner_user_id = COALESCE(owner_user_id, :owner) WHERE organization_id IS NULL"), {"org": organization_id, "owner": first_user_id})
    bind.execute(sa.text("UPDATE jobs SET organization_id = :org, owner_user_id = COALESCE(owner_user_id, :owner), status = 'published', published_at = COALESCE(published_at, created_at), updated_at = COALESCE(updated_at, created_at) WHERE organization_id IS NULL"), {"org": organization_id, "owner": first_user_id})
    json_job_defaults = sa.text("UPDATE jobs SET criteria = COALESCE(criteria, :criteria), pipeline_stages = COALESCE(pipeline_stages, :stages)").bindparams(sa.bindparam("criteria", type_=sa.JSON()), sa.bindparam("stages", type_=sa.JSON()))
    bind.execute(json_job_defaults, {"criteria": {}, "stages": ["applied", "screening", "interview", "offer", "hired", "rejected"]})
    bind.execute(sa.text("UPDATE email_schedules SET organization_id = :org WHERE organization_id IS NULL"), {"org": organization_id})

    import re
    jobs = bind.execute(sa.text("SELECT id, title FROM jobs ORDER BY id")).mappings().all()
    used = set()
    for job in jobs:
        root = re.sub(r"[^a-z0-9]+", "-", (job["title"] or "job").lower()).strip("-") or "job"
        slug = root if root not in used else f"{root}-{job['id']}"
        used.add(slug)
        bind.execute(sa.text("UPDATE jobs SET slug = :slug WHERE id = :id AND slug IS NULL"), {"slug": slug, "id": job["id"]})

    import json
    from pathlib import Path
    settings_path = Path(__file__).resolve().parents[2] / "app" / "data" / "jobs_settings.json"
    try:
        legacy_job_settings = json.loads(settings_path.read_text(encoding="utf-8"))
    except Exception:
        legacy_job_settings = {}
    for job_id, job_settings in legacy_job_settings.items():
        if str(job_id).isdigit() and isinstance(job_settings, dict):
            bind.execute(sa.text("UPDATE jobs SET owner_user_id = COALESCE(:owner, owner_user_id), match_threshold = :threshold WHERE id = :id"), {"id": int(job_id), "owner": job_settings.get("owner_user_id"), "threshold": max(0, min(100, int(job_settings.get("threshold", 50))))})

    candidates = bind.execute(sa.text("SELECT id, status, parsed_json, created_at, organization_id, owner_user_id FROM candidates")).mappings().all()
    for candidate in candidates:
        parsed = candidate["parsed_json"] or {}
        if isinstance(parsed, str):
            try:
                parsed = json.loads(parsed)
            except Exception:
                parsed = {}
        legacy_owner = parsed.get("owner_user_id")
        acquisition_source = "career_site" if parsed.get("source") == "public_apply" else "direct_upload"
        bind.execute(sa.text("UPDATE candidates SET owner_user_id = COALESCE(:owner, owner_user_id), acquisition_source = :source WHERE id = :id"), {"owner": legacy_owner, "source": acquisition_source, "id": candidate["id"]})
        for event in parsed.get("timeline") or []:
            timestamp = event.get("timestamp") or candidate["created_at"] or now
            if isinstance(timestamp, str):
                try:
                    timestamp = __import__("datetime").datetime.fromisoformat(timestamp.replace("Z", "+00:00")).replace(tzinfo=None)
                except Exception:
                    timestamp = candidate["created_at"] or now
            timeline_insert = sa.text("INSERT INTO candidate_timeline (candidate_id, actor_user_id, event_type, value, metadata_json, created_at) VALUES (:candidate, NULL, :event_type, :value, :metadata, :created)").bindparams(sa.bindparam("metadata", type_=sa.JSON()))
            bind.execute(timeline_insert, {"candidate": candidate["id"], "event_type": str(event.get("type") or "note")[:50], "value": str(event.get("value") or ""), "metadata": {}, "created": timestamp})
        job_ids = []
        if parsed.get("applied_job_id"):
            job_ids.append(parsed["applied_job_id"])
        job_ids.extend(parsed.get("shortlisted_job_ids") or [])
        for job_id in {int(value) for value in job_ids if str(value).isdigit()}:
            if not bind.execute(sa.text("SELECT 1 FROM jobs WHERE id = :id"), {"id": job_id}).scalar():
                continue
            existing = bind.execute(sa.text("SELECT id FROM applications WHERE candidate_id = :candidate AND job_id = :job"), {"candidate": candidate["id"], "job": job_id}).scalar()
            if existing:
                continue
            values = {"org": candidate["organization_id"], "candidate": candidate["id"], "job": job_id, "owner": candidate["owner_user_id"], "stage": candidate["status"] or "applied", "source": "legacy_import", "created": candidate["created_at"] or now}
            insert_application = sa.text("INSERT INTO applications (organization_id, candidate_id, job_id, owner_user_id, stage, source, applied_at, stage_changed_at, created_at, updated_at, match_metadata) VALUES (:org, :candidate, :job, :owner, :stage, :source, :created, :created, :created, :created, :metadata) RETURNING id").bindparams(sa.bindparam("metadata", type_=sa.JSON()))
            result = bind.execute(insert_application, {**values, "metadata": {}})
            application_id = result.scalar()
            bind.execute(sa.text("INSERT INTO application_stage_history (application_id, from_stage, to_stage, changed_by_user_id, changed_at) VALUES (:application, NULL, :stage, :owner, :created)"), {"application": application_id, **values})

    job_indexes = inspect(bind).get_indexes("jobs")
    if not any(index.get("unique") and index.get("column_names") == ["slug"] for index in job_indexes):
        op.create_index("ux_jobs_slug", "jobs", ["slug"], unique=True)
    for table, column, name in [
        ("users", "organization_id", "ix_users_organization_id"),
        ("candidates", "organization_id", "ix_candidates_organization_id"),
        ("candidates", "owner_user_id", "ix_candidates_owner_user_id"),
        ("jobs", "organization_id", "ix_jobs_organization_id"),
        ("jobs", "owner_user_id", "ix_jobs_owner_user_id"),
        ("email_schedules", "organization_id", "ix_email_schedules_organization_id"),
        ("candidate_files", "content_sha256", "ix_candidate_files_content_sha256"),
    ]:
        if name not in {index["name"] for index in inspect(bind).get_indexes(table)}:
            op.create_index(name, table, [column])


def downgrade():
    # Data preserving migration: downgrade intentionally keeps the additive schema.
    pass
