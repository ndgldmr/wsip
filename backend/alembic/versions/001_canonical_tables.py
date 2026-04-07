"""canonical tables + auth tables

Revision ID: 001
Revises:
Create Date: 2026-04-06
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # -------------------------------------------------------------------------
    # orgs
    # -------------------------------------------------------------------------
    op.create_table(
        "orgs",
        sa.Column("org_id", UUID(as_uuid=True), primary_key=True),
        sa.Column("org_name", sa.Text, nullable=False),
        sa.Column("parent_org_id", UUID(as_uuid=True), sa.ForeignKey("orgs.org_id"), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    # -------------------------------------------------------------------------
    # skills (no FK to other canonical tables)
    # -------------------------------------------------------------------------
    op.create_table(
        "skills",
        sa.Column("skill_id", UUID(as_uuid=True), primary_key=True),
        sa.Column("skill_name", sa.Text, nullable=False),
        sa.Column("skill_category", sa.Text, nullable=False),
        sa.Column("parent_skill_id", UUID(as_uuid=True), sa.ForeignKey("skills.skill_id"), nullable=True),
    )

    # -------------------------------------------------------------------------
    # teams (FK → orgs; circular FK to employees deferred via use_alter)
    # -------------------------------------------------------------------------
    op.create_table(
        "teams",
        sa.Column("team_id", UUID(as_uuid=True), primary_key=True),
        sa.Column("team_name", sa.Text, nullable=False),
        sa.Column("parent_team_id", UUID(as_uuid=True), sa.ForeignKey("teams.team_id"), nullable=True),
        sa.Column("org_id", UUID(as_uuid=True), sa.ForeignKey("orgs.org_id"), nullable=False),
        sa.Column("function_type", sa.Text, nullable=False),
        sa.Column("mission_area", sa.Text, nullable=True),
        # leader_employee_id added after employees table via ALTER TABLE below
        sa.Column("leader_employee_id", UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    # -------------------------------------------------------------------------
    # employees (FK → teams, orgs; self-ref manager)
    # -------------------------------------------------------------------------
    op.create_table(
        "employees",
        sa.Column("employee_id", UUID(as_uuid=True), primary_key=True),
        sa.Column("external_employee_ref", sa.Text, unique=True, nullable=False),
        sa.Column("full_name", sa.Text, nullable=False),
        sa.Column("preferred_name", sa.Text, nullable=True),
        sa.Column("email", sa.Text, unique=True, nullable=False),
        sa.Column("role_title", sa.Text, nullable=False),
        sa.Column("role_family", sa.Text, nullable=False),
        sa.Column("job_level", sa.Text, nullable=False),
        sa.Column("employment_status", sa.Text, nullable=False, server_default="active"),
        sa.Column("manager_employee_id", UUID(as_uuid=True), sa.ForeignKey("employees.employee_id"), nullable=True),
        sa.Column("team_id", UUID(as_uuid=True), sa.ForeignKey("teams.team_id"), nullable=False),
        sa.Column("org_id", UUID(as_uuid=True), sa.ForeignKey("orgs.org_id"), nullable=False),
        sa.Column("location", sa.Text, nullable=True),
        sa.Column("hire_date", sa.Date, nullable=False),
        sa.Column("exit_date", sa.Date, nullable=True),
        sa.Column("compensation_band", sa.Text, nullable=True),
        sa.Column("clearance_tier", sa.Text, nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    # Now add the deferred FK from teams.leader_employee_id → employees
    op.create_foreign_key(
        "fk_team_leader",
        "teams",
        "employees",
        ["leader_employee_id"],
        ["employee_id"],
    )

    # -------------------------------------------------------------------------
    # repos
    # -------------------------------------------------------------------------
    op.create_table(
        "repos",
        sa.Column("repo_id", UUID(as_uuid=True), primary_key=True),
        sa.Column("source_system", sa.Text, nullable=False),
        sa.Column("repo_name", sa.Text, nullable=False),
        sa.Column("owning_team_id", UUID(as_uuid=True), sa.ForeignKey("teams.team_id"), nullable=True),
        sa.Column("is_monorepo", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    # -------------------------------------------------------------------------
    # projects
    # -------------------------------------------------------------------------
    op.create_table(
        "projects",
        sa.Column("project_id", UUID(as_uuid=True), primary_key=True),
        sa.Column("project_name", sa.Text, nullable=False),
        sa.Column("project_type", sa.Text, nullable=False),
        sa.Column("priority_tier", sa.Text, nullable=False),
        sa.Column("status", sa.Text, nullable=False, server_default="active"),
        sa.Column("owner_employee_id", UUID(as_uuid=True), sa.ForeignKey("employees.employee_id"), nullable=True),
        sa.Column("owning_team_id", UUID(as_uuid=True), sa.ForeignKey("teams.team_id"), nullable=False),
        sa.Column("strategic_area", sa.Text, nullable=True),
        sa.Column("start_date", sa.Date, nullable=False),
        sa.Column("target_end_date", sa.Date, nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    # -------------------------------------------------------------------------
    # employee_project_assignments
    # -------------------------------------------------------------------------
    op.create_table(
        "employee_project_assignments",
        sa.Column("assignment_id", UUID(as_uuid=True), primary_key=True),
        sa.Column("employee_id", UUID(as_uuid=True), sa.ForeignKey("employees.employee_id"), nullable=False),
        sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("projects.project_id"), nullable=False),
        sa.Column("assignment_role", sa.Text, nullable=False),
        sa.Column("allocation_pct", sa.Numeric(5, 2), nullable=False),
        sa.Column("start_date", sa.Date, nullable=False),
        sa.Column("end_date", sa.Date, nullable=True),
        sa.Column("staffing_source", sa.Text, nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    # -------------------------------------------------------------------------
    # employee_skills
    # -------------------------------------------------------------------------
    op.create_table(
        "employee_skills",
        sa.Column("employee_skill_id", UUID(as_uuid=True), primary_key=True),
        sa.Column("employee_id", UUID(as_uuid=True), sa.ForeignKey("employees.employee_id"), nullable=False),
        sa.Column("skill_id", UUID(as_uuid=True), sa.ForeignKey("skills.skill_id"), nullable=False),
        sa.Column("proficiency_level", sa.Text, nullable=False),
        sa.Column("evidence_type", sa.Text, nullable=False),
        sa.Column("confidence_score", sa.Numeric(5, 4), nullable=False),
        sa.Column("valid_from", sa.Date, nullable=False),
        sa.Column("valid_to", sa.Date, nullable=True),
    )

    # -------------------------------------------------------------------------
    # project_skill_requirements
    # -------------------------------------------------------------------------
    op.create_table(
        "project_skill_requirements",
        sa.Column("project_skill_req_id", UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("projects.project_id"), nullable=False),
        sa.Column("skill_id", UUID(as_uuid=True), sa.ForeignKey("skills.skill_id"), nullable=False),
        sa.Column("desired_level", sa.Text, nullable=False),
        sa.Column("weight", sa.Numeric(6, 4), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    # -------------------------------------------------------------------------
    # artifacts
    # -------------------------------------------------------------------------
    op.create_table(
        "artifacts",
        sa.Column("artifact_id", UUID(as_uuid=True), primary_key=True),
        sa.Column("artifact_type", sa.Text, nullable=False),
        sa.Column("source_system", sa.Text, nullable=False),
        sa.Column("source_artifact_ref", sa.Text, nullable=False),
        sa.Column("title", sa.Text, nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("created_by_employee_id", UUID(as_uuid=True), sa.ForeignKey("employees.employee_id"), nullable=True),
        sa.Column("owning_team_id", UUID(as_uuid=True), sa.ForeignKey("teams.team_id"), nullable=True),
        sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("projects.project_id"), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    # -------------------------------------------------------------------------
    # artifact_contributions
    # -------------------------------------------------------------------------
    op.create_table(
        "artifact_contributions",
        sa.Column("contribution_id", UUID(as_uuid=True), primary_key=True),
        sa.Column("artifact_id", UUID(as_uuid=True), sa.ForeignKey("artifacts.artifact_id"), nullable=False),
        sa.Column("employee_id", UUID(as_uuid=True), sa.ForeignKey("employees.employee_id"), nullable=False),
        sa.Column("contribution_type", sa.Text, nullable=False),
        sa.Column("contribution_weight", sa.Numeric(8, 4), nullable=False),
        sa.Column("contribution_ts", sa.TIMESTAMP(timezone=True), nullable=False),
    )

    # -------------------------------------------------------------------------
    # artifact_skill_tags
    # -------------------------------------------------------------------------
    op.create_table(
        "artifact_skill_tags",
        sa.Column("artifact_skill_tag_id", UUID(as_uuid=True), primary_key=True),
        sa.Column("artifact_id", UUID(as_uuid=True), sa.ForeignKey("artifacts.artifact_id"), nullable=False),
        sa.Column("skill_id", UUID(as_uuid=True), sa.ForeignKey("skills.skill_id"), nullable=False),
        sa.Column("tag_source", sa.Text, nullable=False),
        sa.Column("confidence_score", sa.Numeric(5, 4), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    # -------------------------------------------------------------------------
    # interactions
    # -------------------------------------------------------------------------
    op.create_table(
        "interactions",
        sa.Column("interaction_id", UUID(as_uuid=True), primary_key=True),
        sa.Column("interaction_type", sa.Text, nullable=False),
        sa.Column("source_system", sa.Text, nullable=False),
        sa.Column("from_employee_id", UUID(as_uuid=True), sa.ForeignKey("employees.employee_id"), nullable=False),
        sa.Column("to_employee_id", UUID(as_uuid=True), sa.ForeignKey("employees.employee_id"), nullable=False),
        sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("projects.project_id"), nullable=True),
        sa.Column("artifact_id", UUID(as_uuid=True), sa.ForeignKey("artifacts.artifact_id"), nullable=True),
        sa.Column("interaction_ts", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("interaction_weight", sa.Numeric(8, 4), nullable=False, server_default="1.0000"),
        sa.Column("metadata_json", JSONB, nullable=True),
    )

    # -------------------------------------------------------------------------
    # employee_snapshots
    # -------------------------------------------------------------------------
    op.create_table(
        "employee_snapshots",
        sa.Column("snapshot_id", UUID(as_uuid=True), primary_key=True),
        sa.Column("employee_id", UUID(as_uuid=True), sa.ForeignKey("employees.employee_id"), nullable=False),
        sa.Column("snapshot_date", sa.Date, nullable=False),
        sa.Column("role_title", sa.Text, nullable=False),
        sa.Column("role_family", sa.Text, nullable=False),
        sa.Column("job_level", sa.Text, nullable=False),
        sa.Column("manager_employee_id", UUID(as_uuid=True), nullable=True),
        sa.Column("team_id", UUID(as_uuid=True), nullable=False),
        sa.Column("org_id", UUID(as_uuid=True), nullable=False),
        sa.Column("performance_rating", sa.Text, nullable=True),
        sa.Column("promotion_readiness", sa.Text, nullable=True),
        sa.Column("flight_risk_flag", sa.Boolean, nullable=True),
        sa.Column("tenure_days", sa.Integer, nullable=False),
        sa.Column("compensation_band", sa.Text, nullable=True),
    )

    # -------------------------------------------------------------------------
    # employee_change_events
    # -------------------------------------------------------------------------
    op.create_table(
        "employee_change_events",
        sa.Column("change_event_id", UUID(as_uuid=True), primary_key=True),
        sa.Column("employee_id", UUID(as_uuid=True), sa.ForeignKey("employees.employee_id"), nullable=False),
        sa.Column("change_type", sa.Text, nullable=False),
        sa.Column("event_date", sa.Date, nullable=False),
        sa.Column("from_value", sa.Text, nullable=True),
        sa.Column("to_value", sa.Text, nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    # -------------------------------------------------------------------------
    # data_generation_runs
    # -------------------------------------------------------------------------
    op.create_table(
        "data_generation_runs",
        sa.Column("run_id", UUID(as_uuid=True), primary_key=True),
        sa.Column("seed", sa.BigInteger, nullable=False),
        sa.Column("start_date", sa.Date, nullable=False),
        sa.Column("end_date", sa.Date, nullable=False),
        sa.Column("employee_count", sa.Integer, nullable=False),
        sa.Column("notes_json", JSONB, nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    # =========================================================================
    # AUTH TABLES
    # =========================================================================

    op.create_table(
        "app_users",
        sa.Column("user_id", UUID(as_uuid=True), primary_key=True),
        sa.Column("employee_id", UUID(as_uuid=True), sa.ForeignKey("employees.employee_id"), nullable=True),
        sa.Column("username", sa.Text, unique=True, nullable=False),
        sa.Column("password_hash", sa.Text, nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "roles",
        sa.Column("role_id", UUID(as_uuid=True), primary_key=True),
        sa.Column("role_name", sa.Text, unique=True, nullable=False),
        sa.Column("description", sa.Text, nullable=True),
    )

    op.create_table(
        "user_roles",
        sa.Column("user_role_id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("app_users.user_id"), nullable=False),
        sa.Column("role_id", UUID(as_uuid=True), sa.ForeignKey("roles.role_id"), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "viewer_permissions",
        sa.Column("permission_id", UUID(as_uuid=True), primary_key=True),
        sa.Column("viewer_user_id", UUID(as_uuid=True), sa.ForeignKey("app_users.user_id"), nullable=False),
        sa.Column("target_scope", sa.Text, nullable=False),
        sa.Column("target_id", UUID(as_uuid=True), nullable=False),
        sa.Column("permission_type", sa.Text, nullable=False),
        sa.Column("granted_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    # access_audit_log: intentionally NO FK to app_users (immutable audit trail)
    op.create_table(
        "access_audit_log",
        sa.Column("audit_id", UUID(as_uuid=True), primary_key=True),
        sa.Column("viewer_user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("accessed_scope", sa.Text, nullable=False),
        sa.Column("accessed_id", UUID(as_uuid=True), nullable=False),
        sa.Column("access_ts", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("action", sa.Text, nullable=False),
        sa.Column("outcome", sa.Text, nullable=False),
        sa.Column("request_id", sa.Text, nullable=True),
        sa.Column("metadata_json", JSONB, nullable=True),
    )

    # =========================================================================
    # INDEXES
    # =========================================================================

    # employees
    op.create_index("idx_employees_team", "employees", ["team_id"])
    op.create_index("idx_employees_org", "employees", ["org_id"])
    op.create_index("idx_employees_manager", "employees", ["manager_employee_id"])

    # interactions — the hottest table for rolling network queries
    op.create_index("idx_interactions_from", "interactions", ["from_employee_id", "interaction_ts"])
    op.create_index("idx_interactions_to", "interactions", ["to_employee_id", "interaction_ts"])

    # artifacts
    op.create_index("idx_artifacts_project", "artifacts", ["project_id"])

    # audit log — viewer + time; accessed object + time
    op.create_index("idx_audit_log_viewer", "access_audit_log", ["viewer_user_id", "access_ts"])
    op.create_index("idx_audit_log_accessed", "access_audit_log", ["accessed_id", "access_ts"])

    # employee_snapshots — queries always filter by employee + date
    op.create_index("idx_snapshots_employee_date", "employee_snapshots", ["employee_id", "snapshot_date"])

    # employee_project_assignments
    op.create_index("idx_assignments_employee", "employee_project_assignments", ["employee_id"])
    op.create_index("idx_assignments_project", "employee_project_assignments", ["project_id"])


def downgrade() -> None:
    # Drop in reverse creation order

    # indexes
    op.drop_index("idx_assignments_project", table_name="employee_project_assignments")
    op.drop_index("idx_assignments_employee", table_name="employee_project_assignments")
    op.drop_index("idx_snapshots_employee_date", table_name="employee_snapshots")
    op.drop_index("idx_audit_log_accessed", table_name="access_audit_log")
    op.drop_index("idx_audit_log_viewer", table_name="access_audit_log")
    op.drop_index("idx_artifacts_project", table_name="artifacts")
    op.drop_index("idx_interactions_to", table_name="interactions")
    op.drop_index("idx_interactions_from", table_name="interactions")
    op.drop_index("idx_employees_manager", table_name="employees")
    op.drop_index("idx_employees_org", table_name="employees")
    op.drop_index("idx_employees_team", table_name="employees")

    # auth tables
    op.drop_table("access_audit_log")
    op.drop_table("viewer_permissions")
    op.drop_table("user_roles")
    op.drop_table("roles")
    op.drop_table("app_users")

    # canonical tables (reverse order)
    op.drop_table("data_generation_runs")
    op.drop_table("employee_change_events")
    op.drop_table("employee_snapshots")
    op.drop_table("interactions")
    op.drop_table("artifact_skill_tags")
    op.drop_table("artifact_contributions")
    op.drop_table("artifacts")
    op.drop_table("project_skill_requirements")
    op.drop_table("employee_skills")
    op.drop_table("employee_project_assignments")
    op.drop_table("projects")
    op.drop_table("repos")

    # drop the deferred FK before dropping employees
    op.drop_constraint("fk_team_leader", "teams", type_="foreignkey")
    op.drop_table("employees")
    op.drop_table("teams")
    op.drop_table("skills")
    op.drop_table("orgs")
