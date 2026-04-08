"""
Recommendations router — actionable recommendation listing and accept endpoints.

Read access: admin, org_analytics, manager, hrbp.
Write access (accept): admin, manager, hrbp.
"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.dependencies import get_db, require_role
from schemas.insights import RecommendationOut

router = APIRouter()

_READ_ROLES = ("admin", "org_analytics", "manager", "hrbp")
_WRITE_ROLES = ("admin", "manager", "hrbp")


@router.get("/", response_model=list[RecommendationOut])
def list_recommendations(
    scope: str | None = None,
    target_scope: str | None = None,
    priority_min: float = 0.0,
    limit: int = 50,
    current_user: dict = require_role(*_READ_ROLES),
    db: Session = Depends(get_db),
) -> list[RecommendationOut]:
    """List recommendations with optional filters, ordered by priority descending."""
    filters = ["r.priority >= :priority_min"]
    params: dict = {"priority_min": priority_min, "limit": limit}

    if scope is not None:
        filters.append("i.scope = :scope")
        params["scope"] = scope
    if target_scope is not None:
        filters.append("r.target_scope = :target_scope")
        params["target_scope"] = target_scope

    where = " AND ".join(filters)
    sql = text(f"""
        SELECT r.id, r.insight_id, r.action_type, r.priority, r.target_scope,
               r.accepted_flag, r.accepted_at, r.accepted_by
        FROM recommendations r
        JOIN insights i ON i.id = r.insight_id
        WHERE {where}
        ORDER BY r.priority DESC
        LIMIT :limit
    """)

    rows = db.execute(sql, params).mappings().all()
    return [RecommendationOut(**dict(r)) for r in rows]


@router.post("/{recommendation_id}/accept")
def accept_recommendation(
    recommendation_id: uuid.UUID,
    current_user: dict = require_role(*_WRITE_ROLES),
    db: Session = Depends(get_db),
) -> dict:
    """Mark a recommendation as accepted."""
    row = db.execute(
        text("SELECT id FROM recommendations WHERE id = :rid"),
        {"rid": recommendation_id},
    ).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Recommendation not found")

    now = datetime.now(timezone.utc)
    username = current_user.get("username", "unknown")
    db.execute(
        text("""
            UPDATE recommendations
            SET accepted_flag = true,
                accepted_at   = :now,
                accepted_by   = :username,
                updated_at    = :now
            WHERE id = :rid
        """),
        {"rid": recommendation_id, "now": now, "username": username},
    )
    db.commit()

    return {"status": "accepted", "recommendation_id": str(recommendation_id)}
