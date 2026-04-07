import uuid
from datetime import date

from fastapi import APIRouter, HTTPException

from app.dependencies import require_role

router = APIRouter()

_ROLES = ("admin", "org_analytics", "manager", "hrbp")


@router.get("/")
def list_insights(
    scope: str | None = None,
    scope_id: uuid.UUID | None = None,
    insight_type: str | None = None,
    severity: str | None = None,
    as_of: date | None = None,
    limit: int = 50,
    current_user: dict = require_role(*_ROLES),
) -> list:
    """List insights with optional filters. Implemented in S5."""
    return []


@router.get("/{insight_id}")
def get_insight(
    insight_id: uuid.UUID,
    current_user: dict = require_role(*_ROLES),
) -> dict:
    """Get a single insight. Implemented in S5."""
    raise HTTPException(status_code=404, detail="Not found")
