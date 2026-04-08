"""
Pydantic output schemas for insights and recommendations endpoints.
"""

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class InsightOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    scope: str
    scope_id: uuid.UUID
    insight_type: str
    snapshot_date: date
    severity: str
    title: str
    insight_description: str
    confidence: Decimal
    is_active: bool


class RecommendationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    insight_id: uuid.UUID
    action_type: str
    priority: Decimal
    target_scope: str
    accepted_flag: bool
    accepted_at: datetime | None
    accepted_by: str | None
