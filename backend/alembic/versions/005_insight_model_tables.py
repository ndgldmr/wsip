"""insights and recommendations tables

Revision ID: 005
Revises: 004
Create Date: 2026-04-07
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "insights",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("scope", sa.Text, nullable=False),
        sa.Column("scope_id", UUID(as_uuid=True), nullable=False),
        sa.Column("insight_type", sa.Text, nullable=False),
        sa.Column("snapshot_date", sa.Date, nullable=False),
        sa.Column("severity", sa.Text, nullable=False),
        sa.Column("title", sa.Text, nullable=False),
        sa.Column("insight_description", sa.Text, nullable=False),
        sa.Column("confidence", sa.Numeric(5, 4), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_unique_constraint(
        "uq_insight_scope_type_date", "insights",
        ["scope_id", "insight_type", "snapshot_date"],
    )
    op.create_index("idx_insights_snapshot_severity", "insights", ["snapshot_date", "severity"])
    op.create_index("idx_insights_scope_id", "insights", ["scope_id"])

    op.create_table(
        "recommendations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("insight_id", UUID(as_uuid=True), sa.ForeignKey("insights.id"), nullable=False),
        sa.Column("action_type", sa.Text, nullable=False),
        sa.Column("priority", sa.Numeric(5, 4), nullable=False),
        sa.Column("target_scope", sa.Text, nullable=False),
        sa.Column("accepted_flag", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("accepted_by", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("idx_recommendations_insight_id", "recommendations", ["insight_id"])
    op.create_index("idx_recommendations_accepted", "recommendations", ["accepted_flag"])


def downgrade() -> None:
    op.drop_table("recommendations")
    op.drop_table("insights")
