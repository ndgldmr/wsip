"""
Trajectory predictions — Sprint 6.

Uses historical employee_feature_snapshots to train a LogisticRegression
(disengagement_risk at t+horizon) and Ridge (impact score at t+horizon).

When insufficient training pairs exist (< 20), falls back to using each
employee's current scores as the prediction with confidence=0.5.

run_trajectory_predictions() writes employee_trajectory_predictions rows
for the given snapshot_date (DELETE+INSERT).
"""

from __future__ import annotations

import uuid
from datetime import date, timedelta

import numpy as np
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.preprocessing import StandardScaler
from sqlalchemy import text
from sqlalchemy.orm import Session

from models.simulations import EmployeeTrajectoryPrediction

_MIN_TRAINING_ROWS = 20
_DISENGAGEMENT_THRESHOLD = 0.5   # score above this → high-risk class

_FEATURE_COLS = [
    "activity_score_30d",
    "commits_30d",
    "meeting_load_hours_30d",
    "collaboration_breadth_30d",
    "cross_team_interaction_rate_30d",
    "activity_score_90d",
    "glue_person_score",
    "underutilization_score",
    "overload_score",
]


def _fv(snap) -> list[float]:
    return [float(getattr(snap, c) or 0) for c in _FEATURE_COLS]


def run_trajectory_predictions(
    snapshot_date: date,
    session: Session,
    horizon_days: int = 60,
    model_version: str = "wsip-0.1",
) -> int:
    """Predict 60-day trajectory for every employee on snapshot_date.

    Returns number of rows written.
    """
    from models.features import EmployeeFeatureSnapshot

    # Load all snapshots across all dates (needed to build training pairs)
    all_snaps = session.query(EmployeeFeatureSnapshot).all()
    if not all_snaps:
        return 0

    # Index by (employee_id, snapshot_date)
    snap_index: dict[tuple[uuid.UUID, date], EmployeeFeatureSnapshot] = {
        (s.employee_id, s.snapshot_date): s for s in all_snaps
    }

    # Current-date snapshots (the ones we need to predict for)
    current_snaps = [s for s in all_snaps if s.snapshot_date == snapshot_date]
    if not current_snaps:
        return 0

    # Build training pairs: (features at t) → (scores at t + horizon)
    horizon = timedelta(days=horizon_days)
    X_train, y_diseng, y_impact = [], [], []

    for snap in all_snaps:
        future_key = (snap.employee_id, snap.snapshot_date + horizon)
        future = snap_index.get(future_key)
        if future is None:
            continue
        if future.disengagement_risk_score is None or future.activity_score_30d is None:
            continue
        X_train.append(_fv(snap))
        y_diseng.append(1 if float(future.disengagement_risk_score) >= _DISENGAGEMENT_THRESHOLD else 0)
        y_impact.append(float(future.activity_score_30d))

    # Delete existing predictions for this snapshot_date
    session.execute(
        text(
            "DELETE FROM employee_trajectory_predictions "
            "WHERE snapshot_date = :snap AND horizon_days = :h"
        ),
        {"snap": snapshot_date, "h": horizon_days},
    )
    session.flush()

    rows: list[EmployeeTrajectoryPrediction] = []

    if len(X_train) < _MIN_TRAINING_ROWS:
        # Fallback: use current scores as proxy prediction
        for snap in current_snaps:
            dis = float(snap.disengagement_risk_score or 0)
            impact = float(snap.activity_score_30d or 0)
            rows.append(EmployeeTrajectoryPrediction(
                id=uuid.uuid4(),
                employee_id=snap.employee_id,
                snapshot_date=snapshot_date,
                horizon_days=horizon_days,
                predicted_disengagement_risk=round(dis, 4),
                predicted_impact_score=round(impact, 4),
                confidence=0.5,
                model_version=model_version,
            ))
    else:
        X_arr = np.array(X_train, dtype=float)
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X_arr)

        # Disengagement risk: LogisticRegression → P(high risk)
        # Use class_weight='balanced' since high-risk may be minority
        lr = LogisticRegression(class_weight="balanced", max_iter=500, random_state=42)
        lr.fit(X_scaled, y_diseng)

        # Impact score: Ridge regression
        ridge = Ridge(alpha=1.0, random_state=42)
        ridge.fit(X_scaled, y_impact)

        X_current = scaler.transform(np.array([_fv(s) for s in current_snaps], dtype=float))
        dis_probs = lr.predict_proba(X_current)[:, 1]      # P(class=1)
        impact_preds = np.clip(ridge.predict(X_current), 0.0, 1.0)

        # Confidence: distance from decision boundary (scaled sigmoid of abs margin)
        margins = np.abs(dis_probs - 0.5) * 2              # [0, 1] — 1 = certain
        confidences = np.clip(margins, 0.0, 1.0)

        for i, snap in enumerate(current_snaps):
            rows.append(EmployeeTrajectoryPrediction(
                id=uuid.uuid4(),
                employee_id=snap.employee_id,
                snapshot_date=snapshot_date,
                horizon_days=horizon_days,
                predicted_disengagement_risk=round(float(dis_probs[i]), 4),
                predicted_impact_score=round(float(impact_preds[i]), 4),
                confidence=round(float(confidences[i]), 4),
                model_version=model_version,
            ))

    session.bulk_save_objects(rows)
    session.flush()
    return len(rows)
