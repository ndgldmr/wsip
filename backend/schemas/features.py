"""
Pydantic v2 response schemas for employee feature endpoints.

`EmployeeProfileOut` blends identity columns from `Employee` + `Team`
with feature/metric columns from `EmployeeFeatureSnapshot`.  The router
constructs this from a JOIN rather than from a single ORM row, so the
schema does NOT use `from_attributes=True` — values are set explicitly.

`DailyActivityOut` maps directly from `FactEmployeeDailyActivity` rows.
"""

import uuid
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class EmployeeProfileOut(BaseModel):
    # identity
    employee_id: uuid.UUID
    full_name: str
    role_title: str
    role_family: str
    job_level: str
    team_name: str
    snapshot_date: date

    # metric scores
    underutilization_score: float
    overload_score: float
    disengagement_risk_score: float
    skill_utilization_score: float
    glue_person_score: float

    # 30-day rolling features
    commits_30d: int
    prs_merged_30d: int
    meeting_load_hours_30d: float
    collaboration_breadth_30d: int
    experiment_runs_30d: int

    # baseline comparisons (None when insufficient history)
    commits_30d_vs_self_baseline: float | None
    commits_30d_vs_role_baseline: float | None

    # archetype label (populated by Sprint 6 clustering)
    archetype_label: str | None


class DailyActivityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    date_key: int
    commit_count: int
    pr_opened_count: int
    pr_merged_count: int
    code_review_count: int
    experiment_count: int
    research_artifact_count: int
    doc_event_count: int
    meeting_count: int
    meeting_minutes: int
    chat_message_count: int
    is_active: bool
    contribution_units: Decimal
