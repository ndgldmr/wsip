import uuid
from datetime import date

from fastapi import APIRouter, HTTPException

from app.dependencies import require_role

router = APIRouter()

_ROLES = ("admin", "org_analytics", "manager")


@router.get("/{team_id}/health")
def get_team_health(
    team_id: uuid.UUID,
    week_key: int,
    current_user: dict = require_role(*_ROLES),
) -> dict:
    """Team weekly health metrics. Implemented in S3."""
    raise HTTPException(status_code=404, detail="Not found")


@router.get("/{team_id}/members")
def list_team_members(
    team_id: uuid.UUID,
    as_of: date,
    current_user: dict = require_role(*_ROLES),
) -> list:
    """Team member list with summary metrics. Implemented in S3."""
    raise HTTPException(status_code=404, detail="Not found")


@router.get("/{team_id}/trends")
def get_team_trends(
    team_id: uuid.UUID,
    from_week: int,
    to_week: int,
    current_user: dict = require_role(*_ROLES),
) -> list:
    """Weekly trend data for a team. Implemented in S3."""
    raise HTTPException(status_code=404, detail="Not found")
