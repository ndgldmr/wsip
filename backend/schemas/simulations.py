"""
Pydantic v2 schemas for simulation endpoints (Sprint 6).
"""

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


# ---------------------------------------------------------------------------
# Input schemas
# ---------------------------------------------------------------------------

class SimulationCreateIn(BaseModel):
    name: str
    description: str | None = None
    snapshot_date: date


class SimulationMoveIn(BaseModel):
    employee_id: uuid.UUID
    from_team_id: uuid.UUID
    to_team_id: uuid.UUID
    allocation_pct_change: float = 0.0
    notes: str | None = None


# ---------------------------------------------------------------------------
# Output schemas
# ---------------------------------------------------------------------------

class SimulationRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None
    status: str
    snapshot_date: date
    created_by: str
    created_at: datetime


class SimulationMoveOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    simulation_run_id: uuid.UUID
    employee_id: uuid.UUID
    from_team_id: uuid.UUID
    to_team_id: uuid.UUID
    allocation_pct_change: Decimal
    notes: str | None


class SimulationOutcomeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    simulation_run_id: uuid.UUID
    employee_id: uuid.UUID
    metric_name: str
    baseline_value: Decimal | None
    simulated_value: Decimal
    delta: Decimal
    team_scope_id: uuid.UUID | None
