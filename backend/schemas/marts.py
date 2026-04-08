"""
Pydantic v2 response schemas for the analytics mart endpoints.

Numeric rate fields use Decimal to preserve the precision stored in
Numeric(5,4) / Numeric(14,4) columns.  If the frontend requires plain floats
the serialiser can be overridden via model_config json_encoders.
"""

import uuid
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class TeamSummaryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    team_id: uuid.UUID
    team_name: str
    active_employee_count: int
    underutilization_rate: Decimal
    overload_rate: Decimal


class OrgOverviewOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    org_id: uuid.UUID
    org_name: str
    snapshot_date: date
    active_employee_count: int
    underutilization_rate: Decimal
    overload_rate: Decimal
    disengagement_risk_rate: Decimal
    total_contribution_units: Decimal
    teams: list[TeamSummaryOut]


class TeamHealthOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    team_id: uuid.UUID
    team_name: str
    week_key: int
    active_employee_count: int
    underutilization_rate: Decimal
    overload_rate: Decimal
    silent_disengagement_rate: Decimal
    cross_team_collaboration_rate: Decimal
    burnout_risk_rate: Decimal


class EmployeeSummaryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    employee_id: uuid.UUID
    full_name: str
    role_family: str
    job_level: str


class TeamTrendPointOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    week_key: int
    underutilization_rate: Decimal
    overload_rate: Decimal
    silent_disengagement_rate: Decimal
    burnout_risk_rate: Decimal
