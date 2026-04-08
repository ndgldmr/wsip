"""
ORM models for Sprint 6 ML and simulation tables.

Six tables:
  - employee_archetype_assignments  — KMeans cluster assignment per employee/date
  - employee_trajectory_predictions — 60-day disengagement/impact predictions
  - employee_prepost_impact_analysis — metric deltas around change events
  - simulation_runs                 — a named simulation scenario
  - simulation_employee_moves       — proposed employee moves within a simulation
  - simulation_outcomes             — computed metric deltas for each move
"""

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Integer, Numeric, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


class EmployeeArchetypeAssignment(Base):
    __tablename__ = "employee_archetype_assignments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("employees.employee_id"), nullable=False)
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False)
    archetype_label: Mapped[str] = mapped_column(Text, nullable=False)
    cluster_id: Mapped[int] = mapped_column(Integer, nullable=False)
    top_signal_1: Mapped[str | None] = mapped_column(Text, nullable=True)
    top_signal_2: Mapped[str | None] = mapped_column(Text, nullable=True)
    top_signal_3: Mapped[str | None] = mapped_column(Text, nullable=True)
    model_version: Mapped[str] = mapped_column(Text, nullable=False, default="wsip-0.1")
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default="now()")


class EmployeeTrajectoryPrediction(Base):
    __tablename__ = "employee_trajectory_predictions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("employees.employee_id"), nullable=False)
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False)
    horizon_days: Mapped[int] = mapped_column(Integer, nullable=False)
    predicted_disengagement_risk: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    predicted_impact_score: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    confidence: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    model_version: Mapped[str] = mapped_column(Text, nullable=False, default="wsip-0.1")
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default="now()")


class EmployeePrePostImpactAnalysis(Base):
    __tablename__ = "employee_prepost_impact_analysis"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    change_event_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("employee_change_events.change_event_id"), nullable=False)
    employee_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("employees.employee_id"), nullable=False)
    metric_name: Mapped[str] = mapped_column(Text, nullable=False)
    pre_mean: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    post_mean: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    delta: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)
    window_days: Mapped[int] = mapped_column(Integer, nullable=False)
    model_version: Mapped[str] = mapped_column(Text, nullable=False, default="wsip-0.1")
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default="now()")


class SimulationRun(Base):
    __tablename__ = "simulation_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="draft")   # draft | computed
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default="now()")
    updated_at: Mapped[datetime] = mapped_column(nullable=False, server_default="now()")


class SimulationEmployeeMove(Base):
    __tablename__ = "simulation_employee_moves"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    simulation_run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("simulation_runs.id"), nullable=False)
    employee_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("employees.employee_id"), nullable=False)
    from_team_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("teams.team_id"), nullable=False)
    to_team_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("teams.team_id"), nullable=False)
    allocation_pct_change: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=Decimal("0"))
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default="now()")


class SimulationOutcome(Base):
    __tablename__ = "simulation_outcomes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    simulation_run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("simulation_runs.id"), nullable=False)
    employee_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("employees.employee_id"), nullable=False)
    metric_name: Mapped[str] = mapped_column(Text, nullable=False)
    baseline_value: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    simulated_value: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    delta: Mapped[Decimal] = mapped_column(Numeric(8, 4), nullable=False)
    team_scope_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("teams.team_id"), nullable=True)
    model_version: Mapped[str] = mapped_column(Text, nullable=False, default="wsip-0.1")
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default="now()")
