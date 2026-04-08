"""
Rule-based insight engine — Sprint 5.

Evaluates each EmployeeFeatureSnapshot against INSIGHT_RULES and writes
Insight + Recommendation rows.  Idempotent: existing rows for the same
(scope_id, insight_type, snapshot_date) are replaced on each run.

Call generate_insights(snapshot_date, session) from the pipeline.
The session is committed by the caller (pipeline.py).
"""

import uuid
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Callable

from sqlalchemy import text
from sqlalchemy.orm import Session

from models.features import EmployeeFeatureSnapshot
from models.insights import Insight, Recommendation

# ---------------------------------------------------------------------------
# Severity weight used to compute recommendation priority
# ---------------------------------------------------------------------------
_SEVERITY_WEIGHT: dict[str, float] = {"high": 1.0, "medium": 0.7, "low": 0.4}


# ---------------------------------------------------------------------------
# InsightRule definition
# ---------------------------------------------------------------------------

@dataclass
class InsightRule:
    insight_type: str
    condition: Callable[[EmployeeFeatureSnapshot], bool]
    severity_fn: Callable[[EmployeeFeatureSnapshot], str]
    title_fn: Callable[[EmployeeFeatureSnapshot], str]
    description_fn: Callable[[EmployeeFeatureSnapshot], str]
    confidence_fn: Callable[[EmployeeFeatureSnapshot], float]


# ---------------------------------------------------------------------------
# The five core rules
# ---------------------------------------------------------------------------

INSIGHT_RULES: list[InsightRule] = [
    InsightRule(
        insight_type="underutilization",
        condition=lambda s: s.underutilization_score is not None and float(s.underutilization_score) > 0.65,
        severity_fn=lambda s: "high" if float(s.underutilization_score) > 0.80 else "medium",
        title_fn=lambda s: "Underutilization vs allocation",
        description_fn=lambda s: (
            f"30d activity is {float(s.activity_drop_30d or 0):+.0%} vs baseline; "
            f"allocation utilization is {float(s.project_allocation_utilization_score):.0%}."
        ),
        confidence_fn=lambda s: min(1.0, float(s.underutilization_score) + 0.15),
    ),
    InsightRule(
        insight_type="overload",
        condition=lambda s: s.overload_score is not None and float(s.overload_score) > 0.65,
        severity_fn=lambda s: "high" if float(s.overload_score) > 0.80 else "medium",
        title_fn=lambda s: "Employee showing overload signals",
        description_fn=lambda s: (
            f"Meeting load is {float(s.meeting_load_hours_30d):.0f}h over 30 days across "
            f"{s.active_project_count} active projects."
        ),
        confidence_fn=lambda s: min(1.0, float(s.overload_score) + 0.15),
    ),
    InsightRule(
        insight_type="disengagement_risk",
        condition=lambda s: s.disengagement_risk_score is not None and float(s.disengagement_risk_score) > 0.60,
        severity_fn=lambda s: "high" if float(s.disengagement_risk_score) > 0.75 else "medium",
        title_fn=lambda s: "Disengagement risk detected",
        description_fn=lambda s: (
            f"30d activity drop: {float(s.activity_drop_30d or 0):+.0%}; "
            f"14d drop: {float(s.activity_drop_14d or 0):+.0%}; "
            f"collaboration breadth: {s.collaboration_breadth_30d} contacts."
        ),
        confidence_fn=lambda s: min(1.0, float(s.disengagement_risk_score) + 0.15),
    ),
    InsightRule(
        insight_type="skill_underutilization",
        # Low skill_utilization_score = skills not being exercised in current work
        condition=lambda s: float(s.skill_utilization_score) < 0.40,
        severity_fn=lambda s: "high" if float(s.skill_utilization_score) < 0.20 else "medium",
        title_fn=lambda s: "Skill underutilization detected",
        description_fn=lambda s: (
            f"Skill utilization score is {float(s.skill_utilization_score):.0%} "
            f"(depth: {float(s.skill_depth_score):.0%}). "
            "Current assignments may not be drawing on employee's full skill set."
        ),
        confidence_fn=lambda s: min(1.0, (0.40 - float(s.skill_utilization_score)) + 0.15),
    ),
    InsightRule(
        insight_type="glue_person_identified",
        condition=lambda s: s.glue_person_score is not None and float(s.glue_person_score) > 0.70,
        severity_fn=lambda s: "high" if float(s.glue_person_score) > 0.85 else "medium",
        title_fn=lambda s: "Glue person identified",
        description_fn=lambda s: (
            f"Collaboration centrality: {float(s.collaboration_centrality_30d):.0%}; "
            f"cross-team interaction rate: {float(s.cross_team_interaction_rate_30d):.0%}. "
            "High coordination load with limited redundancy — succession risk."
        ),
        confidence_fn=lambda s: min(1.0, float(s.glue_person_score) + 0.15),
    ),
]


# ---------------------------------------------------------------------------
# Recommendation action map
# Each entry: (action_type, target_scope)
# ---------------------------------------------------------------------------

_RECOMMENDATION_MAP: dict[str, list[tuple[str, str]]] = {
    "underutilization":       [("manager_checkin", "manager"), ("reassignment_candidate", "hrbp")],
    "overload":               [("workload_rebalance", "manager"), ("meeting_audit", "hrbp")],
    "disengagement_risk":     [("manager_checkin", "manager"), ("career_path_review", "hrbp")],
    "skill_underutilization": [("skill_deployment", "manager"), ("project_rotation", "hrbp")],
    "glue_person_identified": [("succession_planning", "hrbp"), ("knowledge_transfer", "admin")],
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_insights(snapshot_date: date, session: Session) -> int:
    """Evaluate all rules against feature snapshots for snapshot_date.

    Creates or replaces Insight rows (idempotent) and links Recommendation rows.
    Returns the number of insights written.
    """
    snapshots: list[EmployeeFeatureSnapshot] = (
        session.query(EmployeeFeatureSnapshot)
        .filter(EmployeeFeatureSnapshot.snapshot_date == snapshot_date)
        .all()
    )

    total_written = 0

    for snap in snapshots:
        # Skip snapshots where metrics haven't been computed yet
        if snap.underutilization_score is None and snap.overload_score is None:
            continue

        for rule in INSIGHT_RULES:
            if not rule.condition(snap):
                continue

            severity = rule.severity_fn(snap)
            confidence = Decimal(str(round(rule.confidence_fn(snap), 4)))

            # Idempotent: remove existing insight + its recommendations for this (scope_id, type, date)
            session.execute(
                text(
                    "DELETE FROM recommendations "
                    "WHERE insight_id IN ("
                    "  SELECT id FROM insights "
                    "  WHERE scope_id = :sid AND insight_type = :itype AND snapshot_date = :snap_date"
                    ")"
                ),
                {"sid": snap.employee_id, "itype": rule.insight_type, "snap_date": snapshot_date},
            )
            session.execute(
                text(
                    "DELETE FROM insights "
                    "WHERE scope_id = :sid AND insight_type = :itype AND snapshot_date = :snap_date"
                ),
                {"sid": snap.employee_id, "itype": rule.insight_type, "snap_date": snapshot_date},
            )

            insight = Insight(
                id=uuid.uuid4(),
                scope="employee",
                scope_id=snap.employee_id,
                insight_type=rule.insight_type,
                snapshot_date=snapshot_date,
                severity=severity,
                title=rule.title_fn(snap),
                insight_description=rule.description_fn(snap),
                confidence=confidence,
                is_active=True,
            )
            session.add(insight)
            session.flush()  # get insight.id before creating recommendations

            for action_type, target_scope in _RECOMMENDATION_MAP.get(rule.insight_type, []):
                priority = Decimal(str(round(float(confidence) * _SEVERITY_WEIGHT[severity], 4)))
                session.add(Recommendation(
                    id=uuid.uuid4(),
                    insight_id=insight.id,
                    action_type=action_type,
                    priority=priority,
                    target_scope=target_scope,
                    accepted_flag=False,
                ))

            total_written += 1

    session.flush()
    return total_written
