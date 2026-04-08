"""mart dimension and fact tables

Revision ID: 003
Revises: 002
Create Date: 2026-04-07
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # -------------------------------------------------------------------------
    # dim_date  — integer PK (YYYYMMDD), no FKs
    # -------------------------------------------------------------------------
    op.create_table(
        "dim_date",
        sa.Column("date_key", sa.Integer, primary_key=True),
        sa.Column("date", sa.Date, nullable=False),
        sa.Column("day_of_week", sa.SmallInteger, nullable=False),  # 0=Mon … 6=Sun
        sa.Column("day_name", sa.Text, nullable=False),
        sa.Column("week_key", sa.Integer, nullable=False),           # ISO: YYYYWW
        sa.Column("month_key", sa.Integer, nullable=False),          # YYYYMM
        sa.Column("quarter_key", sa.Integer, nullable=False),        # YYYYQ
        sa.Column("is_weekend", sa.Boolean, nullable=False),
    )
    op.create_index("idx_dim_date_week_key", "dim_date", ["week_key"])
    op.create_index("idx_dim_date_month_key", "dim_date", ["month_key"])

    # -------------------------------------------------------------------------
    # dim_employee  — SCD1: employee_key = employee_id
    # -------------------------------------------------------------------------
    op.create_table(
        "dim_employee",
        sa.Column("employee_key", UUID(as_uuid=True), primary_key=True),
        sa.Column("employee_id", UUID(as_uuid=True), sa.ForeignKey("employees.employee_id"), nullable=False),
        sa.Column("full_name", sa.Text, nullable=False),
        sa.Column("role_family", sa.Text, nullable=False),
        sa.Column("job_level", sa.Text, nullable=False),
        sa.Column("team_id", UUID(as_uuid=True), sa.ForeignKey("teams.team_id"), nullable=False),
        sa.Column("org_id", UUID(as_uuid=True), sa.ForeignKey("orgs.org_id"), nullable=False),
        sa.Column("effective_from", sa.Date, nullable=False),
        sa.Column("effective_to", sa.Date, nullable=True),
        sa.Column("is_current", sa.Boolean, nullable=False, server_default="true"),
    )
    op.create_index("idx_dim_employee_team", "dim_employee", ["team_id"])
    op.create_index("idx_dim_employee_org", "dim_employee", ["org_id"])
    op.create_index("idx_dim_employee_is_current", "dim_employee", ["is_current"])

    # -------------------------------------------------------------------------
    # dim_team
    # -------------------------------------------------------------------------
    op.create_table(
        "dim_team",
        sa.Column("team_key", UUID(as_uuid=True), primary_key=True),
        sa.Column("team_id", UUID(as_uuid=True), sa.ForeignKey("teams.team_id"), nullable=False),
        sa.Column("team_name", sa.Text, nullable=False),
        sa.Column("org_id", UUID(as_uuid=True), sa.ForeignKey("orgs.org_id"), nullable=False),
        sa.Column("effective_from", sa.Date, nullable=False),
        sa.Column("effective_to", sa.Date, nullable=True),
        sa.Column("is_current", sa.Boolean, nullable=False, server_default="true"),
    )
    op.create_index("idx_dim_team_org", "dim_team", ["org_id"])
    op.create_index("idx_dim_team_is_current", "dim_team", ["is_current"])

    # -------------------------------------------------------------------------
    # dim_project
    # -------------------------------------------------------------------------
    op.create_table(
        "dim_project",
        sa.Column("project_key", UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("projects.project_id"), nullable=False),
        sa.Column("project_name", sa.Text, nullable=False),
        sa.Column("project_type", sa.Text, nullable=False),
        sa.Column("priority_tier", sa.Text, nullable=False),
        sa.Column("status", sa.Text, nullable=False),
    )
    op.create_index("idx_dim_project_status", "dim_project", ["status"])

    # -------------------------------------------------------------------------
    # dim_skill
    # -------------------------------------------------------------------------
    op.create_table(
        "dim_skill",
        sa.Column("skill_key", UUID(as_uuid=True), primary_key=True),
        sa.Column("skill_id", UUID(as_uuid=True), sa.ForeignKey("skills.skill_id"), nullable=False),
        sa.Column("skill_name", sa.Text, nullable=False),
        sa.Column("skill_category", sa.Text, nullable=False),
    )
    op.create_index("idx_dim_skill_category", "dim_skill", ["skill_category"])

    # -------------------------------------------------------------------------
    # fact_employee_daily_activity  — composite PK (date_key, employee_key)
    # -------------------------------------------------------------------------
    op.create_table(
        "fact_employee_daily_activity",
        sa.Column("date_key", sa.Integer, sa.ForeignKey("dim_date.date_key"), primary_key=True, nullable=False),
        sa.Column("employee_key", UUID(as_uuid=True), sa.ForeignKey("dim_employee.employee_key"), primary_key=True, nullable=False),
        # git
        sa.Column("commit_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("lines_added", sa.Integer, nullable=False, server_default="0"),
        sa.Column("lines_deleted", sa.Integer, nullable=False, server_default="0"),
        sa.Column("files_changed", sa.Integer, nullable=False, server_default="0"),
        # pull requests
        sa.Column("pr_opened_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("pr_merged_count", sa.Integer, nullable=False, server_default="0"),
        # code review
        sa.Column("code_review_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("code_review_comment_count", sa.Integer, nullable=False, server_default="0"),
        # experiments
        sa.Column("experiment_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("compute_hours", sa.Numeric(12, 2), nullable=False, server_default="0"),
        # research
        sa.Column("research_artifact_count", sa.Integer, nullable=False, server_default="0"),
        # docs
        sa.Column("doc_event_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("doc_word_count", sa.Integer, nullable=False, server_default="0"),
        # tasks
        sa.Column("tasks_opened", sa.Integer, nullable=False, server_default="0"),
        sa.Column("tasks_closed", sa.Integer, nullable=False, server_default="0"),
        sa.Column("story_points_closed", sa.Integer, nullable=False, server_default="0"),
        # meetings
        sa.Column("meeting_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("meeting_minutes", sa.Integer, nullable=False, server_default="0"),
        sa.Column("meetings_organized", sa.Integer, nullable=False, server_default="0"),
        # chat
        sa.Column("chat_message_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("chat_after_hours_count", sa.Integer, nullable=False, server_default="0"),
        # training
        sa.Column("training_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("training_hours", sa.Numeric(10, 2), nullable=False, server_default="0"),
        # derived
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("contribution_units", sa.Numeric(14, 4), nullable=False, server_default="0"),
    )
    op.create_index(
        "idx_fact_daily_employee",
        "fact_employee_daily_activity",
        ["employee_key", "date_key"],
    )

    # -------------------------------------------------------------------------
    # fact_employee_project_contribution  — composite PK (date_key, employee_key, project_id)
    # -------------------------------------------------------------------------
    op.create_table(
        "fact_employee_project_contribution",
        sa.Column("date_key", sa.Integer, sa.ForeignKey("dim_date.date_key"), primary_key=True, nullable=False),
        sa.Column("employee_key", UUID(as_uuid=True), sa.ForeignKey("dim_employee.employee_key"), primary_key=True, nullable=False),
        sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("projects.project_id"), primary_key=True, nullable=False),
        sa.Column("contribution_units", sa.Numeric(14, 4), nullable=False, server_default="0"),
        sa.Column("code_units", sa.Numeric(12, 4), nullable=False, server_default="0"),
        sa.Column("research_units", sa.Numeric(12, 4), nullable=False, server_default="0"),
        sa.Column("documentation_units", sa.Numeric(12, 4), nullable=False, server_default="0"),
        sa.Column("collaboration_units", sa.Numeric(12, 4), nullable=False, server_default="0"),
        sa.Column("impact_units", sa.Numeric(12, 4), nullable=False, server_default="0"),
    )
    op.create_index(
        "idx_fact_proj_contrib_project",
        "fact_employee_project_contribution",
        ["project_id", "date_key"],
    )

    # -------------------------------------------------------------------------
    # fact_team_weekly_health  — composite PK (week_key, team_id)
    # -------------------------------------------------------------------------
    op.create_table(
        "fact_team_weekly_health",
        sa.Column("week_key", sa.Integer, primary_key=True, nullable=False),
        sa.Column("team_id", UUID(as_uuid=True), sa.ForeignKey("teams.team_id"), primary_key=True, nullable=False),
        sa.Column("org_id", UUID(as_uuid=True), sa.ForeignKey("orgs.org_id"), nullable=False),
        sa.Column("active_employee_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("underutilization_rate", sa.Numeric(5, 4), nullable=False, server_default="0"),
        sa.Column("overload_rate", sa.Numeric(5, 4), nullable=False, server_default="0"),
        sa.Column("silent_disengagement_rate", sa.Numeric(5, 4), nullable=False, server_default="0"),
        sa.Column("burnout_risk_rate", sa.Numeric(5, 4), nullable=False, server_default="0"),
        sa.Column("cross_team_collaboration_rate", sa.Numeric(5, 4), nullable=False, server_default="0"),
        sa.Column("avg_contribution_units", sa.Numeric(14, 4), nullable=False, server_default="0"),
        sa.Column("total_contribution_units", sa.Numeric(16, 4), nullable=False, server_default="0"),
    )
    op.create_index(
        "idx_fact_team_weekly_org",
        "fact_team_weekly_health",
        ["org_id", "week_key"],
    )

    # -------------------------------------------------------------------------
    # fact_employee_skill_signal  — composite PK (date_key, employee_key, skill_id)
    # -------------------------------------------------------------------------
    op.create_table(
        "fact_employee_skill_signal",
        sa.Column("date_key", sa.Integer, sa.ForeignKey("dim_date.date_key"), primary_key=True, nullable=False),
        sa.Column("employee_key", UUID(as_uuid=True), sa.ForeignKey("dim_employee.employee_key"), primary_key=True, nullable=False),
        sa.Column("skill_id", UUID(as_uuid=True), sa.ForeignKey("skills.skill_id"), primary_key=True, nullable=False),
        sa.Column("training_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("training_hours", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("code_review_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("experiment_count", sa.Integer, nullable=False, server_default="0"),
    )
    op.create_index(
        "idx_fact_skill_signal_skill",
        "fact_employee_skill_signal",
        ["skill_id", "date_key"],
    )


def downgrade() -> None:
    # Drop facts first (they FK into dims), then dims in reverse creation order
    op.drop_table("fact_employee_skill_signal")
    op.drop_table("fact_team_weekly_health")
    op.drop_table("fact_employee_project_contribution")
    op.drop_table("fact_employee_daily_activity")
    op.drop_table("dim_skill")
    op.drop_table("dim_project")
    op.drop_table("dim_team")
    op.drop_table("dim_employee")
    op.drop_table("dim_date")
