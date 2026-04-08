"""
Daily ETL pipeline orchestrator.

Call `run_daily_pipeline(snapshot_date, session)` to populate all dimension
and fact tables for a given date.  The pipeline runs in dependency order:
dims first (so facts can join against them), then facts in order (team_weekly
depends on fact_daily).

A single session.commit() is issued at the end.  Each builder calls
session.flush() internally so subsequent builders can see rows written by
earlier ones within the same transaction.  On any exception the transaction
rolls back cleanly.
"""

from datetime import date

from sqlalchemy.orm import Session

from etl.dims import (
    build_dim_date,
    build_dim_employee,
    build_dim_project,
    build_dim_skill,
    build_dim_team,
)
from etl.facts import (
    build_fact_daily_activity,
    build_fact_project_contribution,
    build_fact_skill_signal,
    build_fact_team_weekly_health,
)
from etl.features import build_feature_snapshots
from etl.insight_engine import generate_insights
from etl.metrics import compute_all_metrics


def run_daily_pipeline(snapshot_date: date, session: Session) -> dict[str, int]:
    """Populate all mart tables for snapshot_date.

    Returns a dict mapping each step name to the number of rows written.
    """
    counts: dict[str, int] = {}

    # --- dimensions (order: date → employee → team → project → skill) ---
    counts["dim_date"] = build_dim_date(snapshot_date, snapshot_date, session)
    counts["dim_employee"] = build_dim_employee(snapshot_date, session)
    counts["dim_team"] = build_dim_team(snapshot_date, session)
    counts["dim_project"] = build_dim_project(snapshot_date, session)
    counts["dim_skill"] = build_dim_skill(session)

    # --- facts (daily first, team_weekly last as it depends on daily) ---
    counts["fact_daily_activity"] = build_fact_daily_activity(snapshot_date, session)
    counts["fact_project_contribution"] = build_fact_project_contribution(snapshot_date, session)
    counts["fact_skill_signal"] = build_fact_skill_signal(snapshot_date, session)
    counts["fact_team_weekly_health"] = build_fact_team_weekly_health(snapshot_date, session)

    # --- feature store + metric scores ---
    counts["feature_snapshots"] = build_feature_snapshots(snapshot_date, session)
    counts["metrics"] = compute_all_metrics(snapshot_date, session)

    # --- insight engine (rule-based, depends on metric scores) ---
    counts["insights"] = generate_insights(snapshot_date, session)

    session.commit()
    return counts
