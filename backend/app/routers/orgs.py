"""
Orgs router — organisation-level KPI and team listing endpoints.

Accessible to roles: admin, org_analytics, manager.
All mart queries are scoped to the ISO week that contains the as_of date.
"""

import uuid
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.dependencies import get_db, require_role
from schemas.marts import OrgOverviewOut, TeamSummaryOut

router = APIRouter()

_ROLES = ("admin", "org_analytics", "manager")


@router.get("/{org_id}/overview", response_model=OrgOverviewOut)
def get_org_overview(
    org_id: uuid.UUID,
    as_of: date,
    db: Session = Depends(get_db),
    current_user: dict = require_role(*_ROLES),
) -> OrgOverviewOut:
    """Return org-level KPI overview for the ISO week containing as_of.

    Aggregates fact_team_weekly_health across all teams in the org, producing
    employee-weighted averages for underutilization, overload, and disengagement
    rates.  Includes a per-team breakdown in the `teams` list.

    Raises 404 if org_id is not found.
    """
    iso_year, iso_week, _ = as_of.isocalendar()
    week_key = iso_year * 100 + iso_week

    org = db.execute(
        text("SELECT org_id, org_name FROM orgs WHERE org_id = :oid"),
        {"oid": str(org_id)},
    ).mappings().first()
    if not org:
        raise HTTPException(status_code=404, detail="Org not found")

    team_rows = db.execute(
        text("""
            SELECT
                ftwh.team_id,
                dt.team_name,
                ftwh.active_employee_count,
                ftwh.underutilization_rate,
                ftwh.overload_rate,
                ftwh.silent_disengagement_rate,
                ftwh.total_contribution_units
            FROM fact_team_weekly_health ftwh
            JOIN dim_team dt
                ON dt.team_key = ftwh.team_id
               AND dt.is_current = true
            WHERE ftwh.org_id = :oid
              AND ftwh.week_key = :wk
        """),
        {"oid": str(org_id), "wk": week_key},
    ).mappings().all()

    teams = [
        TeamSummaryOut(
            team_id=r["team_id"],
            team_name=r["team_name"],
            active_employee_count=r["active_employee_count"],
            underutilization_rate=Decimal(str(r["underutilization_rate"] or 0)),
            overload_rate=Decimal(str(r["overload_rate"] or 0)),
        )
        for r in team_rows
    ]

    total_employees = sum(t.active_employee_count for t in teams)

    def _weighted_avg(field: str) -> Decimal:
        if total_employees == 0:
            return Decimal("0")
        total = sum(
            Decimal(str(r[field] or 0)) * r["active_employee_count"]
            for r in team_rows
        )
        return round(total / total_employees, 4)

    total_contrib = sum(
        Decimal(str(r["total_contribution_units"] or 0)) for r in team_rows
    )

    return OrgOverviewOut(
        org_id=org_id,
        org_name=org["org_name"],
        snapshot_date=as_of,
        active_employee_count=total_employees,
        underutilization_rate=_weighted_avg("underutilization_rate"),
        overload_rate=_weighted_avg("overload_rate"),
        disengagement_risk_rate=_weighted_avg("silent_disengagement_rate"),
        total_contribution_units=total_contrib,
        teams=teams,
    )


@router.get("/{org_id}/teams", response_model=list[TeamSummaryOut])
def list_org_teams(
    org_id: uuid.UUID,
    as_of: date,
    db: Session = Depends(get_db),
    current_user: dict = require_role(*_ROLES),
) -> list[TeamSummaryOut]:
    """List all teams in an org with their weekly health summary for the ISO week containing as_of.

    Returns an empty list (not 404) if no mart data exists for that week.
    Results are ordered alphabetically by team_name.
    """
    iso_year, iso_week, _ = as_of.isocalendar()
    week_key = iso_year * 100 + iso_week

    rows = db.execute(
        text("""
            SELECT
                ftwh.team_id,
                dt.team_name,
                ftwh.active_employee_count,
                ftwh.underutilization_rate,
                ftwh.overload_rate
            FROM fact_team_weekly_health ftwh
            JOIN dim_team dt
                ON dt.team_key = ftwh.team_id
               AND dt.is_current = true
            WHERE ftwh.org_id = :oid
              AND ftwh.week_key = :wk
            ORDER BY dt.team_name
        """),
        {"oid": str(org_id), "wk": week_key},
    ).mappings().all()

    return [
        TeamSummaryOut(
            team_id=r["team_id"],
            team_name=r["team_name"],
            active_employee_count=r["active_employee_count"],
            underutilization_rate=Decimal(str(r["underutilization_rate"] or 0)),
            overload_rate=Decimal(str(r["overload_rate"] or 0)),
        )
        for r in rows
    ]
