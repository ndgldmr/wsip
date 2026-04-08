"""
Sprint 5 + 6 acceptance tests — insight, recommendation, and simulation endpoints.

Covers:
  - /insights and /recommendations require valid auth
  - analyst-token (org_analytics) can read insights but cannot accept recommendations
  - Severity filter returns only matching rows (integration)
  - POST /recommendations/{id}/accept sets accepted_flag + accepted_at (integration)
  - Sprint 6: simulation create → add moves → compute → get outcomes roundtrip
"""

import os
import uuid
from datetime import date

import pytest
from sqlalchemy import text

TEST_DB_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql://wsip:wsip_dev@localhost:5432/wsip_test",
)


# ---------------------------------------------------------------------------
# Unit-tier (stub DB — no Postgres required)
# ---------------------------------------------------------------------------

class TestInsightAuth:
    def test_no_auth_returns_401(self, client):
        resp = client.get("/insights", params={"as_of": "2026-03-01"})
        assert resp.status_code == 401

    def test_bad_token_returns_401(self, client):
        resp = client.get(
            "/insights",
            headers={"Authorization": "Bearer not-a-real-token"},
            params={"as_of": "2026-03-01"},
        )
        assert resp.status_code == 401

    def test_analyst_token_reaches_insights(self, client):
        """org_analytics role is allowed on GET /insights."""
        resp = client.get(
            "/insights",
            headers={"Authorization": "Bearer analyst-token"},
            params={"as_of": "2026-03-01"},
        )
        assert resp.status_code not in (401, 403)

    def test_admin_token_reaches_insights(self, client):
        resp = client.get(
            "/insights",
            headers={"Authorization": "Bearer admin-token"},
            params={"as_of": "2026-03-01"},
        )
        assert resp.status_code not in (401, 403)


class TestRecommendationAuth:
    def test_no_auth_returns_401(self, client):
        resp = client.get("/recommendations")
        assert resp.status_code == 401

    def test_analyst_cannot_accept(self, client):
        """org_analytics does not have write access to recommendations."""
        resp = client.post(
            f"/recommendations/{uuid.uuid4()}/accept",
            headers={"Authorization": "Bearer analyst-token"},
        )
        assert resp.status_code == 403

    def test_manager_token_reaches_recommendations(self, client):
        resp = client.get(
            "/recommendations",
            headers={"Authorization": "Bearer manager-token"},
        )
        assert resp.status_code not in (401, 403)


# ---------------------------------------------------------------------------
# Integration-tier (requires real Postgres + TEST_DATABASE_URL)
# ---------------------------------------------------------------------------

# Table lists mirror test_etl.py — must match actual DB table names exactly.
_SIMULATION_TABLES = [
    "simulation_outcomes",
    "simulation_employee_moves",
    "simulation_runs",
    "employee_prepost_impact_analysis",
    "employee_trajectory_predictions",
    "employee_archetype_assignments",
]
_INSIGHT_TABLES = ["recommendations", "insights"]
_MART_TABLES = [
    "fact_employee_skill_signal",
    "fact_team_weekly_health",
    "fact_employee_project_contribution",
    "fact_employee_daily_activity",
    "employee_feature_snapshots",
    "dim_skill",
    "dim_project",
    "dim_team",
    "dim_employee",
    "dim_date",
]
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


def _truncate_all(db) -> None:
    """Wipe all data for a clean-slate pipeline run."""
    for table in _SIMULATION_TABLES + _INSIGHT_TABLES + _MART_TABLES + _CANONICAL_TABLES:
        db.execute(text(f'TRUNCATE TABLE "{table}" CASCADE'))
    db.commit()


def _seed_and_run(db, snap_date: date) -> None:
    """Generate synthetic data then run the full pipeline.

    SyntheticGenerator manages its own DB connection (commits internally),
    so run_daily_pipeline uses the real_db session which sees the committed rows.
    """
    from etl.pipeline import run_daily_pipeline
    from synthetic.generate import SyntheticGenerator

    gen = SyntheticGenerator(seed=55, db_url=TEST_DB_URL)
    gen.generate(start_date=date(2025, 12, 1), end_date=snap_date, n_employees=20)
    run_daily_pipeline(snap_date, db)


@pytest.mark.integration
class TestInsightApiIntegration:
    """End-to-end tests: generate data → run pipeline → exercise endpoints."""

    SNAP = date(2026, 3, 1)

    def test_insights_populated_after_pipeline(self, real_db):
        """Pipeline produces at least one insight row for the snapshot date."""
        _truncate_all(real_db)
        _seed_and_run(real_db, self.SNAP)

        count = real_db.execute(
            text("SELECT COUNT(*) FROM insights WHERE snapshot_date = :snap"),
            {"snap": self.SNAP},
        ).scalar()
        assert count > 0

    def test_insights_have_non_null_description(self, real_db):
        """Every insight row must have a non-empty description (acceptance criterion)."""
        _truncate_all(real_db)
        _seed_and_run(real_db, self.SNAP)

        bad = real_db.execute(
            text(
                "SELECT COUNT(*) FROM insights "
                "WHERE snapshot_date = :snap "
                "AND (insight_description IS NULL OR insight_description = '')"
            ),
            {"snap": self.SNAP},
        ).scalar()
        assert bad == 0

    def test_severity_filter_returns_only_high(self, real_client, real_db):
        """GET /insights?severity=high&scope=employee returns only high-severity employee rows."""
        _truncate_all(real_db)
        _seed_and_run(real_db, self.SNAP)

        resp = real_client.get(
            "/insights",
            headers={"Authorization": "Bearer admin-token"},
            params={"as_of": str(self.SNAP), "severity": "high", "scope": "employee", "limit": 100},
        )
        assert resp.status_code == 200
        body = resp.json()
        # All returned rows must match requested filters
        for item in body:
            assert item["severity"] == "high", f"Expected high, got {item['severity']}"
            assert item["scope"] == "employee", f"Expected employee scope, got {item['scope']}"

    def test_insights_list_returns_results(self, real_client, real_db):
        """GET /insights?scope=employee returns a non-empty list after pipeline run."""
        _truncate_all(real_db)
        _seed_and_run(real_db, self.SNAP)

        resp = real_client.get(
            "/insights",
            headers={"Authorization": "Bearer admin-token"},
            params={"as_of": str(self.SNAP), "scope": "employee", "limit": 100},
        )
        assert resp.status_code == 200
        assert len(resp.json()) > 0


@pytest.mark.integration
class TestRecommendationApiIntegration:
    """End-to-end tests for the recommendations endpoints."""

    SNAP = date(2026, 3, 1)

    def test_accept_recommendation_roundtrip(self, real_client, real_db):
        """POST /recommendations/{id}/accept sets accepted_flag=True and accepted_at."""
        _truncate_all(real_db)
        _seed_and_run(real_db, self.SNAP)

        # Fetch a real recommendation id from DB
        row = real_db.execute(
            text("SELECT id FROM recommendations LIMIT 1")
        ).first()
        assert row is not None, "No recommendations found — pipeline must have generated some"
        rec_id = row[0]

        resp = real_client.post(
            f"/recommendations/{rec_id}/accept",
            headers={"Authorization": "Bearer admin-token"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "accepted"

        # Verify DB state
        updated = real_db.execute(
            text("SELECT accepted_flag, accepted_at, accepted_by FROM recommendations WHERE id = :rid"),
            {"rid": rec_id},
        ).first()
        assert updated.accepted_flag is True
        assert updated.accepted_at is not None
        assert updated.accepted_by == "admin"

    def test_recommendations_listed(self, real_client, real_db):
        """GET /recommendations returns rows after pipeline run."""
        _truncate_all(real_db)
        _seed_and_run(real_db, self.SNAP)

        resp = real_client.get(
            "/recommendations",
            headers={"Authorization": "Bearer admin-token"},
        )
        assert resp.status_code == 200
        assert len(resp.json()) > 0


# ---------------------------------------------------------------------------
# Sprint 6 — Simulation tests
# ---------------------------------------------------------------------------

class TestSimulationAuth:
    """Unit-tier RBAC tests — no Postgres required."""

    def test_no_auth_returns_401(self, client):
        resp = client.post("/simulations/", json={"name": "x", "snapshot_date": "2026-03-01"})
        assert resp.status_code == 401

    def test_analyst_cannot_create_simulation(self, client):
        """org_analytics role must not be able to create simulations."""
        resp = client.post(
            "/simulations/",
            headers={"Authorization": "Bearer analyst-token"},
            json={"name": "x", "snapshot_date": "2026-03-01"},
        )
        assert resp.status_code == 403

    def test_admin_can_reach_simulations(self, client):
        resp = client.post(
            "/simulations/",
            headers={"Authorization": "Bearer admin-token"},
            json={"name": "x", "snapshot_date": "2026-03-01"},
        )
        # stub DB will raise 500 on commit; what matters is NOT 401/403
        assert resp.status_code not in (401, 403)

    def test_manager_can_reach_simulations(self, client):
        resp = client.post(
            "/simulations/",
            headers={"Authorization": "Bearer manager-token"},
            json={"name": "x", "snapshot_date": "2026-03-01"},
        )
        assert resp.status_code not in (401, 403)


@pytest.mark.integration
class TestSimulationRoundtrip:
    """End-to-end simulation roundtrip: create → move → compute → outcomes."""

    SNAP = date(2026, 3, 1)

    def _setup(self, real_db):
        _truncate_all(real_db)
        _seed_and_run(real_db, self.SNAP)

    def _pick_employee_and_teams(self, real_db):
        row = real_db.execute(
            text(
                "SELECT e.employee_id, e.team_id, "
                "       (SELECT team_id FROM teams WHERE team_id != e.team_id LIMIT 1) AS other_team "
                "FROM employees e "
                "JOIN employee_feature_snapshots fs ON fs.employee_id = e.employee_id "
                "   AND fs.snapshot_date = :snap "
                "LIMIT 1"
            ),
            {"snap": self.SNAP},
        ).first()
        assert row is not None, "No employees with feature snapshots found"
        return str(row.employee_id), str(row.team_id), str(row.other_team)

    def test_simulation_create_returns_draft(self, real_client, real_db):
        self._setup(real_db)
        resp = real_client.post(
            "/simulations/",
            headers={"Authorization": "Bearer admin-token"},
            json={"name": "S6 test", "snapshot_date": str(self.SNAP)},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "draft"
        assert body["name"] == "S6 test"

    def test_simulation_roundtrip_outcomes_non_zero_delta(self, real_client, real_db):
        """Full roundtrip: create → add move → compute → verify non-zero delta."""
        self._setup(real_db)
        emp_id, from_team, to_team = self._pick_employee_and_teams(real_db)

        # 1. Create simulation run
        resp = real_client.post(
            "/simulations/",
            headers={"Authorization": "Bearer admin-token"},
            json={"name": "roundtrip test", "snapshot_date": str(self.SNAP)},
        )
        assert resp.status_code == 200
        sim_id = resp.json()["id"]

        # 2. Add an employee move with a meaningful allocation change
        resp = real_client.post(
            f"/simulations/{sim_id}/moves",
            headers={"Authorization": "Bearer admin-token"},
            json={
                "employee_id": emp_id,
                "from_team_id": from_team,
                "to_team_id": to_team,
                "allocation_pct_change": 30,
            },
        )
        assert resp.status_code == 200

        # 3. Compute
        resp = real_client.post(
            f"/simulations/{sim_id}/compute",
            headers={"Authorization": "Bearer admin-token"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "computed"

        # 4. Get outcomes — must have rows, at least one with non-zero delta
        resp = real_client.get(
            f"/simulations/{sim_id}/outcomes",
            headers={"Authorization": "Bearer admin-token"},
        )
        assert resp.status_code == 200
        outcomes = resp.json()
        assert len(outcomes) > 0, "Expected at least one outcome row"

        deltas = [abs(float(o["delta"])) for o in outcomes]
        assert any(d > 0 for d in deltas), (
            "Expected at least one non-zero delta after a 30% allocation change"
        )

    def test_compute_adds_moves_to_target_team(self, real_client, real_db):
        """team_scope_id on outcomes should be the destination team."""
        self._setup(real_db)
        emp_id, from_team, to_team = self._pick_employee_and_teams(real_db)

        resp = real_client.post(
            "/simulations/",
            headers={"Authorization": "Bearer admin-token"},
            json={"name": "team scope test", "snapshot_date": str(self.SNAP)},
        )
        sim_id = resp.json()["id"]

        real_client.post(
            f"/simulations/{sim_id}/moves",
            headers={"Authorization": "Bearer admin-token"},
            json={
                "employee_id": emp_id,
                "from_team_id": from_team,
                "to_team_id": to_team,
                "allocation_pct_change": 0,
            },
        )
        real_client.post(
            f"/simulations/{sim_id}/compute",
            headers={"Authorization": "Bearer admin-token"},
        )

        resp = real_client.get(
            f"/simulations/{sim_id}/outcomes",
            headers={"Authorization": "Bearer admin-token"},
        )
        outcomes = resp.json()
        assert all(o["team_scope_id"] == to_team for o in outcomes)
