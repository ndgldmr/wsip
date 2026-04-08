"""
Employees router — individual employee profile, timeline, and insight endpoints.

All endpoints require RBAC via require_employee_access(), which:
  - checks the manager chain and viewer_permissions table
  - writes an AccessAuditLog row (outcome="success" or "denied") before returning

RBAC hierarchy:
  admin / hrbp       → any employee
  manager            → direct reports only (manager_employee_id match)
  org_analytics      → aggregate views only; individual drill-down → 403
  viewer_permissions → explicit per-employee grants
"""

import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_db, require_employee_access
from schemas.features import DailyActivityOut, EmployeeProfileOut

router = APIRouter()


@router.get("/{employee_id}/profile", response_model=EmployeeProfileOut)
def get_employee_profile(
    employee_id: uuid.UUID,
    as_of: date,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> EmployeeProfileOut:
    """Return an employee's feature profile for the given snapshot date.

    Raises 403 if the caller lacks access; raises 404 if no feature snapshot
    exists for (employee_id, as_of).  An audit log row is written in both cases.
    """
    require_employee_access(employee_id, current_user, db)

    from models.canonical import Team
    from models.features import EmployeeFeatureSnapshot
    from models.canonical import Employee

    row = (
        db.query(EmployeeFeatureSnapshot, Employee, Team)
        .join(Employee, Employee.employee_id == EmployeeFeatureSnapshot.employee_id)
        .join(Team, Team.team_id == Employee.team_id)
        .filter(
            EmployeeFeatureSnapshot.employee_id == employee_id,
            EmployeeFeatureSnapshot.snapshot_date == as_of,
        )
        .first()
    )

    if row is None:
        raise HTTPException(status_code=404, detail="No feature snapshot found for this employee and date")

    snap, emp, team = row
    return EmployeeProfileOut(
        employee_id=emp.employee_id,
        full_name=emp.full_name,
        role_title=emp.role_title,
        role_family=emp.role_family,
        job_level=emp.job_level,
        team_name=team.team_name,
        snapshot_date=snap.snapshot_date,
        underutilization_score=float(snap.underutilization_score or 0),
        overload_score=float(snap.overload_score or 0),
        disengagement_risk_score=float(snap.disengagement_risk_score or 0),
        skill_utilization_score=float(snap.skill_utilization_score or 0),
        glue_person_score=float(snap.glue_person_score or 0),
        commits_30d=snap.commits_30d or 0,
        prs_merged_30d=snap.prs_merged_30d or 0,
        meeting_load_hours_30d=float(snap.meeting_load_hours_30d or 0),
        collaboration_breadth_30d=snap.collaboration_breadth_30d or 0,
        experiment_runs_30d=snap.experiment_runs_30d or 0,
        commits_30d_vs_self_baseline=float(snap.commits_30d_vs_self_baseline) if snap.commits_30d_vs_self_baseline is not None else None,
        commits_30d_vs_role_baseline=float(snap.commits_30d_vs_role_baseline) if snap.commits_30d_vs_role_baseline is not None else None,
        archetype_label=snap.archetype_label,
    )


@router.get("/{employee_id}/timeline", response_model=list[DailyActivityOut])
def get_employee_timeline(
    employee_id: uuid.UUID,
    from_date: date,
    to_date: date,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> list[DailyActivityOut]:
    """Return daily activity fact rows for [from_date, to_date] (inclusive).

    Rows are ordered by date_key ascending.
    """
    require_employee_access(employee_id, current_user, db)

    from models.marts import DimEmployee, FactEmployeeDailyActivity

    def _dk(d: date) -> int:
        return int(d.strftime("%Y%m%d"))

    dim_row = (
        db.query(DimEmployee)
        .filter(DimEmployee.employee_id == employee_id, DimEmployee.is_current == True)  # noqa: E712
        .first()
    )
    if dim_row is None:
        return []

    rows = (
        db.query(FactEmployeeDailyActivity)
        .filter(
            FactEmployeeDailyActivity.employee_key == dim_row.employee_key,
            FactEmployeeDailyActivity.date_key >= _dk(from_date),
            FactEmployeeDailyActivity.date_key <= _dk(to_date),
        )
        .order_by(FactEmployeeDailyActivity.date_key)
        .all()
    )
    return rows


@router.get("/{employee_id}/insights")
def get_employee_insights(
    employee_id: uuid.UUID,
    as_of: date,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> list:
    """Insights for a specific employee. Implemented in Sprint 5."""
    require_employee_access(employee_id, current_user, db)
    return []
