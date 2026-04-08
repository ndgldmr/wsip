"""
Core metric computations for WSIP employee feature snapshots.

Each `compute_*` function accepts any object with the expected attributes
(duck-typed so they work with ORM rows, SimpleNamespace, or dataclasses)
and returns a float in [0.0, 1.0].

`compute_all_metrics` loads all feature snapshots for a given snapshot_date,
runs all five functions, and writes the scores back via a bulk UPDATE.

Role-adjusted overload thresholds (meeting hours over 30 days):
  engineering / research → 30 h
  management             → 50 h
  default                → 35 h
"""

from datetime import date

from sqlalchemy import text
from sqlalchemy.orm import Session

# ---------------------------------------------------------------------------
# Overload thresholds (meeting_load_hours_30d)
# ---------------------------------------------------------------------------

_OVERLOAD_MEETING_THRESHOLD: dict[str, float] = {
    "engineering": 30.0,
    "research":    30.0,
    "management":  50.0,
}
_OVERLOAD_MEETING_DEFAULT = 35.0


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def clamp01(v: float) -> float:
    """Clamp v to [0.0, 1.0]."""
    return max(0.0, min(1.0, v))


def _f(val) -> float:
    """Safely cast a possibly-Decimal / None attribute to float."""
    return float(val) if val is not None else 0.0


# ---------------------------------------------------------------------------
# core metric functions
# ---------------------------------------------------------------------------

def compute_underutilization(snap) -> float:
    """Weighted signal of under-engagement relative to allocation and baseline.

    Weights (must sum to 1.0):
      0.30  activity_drop_30d         — activity fell below personal baseline
      0.25  project_allocation gap    — allocated capacity not reflected in output
      0.20  skill_utilization gap     — skills not being exercised
      0.15  collaboration breadth gap — low collaboration reach (norm: 30 collab touches/mo)
      0.10  knowledge creation gap    — low docs/artefact output
    """
    act_drop  = clamp01(_f(snap.activity_drop_30d) * -1)   # negative drop → positive score
    alloc_gap = clamp01(1 - _f(snap.project_allocation_utilization_score))
    skill_gap = clamp01(1 - _f(snap.skill_utilization_score))
    collab_gap = clamp01(1 - _f(snap.collaboration_breadth_30d) / 30.0)
    know_gap  = clamp01(1 - _f(snap.knowledge_creation_score))

    return (
        0.30 * act_drop
        + 0.25 * alloc_gap
        + 0.20 * skill_gap
        + 0.15 * collab_gap
        + 0.10 * know_gap
    )


def compute_overload(snap) -> float:
    """Signal of over-engagement: excessive meetings, many projects, volatile activity.

    Weights:
      0.40  meeting overload (hours vs role-adjusted threshold)
      0.30  project sprawl (active_project_count > 3)
      0.30  activity volatility (high recent activity vs 90d baseline)
    """
    role_family = (getattr(snap, "role_family", None) or "").lower()
    threshold   = _OVERLOAD_MEETING_THRESHOLD.get(role_family, _OVERLOAD_MEETING_DEFAULT)
    meeting_overload = clamp01(_f(snap.meeting_load_hours_30d) / threshold - 0.5) * 2  # >50% of threshold → signal

    proj_sprawl = clamp01((_f(snap.active_project_count) - 3) / 5.0)   # 3=baseline, 8+=max

    # activity spike vs 90d average
    act_30 = _f(snap.activity_score_30d)
    act_90 = _f(snap.activity_score_90d)
    volatility = clamp01((act_30 - act_90) / max(act_90, 0.01))

    return (
        0.40 * clamp01(meeting_overload)
        + 0.30 * proj_sprawl
        + 0.30 * volatility
    )


def compute_disengagement_risk(snap) -> float:
    """Signal of silent disengagement: activity and collaboration declining.

    Weights:
      0.35  activity_drop_30d (negative = drop)
      0.25  activity_drop_14d (short-term leading indicator)
      0.25  collaboration breadth gap
      0.15  low cross-team interaction
    """
    drop_30  = clamp01(_f(snap.activity_drop_30d) * -1)       # negative → positive risk
    drop_14  = clamp01(_f(snap.activity_drop_14d) * -1)
    collab_gap = clamp01(1 - _f(snap.collaboration_breadth_30d) / 30.0)
    low_cross = clamp01(1 - _f(snap.cross_team_interaction_rate_30d))

    return (
        0.35 * drop_30
        + 0.25 * drop_14
        + 0.25 * collab_gap
        + 0.15 * low_cross
    )


def compute_skill_utilization(snap) -> float:
    """Fraction of the employee's known skills exercised in the trailing 90 days."""
    return clamp01(_f(snap.skill_utilization_score))


def compute_glue_score(snap) -> float:
    """Measure of cross-cutting coordination and knowledge-transfer activity.

    Weights:
      0.50  collaboration_centrality_30d — review + meeting-organising reach
      0.50  cross_team_interaction_rate_30d — fraction of meetings that are cross-team
    """
    return (
        0.50 * clamp01(_f(snap.collaboration_centrality_30d))
        + 0.50 * clamp01(_f(snap.cross_team_interaction_rate_30d))
    )


# ---------------------------------------------------------------------------
# pipeline writer
# ---------------------------------------------------------------------------

def compute_all_metrics(snapshot_date: date, session: Session) -> int:
    """Compute all five metric scores for every feature snapshot on snapshot_date.

    Loads snapshots into Python (ORM rows), runs all five functions, then bulk
    UPDATEs the score columns.  Returns the number of rows updated.
    """
    from models.features import EmployeeFeatureSnapshot
    from models.canonical import Employee

    snaps = (
        session.query(EmployeeFeatureSnapshot, Employee.role_family)
        .join(Employee, Employee.employee_id == EmployeeFeatureSnapshot.employee_id)
        .filter(EmployeeFeatureSnapshot.snapshot_date == snapshot_date)
        .all()
    )

    count = 0
    for snap, role_family in snaps:
        # attach role_family so overload threshold can be read
        snap.role_family = role_family

        snap.underutilization_score   = round(compute_underutilization(snap), 4)
        snap.overload_score           = round(compute_overload(snap), 4)
        snap.disengagement_risk_score = round(compute_disengagement_risk(snap), 4)
        snap.glue_person_score        = round(compute_glue_score(snap), 4)
        # skill_utilization_score is already populated by the features step; no write-back needed
        count += 1

    session.flush()
    return count
