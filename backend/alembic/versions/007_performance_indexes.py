"""Performance indexes for key query paths.

Revision ID: 007
Revises: 006
Create Date: 2026-04-08
"""

from alembic import op

revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Employee feature snapshots — primary lookup path for /employees/{id}/profile
    op.create_index(
        "idx_feat_snap_emp_date",
        "employee_feature_snapshots",
        ["employee_id", "snapshot_date"],
    )

    # Team weekly health — /teams/{id}/health and org overview aggregation
    op.create_index(
        "idx_fact_twh_team_week",
        "fact_team_weekly_health",
        ["team_id", "week_key"],
    )
    op.create_index(
        "idx_fact_twh_org_week",
        "fact_team_weekly_health",
        ["org_id", "week_key"],
    )

    # Dim employee current flag — filtered in nearly every employee query
    op.create_index(
        "idx_dim_emp_current",
        "dim_employee",
        ["is_current"],
    )

    # Insights list — filtered by scope_id + date + active flag
    op.create_index(
        "idx_insight_scope_date",
        "insights",
        ["scope_id", "snapshot_date", "is_active"],
    )

    # Recommendations list — sorted by priority DESC
    op.create_index(
        "idx_rec_priority",
        "recommendations",
        ["priority"],
        postgresql_ops={"priority": "DESC"},
    )

    # Audit log — filtered by accessed_id in the new admin endpoint
    op.create_index(
        "idx_audit_accessed",
        "access_audit_log",
        ["accessed_id", "access_ts"],
        postgresql_ops={"access_ts": "DESC"},
    )

    # Fact daily activity — employee timeline lookups
    op.create_index(
        "idx_fact_daily_emp_date",
        "fact_employee_daily_activity",
        ["employee_key", "date_key"],
    )


def downgrade() -> None:
    op.drop_index("idx_fact_daily_emp_date", table_name="fact_employee_daily_activity")
    op.drop_index("idx_audit_accessed",      table_name="access_audit_log")
    op.drop_index("idx_rec_priority",        table_name="recommendations")
    op.drop_index("idx_insight_scope_date",  table_name="insights")
    op.drop_index("idx_dim_emp_current",     table_name="dim_employee")
    op.drop_index("idx_fact_twh_org_week",   table_name="fact_team_weekly_health")
    op.drop_index("idx_fact_twh_team_week",  table_name="fact_team_weekly_health")
    op.drop_index("idx_feat_snap_emp_date",  table_name="employee_feature_snapshots")
