"""
Pre/post impact analysis — Sprint 6.

For each supplied change_event_id, computes the mean of five metric scores
in the 30 days before and after the event date, then writes
EmployeePrePostImpactAnalysis rows with the delta.

run_prepost_analysis(change_event_ids, session) -> int
"""

from __future__ import annotations

import uuid
from datetime import date, timedelta

from sqlalchemy import text
from sqlalchemy.orm import Session

from models.simulations import EmployeePrePostImpactAnalysis

_METRICS = [
    "underutilization_score",
    "overload_score",
    "disengagement_risk_score",
    "glue_person_score",
    "skill_utilization_score",
]


def _mean_metric(
    session: Session,
    employee_id: uuid.UUID,
    from_date: date,
    to_date: date,
    metric: str,
) -> float | None:
    """Return the mean value of a metric column over [from_date, to_date].

    Returns None when no rows exist in the window (no snapshot data).
    """
    row = session.execute(
        text(
            f"SELECT AVG({metric}::numeric) "
            f"FROM employee_feature_snapshots "
            f"WHERE employee_id = :eid "
            f"AND snapshot_date BETWEEN :d0 AND :d1"
        ),
        {"eid": employee_id, "d0": from_date, "d1": to_date},
    ).scalar()
    return float(row) if row is not None else None


def run_prepost_analysis(
    change_event_ids: list[uuid.UUID],
    session: Session,
    window_days: int = 30,
    model_version: str = "wsip-0.1",
) -> int:
    """Compute pre/post metric deltas for each change event.

    Returns total number of EmployeePrePostImpactAnalysis rows written.
    """
    if not change_event_ids:
        return 0

    rows: list[EmployeePrePostImpactAnalysis] = []

    for event_id in change_event_ids:
        # Load the change event to get employee_id + effective_date
        event_row = session.execute(
            text(
                "SELECT employee_id, effective_date "
                "FROM employee_change_events "
                "WHERE change_event_id = :eid"
            ),
            {"eid": event_id},
        ).first()

        if event_row is None:
            continue

        employee_id: uuid.UUID = event_row.employee_id
        effective_date: date = event_row.effective_date

        pre_start = effective_date - timedelta(days=window_days)
        pre_end = effective_date - timedelta(days=1)
        post_start = effective_date
        post_end = effective_date + timedelta(days=window_days - 1)

        for metric in _METRICS:
            pre_mean = _mean_metric(session, employee_id, pre_start, pre_end, metric)
            post_mean = _mean_metric(session, employee_id, post_start, post_end, metric)

            if pre_mean is not None and post_mean is not None:
                delta = round(post_mean - pre_mean, 4)
            elif pre_mean is None and post_mean is not None:
                delta = None
            elif pre_mean is not None and post_mean is None:
                delta = None
            else:
                delta = None

            rows.append(EmployeePrePostImpactAnalysis(
                id=uuid.uuid4(),
                change_event_id=event_id,
                employee_id=employee_id,
                metric_name=metric,
                pre_mean=round(pre_mean, 4) if pre_mean is not None else None,
                post_mean=round(post_mean, 4) if post_mean is not None else None,
                delta=delta,
                window_days=window_days,
                model_version=model_version,
            ))

    session.bulk_save_objects(rows)
    session.flush()
    return len(rows)
