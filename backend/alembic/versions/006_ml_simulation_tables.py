"""ML archetype/trajectory/prepost tables + simulation run/move/outcome tables

Revision ID: 006
Revises: 005
Create Date: 2026-04-07
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # employee_archetype_assignments
    # ------------------------------------------------------------------
    op.create_table(
        "employee_archetype_assignments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("employee_id", UUID(as_uuid=True), sa.ForeignKey("employees.employee_id"), nullable=False),
        sa.Column("snapshot_date", sa.Date, nullable=False),
        sa.Column("archetype_label", sa.Text, nullable=False),
        sa.Column("cluster_id", sa.Integer, nullable=False),
        sa.Column("top_signal_1", sa.Text, nullable=True),
        sa.Column("top_signal_2", sa.Text, nullable=True),
        sa.Column("top_signal_3", sa.Text, nullable=True),
        sa.Column("model_version", sa.Text, nullable=False, server_default="wsip-0.1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_unique_constraint(
        "uq_archetype_employee_date",
        "employee_archetype_assignments",
        ["employee_id", "snapshot_date"],
    )
    op.create_index("idx_archetype_snapshot_date", "employee_archetype_assignments", ["snapshot_date"])

    # ------------------------------------------------------------------
    # employee_trajectory_predictions
    # ------------------------------------------------------------------
    op.create_table(
        "employee_trajectory_predictions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("employee_id", UUID(as_uuid=True), sa.ForeignKey("employees.employee_id"), nullable=False),
        sa.Column("snapshot_date", sa.Date, nullable=False),
        sa.Column("horizon_days", sa.Integer, nullable=False),
        sa.Column("predicted_disengagement_risk", sa.Numeric(5, 4), nullable=False),
        sa.Column("predicted_impact_score", sa.Numeric(5, 4), nullable=False),
        sa.Column("confidence", sa.Numeric(5, 4), nullable=False),
        sa.Column("model_version", sa.Text, nullable=False, server_default="wsip-0.1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_unique_constraint(
        "uq_trajectory_employee_date_horizon",
        "employee_trajectory_predictions",
        ["employee_id", "snapshot_date", "horizon_days"],
    )
    op.create_index("idx_trajectory_snapshot_date", "employee_trajectory_predictions", ["snapshot_date"])

    # ------------------------------------------------------------------
    # employee_prepost_impact_analysis
    # ------------------------------------------------------------------
    op.create_table(
        "employee_prepost_impact_analysis",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("change_event_id", UUID(as_uuid=True), sa.ForeignKey("employee_change_events.change_event_id"), nullable=False),
        sa.Column("employee_id", UUID(as_uuid=True), sa.ForeignKey("employees.employee_id"), nullable=False),
        sa.Column("metric_name", sa.Text, nullable=False),
        sa.Column("pre_mean", sa.Numeric(5, 4), nullable=True),
        sa.Column("post_mean", sa.Numeric(5, 4), nullable=True),
        sa.Column("delta", sa.Numeric(8, 4), nullable=True),
        sa.Column("window_days", sa.Integer, nullable=False),
        sa.Column("model_version", sa.Text, nullable=False, server_default="wsip-0.1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("idx_prepost_change_event", "employee_prepost_impact_analysis", ["change_event_id"])
    op.create_index("idx_prepost_employee", "employee_prepost_impact_analysis", ["employee_id"])

    # ------------------------------------------------------------------
    # simulation_runs
    # ------------------------------------------------------------------
    op.create_table(
        "simulation_runs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("created_by", sa.Text, nullable=False),
        sa.Column("status", sa.Text, nullable=False, server_default="draft"),
        sa.Column("snapshot_date", sa.Date, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("idx_simulation_runs_status", "simulation_runs", ["status"])

    # ------------------------------------------------------------------
    # simulation_employee_moves
    # ------------------------------------------------------------------
    op.create_table(
        "simulation_employee_moves",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("simulation_run_id", UUID(as_uuid=True), sa.ForeignKey("simulation_runs.id"), nullable=False),
        sa.Column("employee_id", UUID(as_uuid=True), sa.ForeignKey("employees.employee_id"), nullable=False),
        sa.Column("from_team_id", UUID(as_uuid=True), sa.ForeignKey("teams.team_id"), nullable=False),
        sa.Column("to_team_id", UUID(as_uuid=True), sa.ForeignKey("teams.team_id"), nullable=False),
        sa.Column("allocation_pct_change", sa.Numeric(5, 2), nullable=False, server_default="0"),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("idx_sim_moves_run_id", "simulation_employee_moves", ["simulation_run_id"])

    # ------------------------------------------------------------------
    # simulation_outcomes
    # ------------------------------------------------------------------
    op.create_table(
        "simulation_outcomes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("simulation_run_id", UUID(as_uuid=True), sa.ForeignKey("simulation_runs.id"), nullable=False),
        sa.Column("employee_id", UUID(as_uuid=True), sa.ForeignKey("employees.employee_id"), nullable=False),
        sa.Column("metric_name", sa.Text, nullable=False),
        sa.Column("baseline_value", sa.Numeric(5, 4), nullable=True),
        sa.Column("simulated_value", sa.Numeric(5, 4), nullable=False),
        sa.Column("delta", sa.Numeric(8, 4), nullable=False),
        sa.Column("team_scope_id", UUID(as_uuid=True), sa.ForeignKey("teams.team_id"), nullable=True),
        sa.Column("model_version", sa.Text, nullable=False, server_default="wsip-0.1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("idx_sim_outcomes_run_id", "simulation_outcomes", ["simulation_run_id"])
    op.create_index("idx_sim_outcomes_employee", "simulation_outcomes", ["employee_id"])


def downgrade() -> None:
    op.drop_table("simulation_outcomes")
    op.drop_table("simulation_employee_moves")
    op.drop_table("simulation_runs")
    op.drop_table("employee_prepost_impact_analysis")
    op.drop_table("employee_trajectory_predictions")
    op.drop_table("employee_archetype_assignments")
