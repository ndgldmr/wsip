"""SQLAlchemy 2.0 ORM models for the analytics mart layer.

Mart tables have non-standard PK shapes (integer keys, composite PKs, PKs that
equal source-system IDs) so they do NOT inherit UUIDPKMixin or TimestampMixin.
"""

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import Boolean, Date, ForeignKey, Integer, Numeric, SmallInteger, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


class DimDate(Base):
    __tablename__ = "dim_date"

    date_key: Mapped[int] = mapped_column(Integer, primary_key=True)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    day_of_week: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    day_name: Mapped[str] = mapped_column(Text, nullable=False)
    week_key: Mapped[int] = mapped_column(Integer, nullable=False)
    month_key: Mapped[int] = mapped_column(Integer, nullable=False)
    quarter_key: Mapped[int] = mapped_column(Integer, nullable=False)
    is_weekend: Mapped[bool] = mapped_column(Boolean, nullable=False)


class DimEmployee(Base):
    __tablename__ = "dim_employee"

    employee_key: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    employee_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("employees.employee_id"), nullable=False)
    full_name: Mapped[str] = mapped_column(Text, nullable=False)
    role_family: Mapped[str] = mapped_column(Text, nullable=False)
    job_level: Mapped[str] = mapped_column(Text, nullable=False)
    team_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("teams.team_id"), nullable=False)
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("orgs.org_id"), nullable=False)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class DimTeam(Base):
    __tablename__ = "dim_team"

    team_key: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    team_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("teams.team_id"), nullable=False)
    team_name: Mapped[str] = mapped_column(Text, nullable=False)
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("orgs.org_id"), nullable=False)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class DimProject(Base):
    __tablename__ = "dim_project"

    project_key: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.project_id"), nullable=False)
    project_name: Mapped[str] = mapped_column(Text, nullable=False)
    project_type: Mapped[str] = mapped_column(Text, nullable=False)
    priority_tier: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)


class DimSkill(Base):
    __tablename__ = "dim_skill"

    skill_key: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    skill_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("skills.skill_id"), nullable=False)
    skill_name: Mapped[str] = mapped_column(Text, nullable=False)
    skill_category: Mapped[str] = mapped_column(Text, nullable=False)


class FactEmployeeDailyActivity(Base):
    __tablename__ = "fact_employee_daily_activity"

    date_key: Mapped[int] = mapped_column(Integer, ForeignKey("dim_date.date_key"), primary_key=True)
    employee_key: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("dim_employee.employee_key"), primary_key=True)
    # git
    commit_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    lines_added: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    lines_deleted: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    files_changed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # pull requests
    pr_opened_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    pr_merged_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # code review
    code_review_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    code_review_comment_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # experiments
    experiment_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    compute_hours: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0"))
    # research
    research_artifact_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # docs
    doc_event_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    doc_word_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # tasks
    tasks_opened: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tasks_closed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    story_points_closed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # meetings
    meeting_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    meeting_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    meetings_organized: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # chat
    chat_message_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    chat_after_hours_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # training
    training_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    training_hours: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=Decimal("0"))
    # derived
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    contribution_units: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False, default=Decimal("0"))


class FactEmployeeProjectContribution(Base):
    __tablename__ = "fact_employee_project_contribution"

    date_key: Mapped[int] = mapped_column(Integer, ForeignKey("dim_date.date_key"), primary_key=True)
    employee_key: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("dim_employee.employee_key"), primary_key=True)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.project_id"), primary_key=True)
    contribution_units: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False, default=Decimal("0"))
    code_units: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False, default=Decimal("0"))
    research_units: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False, default=Decimal("0"))
    documentation_units: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False, default=Decimal("0"))
    collaboration_units: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False, default=Decimal("0"))
    impact_units: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False, default=Decimal("0"))


class FactTeamWeeklyHealth(Base):
    __tablename__ = "fact_team_weekly_health"

    week_key: Mapped[int] = mapped_column(Integer, primary_key=True)
    team_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("teams.team_id"), primary_key=True)
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("orgs.org_id"), nullable=False)
    active_employee_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    underutilization_rate: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False, default=Decimal("0"))
    overload_rate: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False, default=Decimal("0"))
    silent_disengagement_rate: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False, default=Decimal("0"))
    burnout_risk_rate: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False, default=Decimal("0"))
    cross_team_collaboration_rate: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False, default=Decimal("0"))
    avg_contribution_units: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False, default=Decimal("0"))
    total_contribution_units: Mapped[Decimal] = mapped_column(Numeric(16, 4), nullable=False, default=Decimal("0"))


class FactEmployeeSkillSignal(Base):
    __tablename__ = "fact_employee_skill_signal"

    date_key: Mapped[int] = mapped_column(Integer, ForeignKey("dim_date.date_key"), primary_key=True)
    employee_key: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("dim_employee.employee_key"), primary_key=True)
    skill_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("skills.skill_id"), primary_key=True)
    training_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    training_hours: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=Decimal("0"))
    code_review_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    experiment_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
