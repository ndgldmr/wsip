"""
Teams router — team health, member listing, and trend endpoints.

Accessible to roles: admin, org_analytics, manager.
week_key format throughout: YYYYWW (ISO year × 100 + ISO week number).
"""

import uuid
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.dependencies import get_db, require_role
from schemas.marts import EmployeeSummaryOut, TeamHealthOut, TeamTrendPointOut

router = APIRouter()

_ROLES = ("admin", "org_analytics", "manager")


@router.get("/{team_id}/health", response_model=TeamHealthOut)
def get_team_health(
    team_id: uuid.UUID,
    week_key: int,
    db: Session = Depends(get_db),
    current_user: dict = require_role(*_ROLES),
) -> TeamHealthOut:
    """Return team weekly health metrics for a specific ISO week_key.

    All rate fields (underutilization, overload, disengagement, burnout) are
    proportions in [0, 1] stored at 4 decimal places.

    Raises 404 if no mart data exists for this team + week combination.
    """
    row = db.execute(
        text("""
            SELECT
                ftwh.team_id,
                dt.team_name,
                ftwh.week_key,
                ftwh.active_employee_count,
                ftwh.underutilization_rate,
                ftwh.overload_rate,
                ftwh.silent_disengagement_rate,
                ftwh.cross_team_collaboration_rate,
                ftwh.burnout_risk_rate
            FROM fact_team_weekly_health ftwh
            JOIN dim_team dt
                ON dt.team_key = ftwh.team_id
               AND dt.is_current = true
            WHERE ftwh.team_id = :tid
              AND ftwh.week_key = :wk
        """),
        {"tid": str(team_id), "wk": week_key},
    ).mappings().first()

    if not row:
        raise HTTPException(status_code=404, detail="Team health data not found for this week")

    return TeamHealthOut(
        team_id=row["team_id"],
        team_name=row["team_name"],
        week_key=row["week_key"],
        active_employee_count=row["active_employee_count"],
        underutilization_rate=Decimal(str(row["underutilization_rate"] or 0)),
        overload_rate=Decimal(str(row["overload_rate"] or 0)),
        silent_disengagement_rate=Decimal(str(row["silent_disengagement_rate"] or 0)),
        cross_team_collaboration_rate=Decimal(str(row["cross_team_collaboration_rate"] or 0)),
        burnout_risk_rate=Decimal(str(row["burnout_risk_rate"] or 0)),
    )


@router.get("/{team_id}/members", response_model=list[EmployeeSummaryOut])
def list_team_members(
    team_id: uuid.UUID,
    as_of: date,  # noqa: ARG001 — reserved for future SCD2 filtering
    db: Session = Depends(get_db),
    current_user: dict = require_role(*_ROLES),
) -> list[EmployeeSummaryOut]:
    """Return current members of a team from the employee dimension.

    Only employees with is_current = True in dim_employee are returned.
    The as_of parameter is reserved for future SCD-2 point-in-time filtering
    and is currently unused.  Results are ordered alphabetically by full_name.
    """
    rows = db.execute(
        text("""
            SELECT employee_id, full_name, role_family, job_level
            FROM dim_employee
            WHERE team_id = :tid
              AND is_current = true
            ORDER BY full_name
        """),
        {"tid": str(team_id)},
    ).mappings().all()

    return [
        EmployeeSummaryOut(
            employee_id=r["employee_id"],
            full_name=r["full_name"],
            role_family=r["role_family"],
            job_level=r["job_level"],
        )
        for r in rows
    ]


@router.get("/{team_id}/trends", response_model=list[TeamTrendPointOut])
def get_team_trends(
    team_id: uuid.UUID,
    from_week: int,
    to_week: int,
    db: Session = Depends(get_db),
    current_user: dict = require_role(*_ROLES),
) -> list[TeamTrendPointOut]:
    """Return weekly trend data for a team between from_week and to_week (inclusive).

    Results are ordered by week_key ascending.  Returns an empty list (not 404)
    if no data exists for the range — callers should check for an empty response
    before rendering charts.
    """
    rows = db.execute(
        text("""
            SELECT
                week_key,
                underutilization_rate,
                overload_rate,
                silent_disengagement_rate,
                burnout_risk_rate
            FROM fact_team_weekly_health
            WHERE team_id = :tid
              AND week_key >= :fw
              AND week_key <= :tw
            ORDER BY week_key
        """),
        {"tid": str(team_id), "fw": from_week, "tw": to_week},
    ).mappings().all()

    return [
        TeamTrendPointOut(
            week_key=r["week_key"],
            underutilization_rate=Decimal(str(r["underutilization_rate"] or 0)),
            overload_rate=Decimal(str(r["overload_rate"] or 0)),
            silent_disengagement_rate=Decimal(str(r["silent_disengagement_rate"] or 0)),
            burnout_risk_rate=Decimal(str(r["burnout_risk_rate"] or 0)),
        )
        for r in rows
    ]
