"""
Integration tests for the Sprint 3 ETL pipeline.

Tier: real Postgres (requires wsip_test DB and migrations applied).
Run with: pytest tests/test_etl.py -v

Tests are skipped automatically if TEST_DATABASE_URL is unreachable.
"""

import os
import sys
from datetime import date

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session as OrmSession

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

TEST_DB_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql://wsip:wsip_dev@localhost:5432/wsip_test",
)

# Mart tables in safe truncation order (facts first, then dims)
_MART_TABLES = [
    "fact_employee_skill_signal",
    "fact_team_weekly_health",
    "fact_employee_project_contribution",
    "fact_employee_daily_activity",
    "dim_skill",
    "dim_project",
    "dim_team",
    "dim_employee",
    "dim_date",
]

# Canonical + raw tables — truncated before seeding to ensure a clean slate
_CANONICAL_TABLES = [
    "resume_skill_inference",
    "training_completion_events",
    "chat_metadata_events",
    "meeting_events",
    "task_events",
    "document_events",
    "research_artifact_events",
    "experiment_run_events",
    "code_review_events",
    "pull_request_events",
    "git_commit_events",
    "data_generation_runs",
    "employee_change_events",
    "employee_snapshots",
    "project_skill_requirements",
    "employee_project_assignments",
    "employee_skills",
    "repos",
    "projects",
    "employees",
    "skills",
    "teams",
    "orgs",
]


def _can_connect() -> bool:
    # Connect to the postgres system DB (not wsip_test, which may not exist yet —
    # the real_db_engine fixture creates it).
    root_url = TEST_DB_URL.rsplit("/", 1)[0] + "/postgres"
    try:
        engine = sa.create_engine(root_url, pool_pre_ping=True)
        with engine.connect() as conn:
            conn.execute(sa.text("SELECT 1"))
        engine.dispose()
        return True
    except Exception:
        return False


needs_db = pytest.mark.skipif(
    not _can_connect(),
    reason="Postgres not reachable at TEST_DATABASE_URL",
)


def _truncate_all(session: OrmSession) -> None:
    for table in _MART_TABLES + _CANONICAL_TABLES:
        session.execute(sa.text(f'TRUNCATE TABLE "{table}" CASCADE'))
    session.commit()


def _truncate_marts(session: OrmSession) -> None:
    for table in _MART_TABLES:
        session.execute(sa.text(f'TRUNCATE TABLE "{table}" CASCADE'))
    session.commit()


def _count_marts(session: OrmSession) -> dict[str, int]:
    return {
        t: session.execute(sa.text(f"SELECT COUNT(*) FROM {t}")).scalar() or 0
        for t in _MART_TABLES
    }


def _seed(db_url: str, seed: int = 42) -> None:
    from synthetic.generate import SyntheticGenerator

    gen = SyntheticGenerator(seed=seed, db_url=db_url)
    gen.generate(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 14),
        n_employees=20,
    )


# ---------------------------------------------------------------------------
# Test 1 — idempotency
# ---------------------------------------------------------------------------

@needs_db
def test_pipeline_idempotency(real_db):
    """Running run_daily_pipeline twice with the same snapshot_date must produce
    identical row counts in all mart tables."""
    from etl.pipeline import run_daily_pipeline

    _truncate_all(real_db)
    _seed(TEST_DB_URL)

    snap = date(2026, 1, 7)

    counts1 = run_daily_pipeline(snap, real_db)
    mart_counts1 = _count_marts(real_db)

    counts2 = run_daily_pipeline(snap, real_db)
    mart_counts2 = _count_marts(real_db)

    assert counts1 == counts2, f"Pipeline return counts differ: {counts1} vs {counts2}"
    assert mart_counts1 == mart_counts2, (
        f"Mart row counts differ after second run:\n"
        f"  first:  {mart_counts1}\n"
        f"  second: {mart_counts2}"
    )


# ---------------------------------------------------------------------------
# Test 2 — rate bounds
# ---------------------------------------------------------------------------

@needs_db
def test_health_rate_bounds(real_db):
    """All rate columns in fact_team_weekly_health must be in [0.0, 1.0]."""
    from etl.pipeline import run_daily_pipeline

    _truncate_all(real_db)
    _seed(TEST_DB_URL, seed=99)

    # Run on end-of-ISO-week (Sunday of week 2, 2026)
    run_daily_pipeline(date(2026, 1, 11), real_db)

    rows = real_db.execute(
        sa.text("""
            SELECT underutilization_rate, overload_rate,
                   silent_disengagement_rate, burnout_risk_rate,
                   cross_team_collaboration_rate
            FROM fact_team_weekly_health
        """)
    ).fetchall()

    assert len(rows) > 0, "No fact_team_weekly_health rows found after pipeline run"
    for row in rows:
        for val in row:
            assert val is not None, "Rate column is NULL"
            assert 0.0 <= float(val) <= 1.0, f"Rate out of [0, 1] bounds: {val}"


# ---------------------------------------------------------------------------
# Test 3 — org overview endpoint returns real data
# ---------------------------------------------------------------------------

@needs_db
def test_org_overview_non_null(real_client, real_db):
    """GET /orgs/{id}/overview must return 200 with non-null contribution units
    after the pipeline has been run."""
    from etl.pipeline import run_daily_pipeline

    _truncate_all(real_db)
    _seed(TEST_DB_URL, seed=7)

    snap = date(2026, 1, 7)
    run_daily_pipeline(snap, real_db)

    org_id = real_db.execute(sa.text("SELECT org_id FROM orgs LIMIT 1")).scalar()
    assert org_id is not None, "No org found — seed may have failed"

    # Use the admin token defined in the test env (same as conftest)
    admin_token = os.environ.get("WSIP_ADMIN_TOKEN", "admin-token")

    resp = real_client.get(
        f"/orgs/{org_id}/overview",
        params={"as_of": str(snap)},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

    data = resp.json()
    assert data["active_employee_count"] is not None
    assert data["total_contribution_units"] is not None
    assert isinstance(data["teams"], list)
