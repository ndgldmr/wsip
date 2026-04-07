import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_db, require_employee_access

router = APIRouter()


@router.get("/{employee_id}/profile")
def get_employee_profile(
    employee_id: uuid.UUID,
    as_of: date,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Individual employee profile (RBAC gated + audit logged). Implemented in S4."""
    require_employee_access(employee_id, current_user, db)
    raise HTTPException(status_code=404, detail="Not found")


@router.get("/{employee_id}/timeline")
def get_employee_timeline(
    employee_id: uuid.UUID,
    from_date: date,
    to_date: date,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> list:
    """Employee daily activity timeline. Implemented in S4."""
    require_employee_access(employee_id, current_user, db)
    raise HTTPException(status_code=404, detail="Not found")


@router.get("/{employee_id}/insights")
def get_employee_insights(
    employee_id: uuid.UUID,
    as_of: date,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> list:
    """Insights for a specific employee. Implemented in S5."""
    require_employee_access(employee_id, current_user, db)
    raise HTTPException(status_code=404, detail="Not found")
