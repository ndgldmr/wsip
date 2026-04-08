"""
ETL dimension builders — all idempotent via upsert (INSERT … ON CONFLICT DO UPDATE).

Each function returns the number of rows processed.
"""

from datetime import date, timedelta

from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from models.marts import DimDate, DimEmployee, DimProject, DimSkill, DimTeam


def build_dim_date(start_date: date, end_date: date, session: Session) -> int:
    """Populate dim_date for every calendar day in [start_date, end_date] inclusive.

    Uses ISO week/year so that week_key is correct across year boundaries
    (e.g. 2026-01-01 belongs to ISO week 1 of 2026 → week_key 202601).
    """
    rows: list[dict] = []
    current = start_date
    while current <= end_date:
        iso_year, iso_week, _ = current.isocalendar()
        rows.append(
            {
                "date_key": int(current.strftime("%Y%m%d")),
                "date": current,
                "day_of_week": current.weekday(),  # 0=Mon … 6=Sun
                "day_name": current.strftime("%A"),
                "week_key": iso_year * 100 + iso_week,
                "month_key": current.year * 100 + current.month,
                "quarter_key": current.year * 10 + ((current.month - 1) // 3 + 1),
                "is_weekend": current.weekday() >= 5,
            }
        )
        current += timedelta(days=1)

    if not rows:
        return 0

    stmt = pg_insert(DimDate).values(rows)
    stmt = stmt.on_conflict_do_update(
        index_elements=["date_key"],
        set_={
            "date": stmt.excluded.date,
            "day_of_week": stmt.excluded.day_of_week,
            "day_name": stmt.excluded.day_name,
            "week_key": stmt.excluded.week_key,
            "month_key": stmt.excluded.month_key,
            "quarter_key": stmt.excluded.quarter_key,
            "is_weekend": stmt.excluded.is_weekend,
        },
    )
    session.execute(stmt)
    session.flush()
    return len(rows)


def build_dim_employee(snapshot_date: date, session: Session) -> int:
    """Upsert current-state employee dimension (SCD Type 1).

    employee_key equals employee_id — this is a deliberate simplification for
    MVP.  effective_from = hire_date, effective_to = NULL, is_current = True.
    Only employees who are active or whose exit_date is on/after snapshot_date
    are included.
    """
    rows = session.execute(
        text("""
            SELECT
                employee_id          AS employee_key,
                employee_id,
                full_name,
                role_family,
                job_level,
                team_id,
                org_id,
                hire_date            AS effective_from
            FROM employees
            WHERE employment_status = 'active'
               OR exit_date IS NULL
               OR exit_date >= :snap
        """),
        {"snap": snapshot_date},
    ).mappings().all()

    if not rows:
        return 0

    data = [
        {**dict(r), "effective_to": None, "is_current": True}
        for r in rows
    ]

    stmt = pg_insert(DimEmployee).values(data)
    stmt = stmt.on_conflict_do_update(
        index_elements=["employee_key"],
        set_={
            "full_name": stmt.excluded.full_name,
            "role_family": stmt.excluded.role_family,
            "job_level": stmt.excluded.job_level,
            "team_id": stmt.excluded.team_id,
            "org_id": stmt.excluded.org_id,
            "is_current": stmt.excluded.is_current,
        },
    )
    session.execute(stmt)
    session.flush()
    return len(data)


def build_dim_team(snapshot_date: date, session: Session) -> int:  # noqa: ARG001
    """Upsert all teams into dim_team (SCD Type 1, team_key = team_id)."""
    rows = session.execute(
        text("""
            SELECT
                team_id  AS team_key,
                team_id,
                team_name,
                org_id,
                created_at::date AS effective_from
            FROM teams
        """)
    ).mappings().all()

    if not rows:
        return 0

    data = [{**dict(r), "effective_to": None, "is_current": True} for r in rows]

    stmt = pg_insert(DimTeam).values(data)
    stmt = stmt.on_conflict_do_update(
        index_elements=["team_key"],
        set_={
            "team_name": stmt.excluded.team_name,
            "org_id": stmt.excluded.org_id,
            "is_current": stmt.excluded.is_current,
        },
    )
    session.execute(stmt)
    session.flush()
    return len(data)


def build_dim_project(snapshot_date: date, session: Session) -> int:  # noqa: ARG001
    """Upsert all projects into dim_project (project_key = project_id)."""
    rows = session.execute(
        text("""
            SELECT
                project_id  AS project_key,
                project_id,
                project_name,
                project_type,
                priority_tier,
                status
            FROM projects
        """)
    ).mappings().all()

    if not rows:
        return 0

    data = [dict(r) for r in rows]

    stmt = pg_insert(DimProject).values(data)
    stmt = stmt.on_conflict_do_update(
        index_elements=["project_key"],
        set_={
            "project_name": stmt.excluded.project_name,
            "project_type": stmt.excluded.project_type,
            "priority_tier": stmt.excluded.priority_tier,
            "status": stmt.excluded.status,
        },
    )
    session.execute(stmt)
    session.flush()
    return len(data)


def build_dim_skill(session: Session) -> int:
    """Upsert all skills into dim_skill (skill_key = skill_id)."""
    rows = session.execute(
        text("""
            SELECT
                skill_id  AS skill_key,
                skill_id,
                skill_name,
                skill_category
            FROM skills
        """)
    ).mappings().all()

    if not rows:
        return 0

    data = [dict(r) for r in rows]

    stmt = pg_insert(DimSkill).values(data)
    stmt = stmt.on_conflict_do_update(
        index_elements=["skill_key"],
        set_={
            "skill_name": stmt.excluded.skill_name,
            "skill_category": stmt.excluded.skill_category,
        },
    )
    session.execute(stmt)
    session.flush()
    return len(data)
