import uuid

from fastapi import APIRouter, HTTPException

from app.dependencies import require_role

router = APIRouter()

_READ_ROLES = ("admin", "org_analytics", "manager", "hrbp")
_WRITE_ROLES = ("admin", "manager", "hrbp")


@router.get("/")
def list_recommendations(
    scope: str | None = None,
    target_scope: str | None = None,
    priority_min: float = 0.0,
    limit: int = 50,
    current_user: dict = require_role(*_READ_ROLES),
) -> list:
    """List actionable recommendations. Implemented in S5."""
    return []


@router.post("/{recommendation_id}/accept")
def accept_recommendation(
    recommendation_id: uuid.UUID,
    current_user: dict = require_role(*_WRITE_ROLES),
) -> dict:
    """Mark a recommendation as accepted. Implemented in S5."""
    raise HTTPException(status_code=404, detail="Not found")
