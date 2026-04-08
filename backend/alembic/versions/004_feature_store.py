"""employee feature snapshots table

Revision ID: 004
Revises: 003
Create Date: 2026-04-07
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "employee_feature_snapshots",
        # --- identity / link ---
        sa.Column("employee_id", UUID(as_uuid=True), sa.ForeignKey("employees.employee_id"), primary_key=True, nullable=False),
        sa.Column("snapshot_date", sa.Date, primary_key=True, nullable=False),
        sa.Column("employee_key", UUID(as_uuid=True), sa.ForeignKey("dim_employee.employee_key"), nullable=True),

        # --- 7-day rolling ---
        sa.Column("commits_7d", sa.Integer, nullable=False, server_default="0"),
        sa.Column("prs_7d", sa.Integer, nullable=False, server_default="0"),
        sa.Column("reviews_7d", sa.Integer, nullable=False, server_default="0"),
        sa.Column("meeting_hours_7d", sa.Numeric(8, 2), nullable=False, server_default="0"),
        sa.Column("activity_score_7d", sa.Numeric(5, 4), nullable=False, server_default="0"),

        # --- 14-day ---
        sa.Column("activity_drop_14d", sa.Numeric(8, 4), nullable=True),   # signed: negative = drop

        # --- 30-day rolling ---
        sa.Column("commits_30d", sa.Integer, nullable=False, server_default="0"),
        sa.Column("prs_merged_30d", sa.Integer, nullable=False, server_default="0"),
        sa.Column("reviews_30d", sa.Integer, nullable=False, server_default="0"),
        sa.Column("experiment_runs_30d", sa.Integer, nullable=False, server_default="0"),
        sa.Column("meeting_load_hours_30d", sa.Numeric(8, 2), nullable=False, server_default="0"),
        sa.Column("collaboration_breadth_30d", sa.Integer, nullable=False, server_default="0"),
        sa.Column("cross_team_interaction_rate_30d", sa.Numeric(5, 4), nullable=False, server_default="0"),
        sa.Column("collaboration_centrality_30d", sa.Numeric(5, 4), nullable=False, server_default="0"),
        sa.Column("knowledge_creation_score", sa.Numeric(5, 4), nullable=False, server_default="0"),
        sa.Column("activity_score_30d", sa.Numeric(5, 4), nullable=False, server_default="0"),
        sa.Column("activity_drop_30d", sa.Numeric(8, 4), nullable=True),   # signed

        # --- 90-day rolling ---
        sa.Column("commits_90d", sa.Integer, nullable=False, server_default="0"),
        sa.Column("activity_score_90d", sa.Numeric(5, 4), nullable=False, server_default="0"),

        # --- allocation & skills ---
        sa.Column("active_project_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("project_allocation_utilization_score", sa.Numeric(5, 4), nullable=False, server_default="0"),
        sa.Column("skill_utilization_score", sa.Numeric(5, 4), nullable=False, server_default="0"),
        sa.Column("skill_depth_score", sa.Numeric(5, 4), nullable=False, server_default="0"),

        # --- baselines (signed ratios: 0.0 = at baseline, negative = below, positive = above) ---
        sa.Column("commits_30d_vs_self_baseline", sa.Numeric(8, 4), nullable=True),
        sa.Column("commits_30d_vs_role_baseline", sa.Numeric(8, 4), nullable=True),
        sa.Column("activity_30d_vs_self_baseline", sa.Numeric(8, 4), nullable=True),

        # --- metric scores (written by metrics step; null until metrics run) ---
        sa.Column("underutilization_score", sa.Numeric(5, 4), nullable=True),
        sa.Column("overload_score", sa.Numeric(5, 4), nullable=True),
        sa.Column("disengagement_risk_score", sa.Numeric(5, 4), nullable=True),
        sa.Column("glue_person_score", sa.Numeric(5, 4), nullable=True),

        # --- archetype label (written by Sprint 6 clustering) ---
        sa.Column("archetype_label", sa.Text, nullable=True),
    )
    op.create_index("idx_efs_snapshot_date", "employee_feature_snapshots", ["snapshot_date"])
    op.create_index("idx_efs_employee_id", "employee_feature_snapshots", ["employee_id"])


def downgrade() -> None:
    op.drop_table("employee_feature_snapshots")
