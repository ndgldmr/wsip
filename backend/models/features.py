"""
Employee feature snapshot model — one row per (employee, snapshot_date).

Feature columns are populated by etl/features.py (rolling aggregates + baselines).
Metric score columns are written back by etl/metrics.py in a second pass.
"""

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Integer, Numeric, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


class EmployeeFeatureSnapshot(Base):
    __tablename__ = "employee_feature_snapshots"

    # --- identity / link ---
    employee_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("employees.employee_id"), primary_key=True)
    snapshot_date: Mapped[date] = mapped_column(Date, primary_key=True)
    employee_key: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("dim_employee.employee_key"), nullable=True)

    # --- 7-day rolling ---
    commits_7d: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    prs_7d: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reviews_7d: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    meeting_hours_7d: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False, default=Decimal("0"))
    activity_score_7d: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False, default=Decimal("0"))

    # --- 14-day ---
    activity_drop_14d: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)

    # --- 30-day rolling ---
    commits_30d: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    prs_merged_30d: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reviews_30d: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    experiment_runs_30d: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    meeting_load_hours_30d: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False, default=Decimal("0"))
    collaboration_breadth_30d: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cross_team_interaction_rate_30d: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False, default=Decimal("0"))
    collaboration_centrality_30d: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False, default=Decimal("0"))
    knowledge_creation_score: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False, default=Decimal("0"))
    activity_score_30d: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False, default=Decimal("0"))
    activity_drop_30d: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)

    # --- 90-day rolling ---
    commits_90d: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    activity_score_90d: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False, default=Decimal("0"))

    # --- allocation & skills ---
    active_project_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    project_allocation_utilization_score: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False, default=Decimal("0"))
    skill_utilization_score: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False, default=Decimal("0"))
    skill_depth_score: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False, default=Decimal("0"))

    # --- baselines (signed: negative = below baseline, positive = above) ---
    commits_30d_vs_self_baseline: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)
    commits_30d_vs_role_baseline: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)
    activity_30d_vs_self_baseline: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)

    # --- metric scores (null until metrics step runs) ---
    underutilization_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    overload_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    disengagement_risk_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    glue_person_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)

    # --- archetype (Sprint 6) ---
    archetype_label: Mapped[str | None] = mapped_column(Text, nullable=True)
