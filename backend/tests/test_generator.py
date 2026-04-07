"""
Tests for the synthetic data generator.

Tier: real Postgres (requires wsip_test DB and migrations applied).
Run with: pytest tests/test_generator.py -v

These tests are skipped automatically if TEST_DATABASE_URL is unreachable.
"""

import os
import sys
from datetime import date

import pytest
import sqlalchemy as sa

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

TEST_DB_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql://wsip:wsip_dev@localhost:5432/wsip_test",
)

# All tables written by the generator — in safe truncation order (children first)
_TRUNCATE_ORDER = [
    # raw events (no FK to each other)
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
    # canonical dependents
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

# Raw event tables whose counts are the primary determinism signal
_RAW_EVENT_TABLES = [
    "git_commit_events",
    "pull_request_events",
    "code_review_events",
    "experiment_run_events",
    "research_artifact_events",
    "document_events",
    "task_events",
    "meeting_events",
    "chat_metadata_events",
    "training_completion_events",
    "resume_skill_inference",
]


def _truncate_all(session: sa.orm.Session) -> None:
    """Truncate all generated tables using CASCADE to handle FK constraints."""
    for table in _TRUNCATE_ORDER:
        session.execute(sa.text(f'TRUNCATE TABLE "{table}" CASCADE'))
    session.commit()


def _count_rows(session: sa.orm.Session, tables: list[str]) -> dict[str, int]:
    return {
        t: session.execute(sa.text(f"SELECT COUNT(*) FROM {t}")).scalar() or 0
        for t in tables
    }


def _can_connect() -> bool:
    try:
        from sqlalchemy import create_engine, text
        engine = create_engine(TEST_DB_URL, pool_pre_ping=True)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        engine.dispose()
        return True
    except Exception:
        return False


needs_db = pytest.mark.skipif(
    not _can_connect(),
    reason="Postgres not reachable at TEST_DATABASE_URL",
)


# ---------------------------------------------------------------------------
# Determinism test
# ---------------------------------------------------------------------------

@needs_db
def test_generator_determinism(real_db):
    """
    Running the generator twice with the same seed and parameters must produce
    identical row counts in every raw event table.
    """
    from synthetic.generate import SyntheticGenerator

    _truncate_all(real_db)

    gen = SyntheticGenerator(seed=42, db_url=TEST_DB_URL)
    gen.generate(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 7),
        n_employees=10,
        n_orgs=1,
        n_teams=3,
        n_projects=5,
        n_repos=4,
        n_skills=15,
    )
    counts_run1 = _count_rows(real_db, _RAW_EVENT_TABLES + ["employees", "data_generation_runs"])

    _truncate_all(real_db)

    # Recreate generator to reset internal RNG state
    gen2 = SyntheticGenerator(seed=42, db_url=TEST_DB_URL)
    gen2.generate(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 7),
        n_employees=10,
        n_orgs=1,
        n_teams=3,
        n_projects=5,
        n_repos=4,
        n_skills=15,
    )
    counts_run2 = _count_rows(real_db, _RAW_EVENT_TABLES + ["employees", "data_generation_runs"])

    assert counts_run1 == counts_run2, (
        f"Counts diverged between identical-seed runs:\n"
        f"  Run 1: {counts_run1}\n"
        f"  Run 2: {counts_run2}"
    )

    # Sanity: we should actually have some data
    assert counts_run1["employees"] == 10
    assert counts_run1["git_commit_events"] > 0


# ---------------------------------------------------------------------------
# Persona distribution test
# ---------------------------------------------------------------------------

@needs_db
def test_persona_signal_distribution(real_db):
    """
    prolific_engineer employees must have significantly more git commits than
    meeting_heavy_manager employees (>= 3× on average).
    """
    from synthetic.generate import SyntheticGenerator

    _truncate_all(real_db)

    # Use a larger population so we're likely to have both persona types
    gen = SyntheticGenerator(seed=99, db_url=TEST_DB_URL)
    gen.generate(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 14),
        n_employees=50,
        n_orgs=1,
        n_teams=5,
        n_projects=8,
        n_repos=6,
        n_skills=20,
    )

    # Get per-employee commit counts joined with role_family
    result = real_db.execute(sa.text("""
        SELECT e.role_family, COUNT(g.commit_event_id) AS commit_count
        FROM employees e
        LEFT JOIN git_commit_events g ON g.employee_id = e.employee_id
        WHERE e.role_family IN ('engineering', 'management')
        GROUP BY e.employee_id, e.role_family
    """)).fetchall()

    by_family: dict[str, list[int]] = {}
    for row in result:
        family, count = row[0], row[1]
        by_family.setdefault(family, []).append(count)

    if "engineering" in by_family and "management" in by_family:
        eng_avg = sum(by_family["engineering"]) / len(by_family["engineering"])
        mgmt_avg = sum(by_family["management"]) / len(by_family["management"])
        assert eng_avg >= mgmt_avg * 3, (
            f"Engineering avg commits ({eng_avg:.1f}) should be >= 3× management avg ({mgmt_avg:.1f})"
        )


# ---------------------------------------------------------------------------
# data_generation_runs record test
# ---------------------------------------------------------------------------

@needs_db
def test_generation_run_record(real_db):
    """
    After generation, data_generation_runs must have a row with correct metadata.
    """
    from synthetic.generate import SyntheticGenerator

    _truncate_all(real_db)

    gen = SyntheticGenerator(seed=7, db_url=TEST_DB_URL)
    run_id = gen.generate(
        start_date=date(2026, 2, 1),
        end_date=date(2026, 2, 7),
        n_employees=5,
        n_orgs=1,
        n_teams=2,
        n_projects=3,
        n_repos=2,
        n_skills=10,
    )

    row = real_db.execute(
        sa.text("SELECT seed, employee_count FROM data_generation_runs WHERE run_id = :rid"),
        {"rid": str(run_id)},
    ).fetchone()

    assert row is not None, "data_generation_runs row not found"
    assert row[0] == 7, f"Expected seed=7, got {row[0]}"
    assert row[1] == 5, f"Expected employee_count=5, got {row[1]}"
