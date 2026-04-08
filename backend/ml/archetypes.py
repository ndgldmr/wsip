"""
Archetype clustering — Sprint 6.

KMeans (k=8) over employee feature snapshots for a given date.
Assigns human-readable labels by inspecting which feature dimension
dominates each cluster's scaled centroid.

run_archetype_clustering() writes:
  - employee_archetype_assignments rows (DELETE+INSERT for snapshot_date)
  - employee_feature_snapshots.archetype_label (UPDATE)
"""

from __future__ import annotations

import uuid
from datetime import date
from typing import Any

import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sqlalchemy import text
from sqlalchemy.orm import Session

from models.simulations import EmployeeArchetypeAssignment

# Feature columns fed to KMeans (must exist on EmployeeFeatureSnapshot)
_FEATURE_COLS: list[str] = [
    "experiment_runs_30d",
    "commits_30d",
    "meeting_load_hours_30d",
    "collaboration_breadth_30d",
    "cross_team_interaction_rate_30d",
    "knowledge_creation_score",
    "activity_score_30d",
    "glue_person_score",
    "underutilization_score",
    "overload_score",
]

# Human-readable label assigned based on which scaled centroid dimension is highest.
# Priority order: if multiple features tie, earlier entry wins.
_LABEL_MAP: list[tuple[str, str]] = [
    ("experiment_runs_30d",          "Research Pioneer"),
    ("glue_person_score",            "Glue Person"),
    ("meeting_load_hours_30d",       "Meeting Heavy"),
    ("knowledge_creation_score",     "Knowledge Creator"),
    ("commits_30d",                  "Deep Contributor"),
    ("collaboration_breadth_30d",    "Collaborator"),
    ("overload_score",               "Overloaded"),
    ("underutilization_score",       "Underutilizer"),
]
# Fallback when no feature clearly dominates
_FALLBACK_LABEL = "Balanced Performer"

# Readable signal names for top_signal columns
_SIGNAL_NAMES: dict[str, str] = {
    "experiment_runs_30d":           "experiment_activity",
    "commits_30d":                   "commit_volume",
    "meeting_load_hours_30d":        "meeting_load",
    "collaboration_breadth_30d":     "collab_breadth",
    "cross_team_interaction_rate_30d": "cross_team_rate",
    "knowledge_creation_score":      "knowledge_creation",
    "activity_score_30d":            "activity_level",
    "glue_person_score":             "glue_influence",
    "underutilization_score":        "underutilization",
    "overload_score":                "overload_pressure",
}


def _label_cluster(centroid_scaled: np.ndarray) -> str:
    """Return a human-readable label from a standardised centroid vector."""
    best_val = -np.inf
    best_label = _FALLBACK_LABEL
    for col, label in _LABEL_MAP:
        idx = _FEATURE_COLS.index(col)
        if centroid_scaled[idx] > best_val:
            best_val = centroid_scaled[idx]
            best_label = label
    # Only assign a specific label when the centroid's best dimension is
    # meaningfully above average (> 0.3 std dev above mean in scaled space).
    if best_val < 0.3:
        return _FALLBACK_LABEL
    return best_label


def _top_signals(raw_values: dict[str, float], n: int = 3) -> list[str]:
    """Return the top-n feature signal names by raw value (highest first)."""
    sorted_cols = sorted(_FEATURE_COLS, key=lambda c: raw_values.get(c, 0.0), reverse=True)
    return [_SIGNAL_NAMES.get(c, c) for c in sorted_cols[:n]]


def run_archetype_clustering(
    snapshot_date: date,
    session: Session,
    n_clusters: int = 8,
    model_version: str = "wsip-0.1",
) -> int:
    """Cluster employees for snapshot_date and persist archetype assignments.

    Returns the number of rows written to employee_archetype_assignments.
    """
    from models.features import EmployeeFeatureSnapshot

    snaps = (
        session.query(EmployeeFeatureSnapshot)
        .filter(EmployeeFeatureSnapshot.snapshot_date == snapshot_date)
        .all()
    )
    if not snaps:
        return 0

    # Build feature matrix (float, fill None → 0)
    def _fv(snap: Any) -> list[float]:
        return [float(getattr(snap, c) or 0) for c in _FEATURE_COLS]

    employee_ids: list[uuid.UUID] = [s.employee_id for s in snaps]
    X_raw = np.array([_fv(s) for s in snaps], dtype=float)

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_raw)

    # Clamp n_clusters to number of samples (edge case for small test datasets)
    k = min(n_clusters, len(snaps))
    km = KMeans(n_clusters=k, random_state=42, n_init=10)
    labels = km.fit_predict(X_scaled)
    centroids_scaled = km.cluster_centers_  # shape (k, n_features)

    cluster_labels: list[str] = [_label_cluster(centroids_scaled[i]) for i in range(k)]

    # Delete existing assignments for this snapshot_date
    session.execute(
        text("DELETE FROM employee_archetype_assignments WHERE snapshot_date = :snap"),
        {"snap": snapshot_date},
    )
    session.flush()

    rows: list[EmployeeArchetypeAssignment] = []
    archetype_by_employee: dict[uuid.UUID, str] = {}
    for i, snap in enumerate(snaps):
        cluster_id = int(labels[i])
        label = cluster_labels[cluster_id]
        raw_vals = {_FEATURE_COLS[j]: float(X_raw[i, j]) for j in range(len(_FEATURE_COLS))}
        signals = _top_signals(raw_vals)

        rows.append(EmployeeArchetypeAssignment(
            id=uuid.uuid4(),
            employee_id=employee_ids[i],
            snapshot_date=snapshot_date,
            archetype_label=label,
            cluster_id=cluster_id,
            top_signal_1=signals[0] if len(signals) > 0 else None,
            top_signal_2=signals[1] if len(signals) > 1 else None,
            top_signal_3=signals[2] if len(signals) > 2 else None,
            model_version=model_version,
        ))
        archetype_by_employee[employee_ids[i]] = label

    session.bulk_save_objects(rows)

    # Back-fill archetype_label on employee_feature_snapshots
    for snap in snaps:
        snap.archetype_label = archetype_by_employee[snap.employee_id]

    session.flush()
    return len(rows)
