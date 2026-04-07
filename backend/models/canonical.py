"""
Canonical core tables — the normalized domain model.

Creation order respects FK dependencies:
  Org → Skill → Team → Employee → Repo → Project →
  EmployeeProjectAssignment, EmployeeSkill, ProjectSkillRequirement →
  Artifact → ArtifactContribution, ArtifactSkillTag →
  Interaction, EmployeeSnapshot, EmployeeChangeEvent, DataGenerationRun
"""

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base


class Org(Base):
    __tablename__ = "orgs"

    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_name: Mapped[str] = mapped_column(Text, nullable=False)
    parent_org_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("orgs.org_id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default="now()")

    parent: Mapped["Org | None"] = relationship("Org", remote_side="Org.org_id", foreign_keys=[parent_org_id])
    teams: Mapped[list["Team"]] = relationship("Team", back_populates="org", foreign_keys="Team.org_id")


class Skill(Base):
    __tablename__ = "skills"

    skill_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    skill_name: Mapped[str] = mapped_column(Text, nullable=False)
    skill_category: Mapped[str] = mapped_column(Text, nullable=False)
    parent_skill_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("skills.skill_id"), nullable=True)

    parent: Mapped["Skill | None"] = relationship("Skill", remote_side="Skill.skill_id", foreign_keys=[parent_skill_id])


class Team(Base):
    __tablename__ = "teams"

    team_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    team_name: Mapped[str] = mapped_column(Text, nullable=False)
    parent_team_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("teams.team_id"), nullable=True)
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("orgs.org_id"), nullable=False)
    function_type: Mapped[str] = mapped_column(Text, nullable=False)
    mission_area: Mapped[str | None] = mapped_column(Text, nullable=True)
    leader_employee_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("employees.employee_id", use_alter=True, name="fk_team_leader"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default="now()")
    updated_at: Mapped[datetime] = mapped_column(nullable=False, server_default="now()")

    org: Mapped["Org"] = relationship("Org", back_populates="teams", foreign_keys=[org_id])
    parent: Mapped["Team | None"] = relationship("Team", remote_side="Team.team_id", foreign_keys=[parent_team_id])
    employees: Mapped[list["Employee"]] = relationship("Employee", back_populates="team", foreign_keys="Employee.team_id")


class Employee(Base):
    __tablename__ = "employees"

    employee_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    external_employee_ref: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(Text, nullable=False)
    preferred_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    email: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    role_title: Mapped[str] = mapped_column(Text, nullable=False)
    role_family: Mapped[str] = mapped_column(Text, nullable=False)
    job_level: Mapped[str] = mapped_column(Text, nullable=False)
    employment_status: Mapped[str] = mapped_column(Text, nullable=False, default="active")
    manager_employee_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("employees.employee_id"), nullable=True)
    team_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("teams.team_id"), nullable=False)
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("orgs.org_id"), nullable=False)
    location: Mapped[str | None] = mapped_column(Text, nullable=True)
    hire_date: Mapped[date] = mapped_column(Date, nullable=False)
    exit_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    compensation_band: Mapped[str | None] = mapped_column(Text, nullable=True)
    clearance_tier: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default="now()")
    updated_at: Mapped[datetime] = mapped_column(nullable=False, server_default="now()")

    manager: Mapped["Employee | None"] = relationship("Employee", remote_side="Employee.employee_id", foreign_keys=[manager_employee_id])
    team: Mapped["Team"] = relationship("Team", back_populates="employees", foreign_keys=[team_id])
    direct_reports: Mapped[list["Employee"]] = relationship("Employee", foreign_keys=[manager_employee_id])


class Repo(Base):
    __tablename__ = "repos"

    repo_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_system: Mapped[str] = mapped_column(Text, nullable=False)
    repo_name: Mapped[str] = mapped_column(Text, nullable=False)
    owning_team_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("teams.team_id"), nullable=True)
    is_monorepo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default="now()")


class Project(Base):
    __tablename__ = "projects"

    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_name: Mapped[str] = mapped_column(Text, nullable=False)
    project_type: Mapped[str] = mapped_column(Text, nullable=False)
    priority_tier: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="active")
    owner_employee_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("employees.employee_id"), nullable=True)
    owning_team_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("teams.team_id"), nullable=False)
    strategic_area: Mapped[str | None] = mapped_column(Text, nullable=True)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    target_end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default="now()")
    updated_at: Mapped[datetime] = mapped_column(nullable=False, server_default="now()")


class EmployeeProjectAssignment(Base):
    __tablename__ = "employee_project_assignments"

    assignment_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("employees.employee_id"), nullable=False)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.project_id"), nullable=False)
    assignment_role: Mapped[str] = mapped_column(Text, nullable=False)
    allocation_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    staffing_source: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default="now()")


class EmployeeSkill(Base):
    __tablename__ = "employee_skills"

    employee_skill_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("employees.employee_id"), nullable=False)
    skill_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("skills.skill_id"), nullable=False)
    proficiency_level: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_type: Mapped[str] = mapped_column(Text, nullable=False)
    confidence_score: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    valid_from: Mapped[date] = mapped_column(Date, nullable=False)
    valid_to: Mapped[date | None] = mapped_column(Date, nullable=True)


class ProjectSkillRequirement(Base):
    __tablename__ = "project_skill_requirements"

    project_skill_req_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.project_id"), nullable=False)
    skill_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("skills.skill_id"), nullable=False)
    desired_level: Mapped[str] = mapped_column(Text, nullable=False)
    weight: Mapped[Decimal] = mapped_column(Numeric(6, 4), nullable=False)
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default="now()")


class Artifact(Base):
    __tablename__ = "artifacts"

    artifact_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    artifact_type: Mapped[str] = mapped_column(Text, nullable=False)
    source_system: Mapped[str] = mapped_column(Text, nullable=False)
    source_artifact_ref: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_employee_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("employees.employee_id"), nullable=True)
    owning_team_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("teams.team_id"), nullable=True)
    project_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.project_id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default="now()")
    updated_at: Mapped[datetime] = mapped_column(nullable=False, server_default="now()")


class ArtifactContribution(Base):
    __tablename__ = "artifact_contributions"

    contribution_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    artifact_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("artifacts.artifact_id"), nullable=False)
    employee_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("employees.employee_id"), nullable=False)
    contribution_type: Mapped[str] = mapped_column(Text, nullable=False)
    contribution_weight: Mapped[Decimal] = mapped_column(Numeric(8, 4), nullable=False)
    contribution_ts: Mapped[datetime] = mapped_column(nullable=False)


class ArtifactSkillTag(Base):
    __tablename__ = "artifact_skill_tags"

    artifact_skill_tag_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    artifact_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("artifacts.artifact_id"), nullable=False)
    skill_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("skills.skill_id"), nullable=False)
    tag_source: Mapped[str] = mapped_column(Text, nullable=False)
    confidence_score: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default="now()")


class Interaction(Base):
    __tablename__ = "interactions"

    interaction_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    interaction_type: Mapped[str] = mapped_column(Text, nullable=False)
    source_system: Mapped[str] = mapped_column(Text, nullable=False)
    from_employee_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("employees.employee_id"), nullable=False)
    to_employee_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("employees.employee_id"), nullable=False)
    project_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.project_id"), nullable=True)
    artifact_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("artifacts.artifact_id"), nullable=True)
    interaction_ts: Mapped[datetime] = mapped_column(nullable=False)
    interaction_weight: Mapped[Decimal] = mapped_column(Numeric(8, 4), nullable=False, default=Decimal("1.0000"))
    metadata_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)


class EmployeeSnapshot(Base):
    __tablename__ = "employee_snapshots"

    snapshot_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("employees.employee_id"), nullable=False)
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False)
    role_title: Mapped[str] = mapped_column(Text, nullable=False)
    role_family: Mapped[str] = mapped_column(Text, nullable=False)
    job_level: Mapped[str] = mapped_column(Text, nullable=False)
    manager_employee_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    team_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    performance_rating: Mapped[str | None] = mapped_column(Text, nullable=True)
    promotion_readiness: Mapped[str | None] = mapped_column(Text, nullable=True)
    flight_risk_flag: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    tenure_days: Mapped[int] = mapped_column(Integer, nullable=False)
    compensation_band: Mapped[str | None] = mapped_column(Text, nullable=True)


class EmployeeChangeEvent(Base):
    __tablename__ = "employee_change_events"

    change_event_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("employees.employee_id"), nullable=False)
    change_type: Mapped[str] = mapped_column(Text, nullable=False)
    event_date: Mapped[date] = mapped_column(Date, nullable=False)
    from_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    to_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default="now()")


class DataGenerationRun(Base):
    __tablename__ = "data_generation_runs"

    run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    seed: Mapped[int] = mapped_column(Integer, nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    employee_count: Mapped[int] = mapped_column(Integer, nullable=False)
    notes_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default="now()")
