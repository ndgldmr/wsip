import uuid
from datetime import date

from fastapi import APIRouter

from app.dependencies import require_role

router = APIRouter()

_ROLES = ("admin", "org_analytics", "manager")


@router.get("/{org_id}/overview")
def get_org_overview(
    org_id: uuid.UUID,
    as_of: date,
    current_user: dict = require_role(*_ROLES),
) -> dict:
    """Org-level KPI overview. Implemented in S3."""
    raise __import__("fastapi").HTTPException(status_code=404, detail="Not found")


@router.get("/{org_id}/teams")
def list_org_teams(
    org_id: uuid.UUID,
    as_of: date,
    current_user: dict = require_role(*_ROLES),
) -> list:
    """List teams under an org. Implemented in S3."""
    raise __import__("fastapi").HTTPException(status_code=404, detail="Not found")
