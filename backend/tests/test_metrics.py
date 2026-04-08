"""
Sprint 4 metric tests.

Two tiers:
  - TestMetricGoldenRows  — pure unit tests; no DB needed.
    Each metric has a "high signal" and a "low signal" fixture row.
    Golden values are checked with loose bounds rather than exact floats
    so the tests stay valid if formula weights are tuned.

  - TestMetricPipeline    — integration test (real Postgres).
    Verifies that after run_daily_pipeline() the feature snapshot table
    is populated and all score columns are non-null and in [0, 1].
"""

import os
import sys
from datetime import date
from types import SimpleNamespace

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from etl.metrics import (
    clamp01,
    compute_disengagement_risk,
    compute_glue_score,
    compute_overload,
    compute_skill_utilization,
    compute_underutilization,
)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _snap(**kwargs) -> SimpleNamespace:
    """Build a minimal feature snapshot with sensible defaults."""
    defaults = dict(
        role_family="engineering",
        activity_drop_30d=0.0,
        activity_drop_14d=0.0,
        project_allocation_utilization_score=0.8,
        skill_utilization_score=0.7,
        collaboration_breadth_30d=20,
        knowledge_creation_score=0.5,
        meeting_load_hours_30d=20.0,
        active_project_count=2,
        activity_score_30d=1.2,
        activity_score_90d=1.0,
        cross_team_interaction_rate_30d=0.3,
        collaboration_centrality_30d=0.4,
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


# ---------------------------------------------------------------------------
# clamp01
# ---------------------------------------------------------------------------

class TestClamp01:
    def test_below_zero(self):
        assert clamp01(-5.0) == 0.0

    def test_above_one(self):
        assert clamp01(2.0) == 1.0

    def test_in_range(self):
        assert clamp01(0.5) == 0.5

    def test_exact_boundaries(self):
        assert clamp01(0.0) == 0.0
        assert clamp01(1.0) == 1.0


# ---------------------------------------------------------------------------
# compute_underutilization
# ---------------------------------------------------------------------------

class TestUnderutilization:
    def test_high_underutilization(self):
        """Employee with big activity drop, low allocation usage, and low skill engagement."""
        snap = _snap(
            activity_drop_30d=-0.60,          # fell 60% below baseline
            project_allocation_utilization_score=0.10,
            skill_utilization_score=0.10,
            collaboration_breadth_30d=2,
            knowledge_creation_score=0.05,
        )
        score = compute_underutilization(snap)
        assert score > 0.55, f"Expected high underutilization, got {score:.4f}"
        assert 0.0 <= score <= 1.0

    def test_low_underutilization(self):
        """Fully utilized employee: small drop, high allocation, high skill use."""
        snap = _snap(
            activity_drop_30d=0.10,           # activity actually rose
            project_allocation_utilization_score=0.90,
            skill_utilization_score=0.85,
            collaboration_breadth_30d=30,
            knowledge_creation_score=0.80,
        )
        score = compute_underutilization(snap)
        assert score < 0.20, f"Expected low underutilization, got {score:.4f}"
        assert 0.0 <= score <= 1.0

    def test_score_in_bounds(self):
        for _ in range(5):
            score = compute_underutilization(_snap())
            assert 0.0 <= score <= 1.0


# ---------------------------------------------------------------------------
# compute_overload
# ---------------------------------------------------------------------------

class TestOverload:
    def test_high_overload(self):
        """Engineer with 50h meetings in 30d, 7 projects, activity spike."""
        snap = _snap(
            role_family="engineering",
            meeting_load_hours_30d=50.0,   # well above 30h engineering threshold
            active_project_count=7,
            activity_score_30d=2.5,
            activity_score_90d=1.0,
        )
        score = compute_overload(snap)
        assert score > 0.50, f"Expected high overload, got {score:.4f}"
        assert 0.0 <= score <= 1.0

    def test_low_overload(self):
        """Engineer with modest meeting load, 2 projects, stable activity."""
        snap = _snap(
            role_family="engineering",
            meeting_load_hours_30d=15.0,
            active_project_count=2,
            activity_score_30d=1.0,
            activity_score_90d=1.0,
        )
        score = compute_overload(snap)
        assert score < 0.25, f"Expected low overload, got {score:.4f}"
        assert 0.0 <= score <= 1.0

    def test_management_higher_threshold(self):
        """Manager with 45h meetings should score lower overload than engineer with same hours."""
        eng_snap = _snap(role_family="engineering", meeting_load_hours_30d=45.0, active_project_count=2, activity_score_30d=1.0, activity_score_90d=1.0)
        mgr_snap = _snap(role_family="management",  meeting_load_hours_30d=45.0, active_project_count=2, activity_score_30d=1.0, activity_score_90d=1.0)
        assert compute_overload(mgr_snap) < compute_overload(eng_snap)


# ---------------------------------------------------------------------------
# compute_disengagement_risk
# ---------------------------------------------------------------------------

class TestDisengagementRisk:
    def test_high_risk(self):
        """Employee with steep activity drop, low collab, no cross-team."""
        snap = _snap(
            activity_drop_30d=-0.70,
            activity_drop_14d=-0.65,
            collaboration_breadth_30d=1,
            cross_team_interaction_rate_30d=0.01,
        )
        score = compute_disengagement_risk(snap)
        assert score > 0.55, f"Expected high disengagement risk, got {score:.4f}"
        assert 0.0 <= score <= 1.0

    def test_low_risk(self):
        """Engaged employee: activity stable or rising, broad collab."""
        snap = _snap(
            activity_drop_30d=0.05,
            activity_drop_14d=0.02,
            collaboration_breadth_30d=28,
            cross_team_interaction_rate_30d=0.50,
        )
        score = compute_disengagement_risk(snap)
        assert score < 0.20, f"Expected low disengagement risk, got {score:.4f}"
        assert 0.0 <= score <= 1.0


# ---------------------------------------------------------------------------
# compute_skill_utilization
# ---------------------------------------------------------------------------

class TestSkillUtilization:
    def test_high(self):
        snap = _snap(skill_utilization_score=0.90)
        assert compute_skill_utilization(snap) > 0.85

    def test_low(self):
        snap = _snap(skill_utilization_score=0.10)
        assert compute_skill_utilization(snap) < 0.15

    def test_passthrough(self):
        """skill_utilization is a straight passthrough of the feature column."""
        for v in [0.0, 0.25, 0.5, 0.75, 1.0]:
            assert compute_skill_utilization(_snap(skill_utilization_score=v)) == pytest.approx(v, abs=1e-6)


# ---------------------------------------------------------------------------
# compute_glue_score
# ---------------------------------------------------------------------------

class TestGlueScore:
    def test_high_glue(self):
        snap = _snap(collaboration_centrality_30d=0.90, cross_team_interaction_rate_30d=0.80)
        score = compute_glue_score(snap)
        assert score > 0.80, f"Expected high glue score, got {score:.4f}"
        assert 0.0 <= score <= 1.0

    def test_low_glue(self):
        snap = _snap(collaboration_centrality_30d=0.05, cross_team_interaction_rate_30d=0.03)
        score = compute_glue_score(snap)
        assert score < 0.10, f"Expected low glue score, got {score:.4f}"
        assert 0.0 <= score <= 1.0

    def test_equal_weights(self):
        """Both components weighted 0.5 — verify symmetry."""
        s1 = _snap(collaboration_centrality_30d=0.8, cross_team_interaction_rate_30d=0.2)
        s2 = _snap(collaboration_centrality_30d=0.2, cross_team_interaction_rate_30d=0.8)
        assert compute_glue_score(s1) == pytest.approx(compute_glue_score(s2), abs=1e-6)


# ---------------------------------------------------------------------------
# Integration test (real Postgres)
# ---------------------------------------------------------------------------

TEST_DB_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql://wsip:wsip_dev@localhost:5432/wsip_test",
)


@pytest.mark.integration
class TestMetricPipeline:
    """Requires real Postgres with seeded data and migrations applied."""

    def test_feature_snapshots_populated(self, real_db):
        """After run_daily_pipeline, feature snapshots exist and scores are in [0, 1]."""
        from etl.pipeline import run_daily_pipeline
        from models.features import EmployeeFeatureSnapshot

        snap_date = date(2026, 1, 15)
        counts = run_daily_pipeline(snap_date, real_db)

        assert counts["feature_snapshots"] > 0, "No feature snapshots written"
        assert counts["metrics"] > 0, "No metric scores written"

        rows = real_db.query(EmployeeFeatureSnapshot).filter_by(snapshot_date=snap_date).all()
        assert len(rows) > 0

        for row in rows:
            for col in ("underutilization_score", "overload_score",
                        "disengagement_risk_score", "glue_person_score"):
                val = getattr(row, col)
                assert val is not None, f"{col} is NULL for employee {row.employee_id}"
                assert 0.0 <= float(val) <= 1.0, f"{col}={val} out of [0,1] for {row.employee_id}"
