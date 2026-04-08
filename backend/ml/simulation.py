"""
Simulation outcomes computation — Sprint 6.

For each SimulationEmployeeMove in a run, loads the employee's baseline
feature snapshot, applies deterministic re-weighting rules, re-runs the
five core metric functions, and writes SimulationOutcome rows.

Re-weighting rules (applied to a SimpleNamespace clone):
  allocation_pct_change > 0  → raises project_allocation_utilization_score
  allocation_pct_change < 0  → lowers project_allocation_utilization_score
  team change (from != to)   → raises cross_team_interaction_rate_30d by 0.10,
                                adjusts collaboration_breadth_30d by ±5

All metric functions are imported directly from etl.metrics — no re-training.
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace

from sqlalchemy import text
from sqlalchemy.orm import Session

from etl.metrics import (
    clamp01,
    compute_disengagement_risk,
    compute_glue_score,
    compute_overload,
    compute_skill_utilization,
    compute_underutilization,
)
from models.features import EmployeeFeatureSnapshot
from models.simulations import SimulationEmployeeMove, SimulationOutcome, SimulationRun

_METRICS = [
    ("underutilization_score",    compute_underutilization),
    ("overload_score",            compute_overload),
    ("disengagement_risk_score",  compute_disengagement_risk),
    ("skill_utilization_score",   compute_skill_utilization),
    ("glue_person_score",         compute_glue_score),
]

# Allocation adjustment sensitivity: each 1% change moves the score by this amount
_ALLOC_SENSITIVITY = 0.005   # 20% increase → +0.10 score


def _clone_snap(snap: EmployeeFeatureSnapshot, role_family: str) -> SimpleNamespace:
    """Copy feature columns into a mutable SimpleNamespace."""
    ns = SimpleNamespace()
    for col in [
        "activity_drop_30d", "project_allocation_utilization_score",
        "skill_utilization_score", "collaboration_breadth_30d",
        "knowledge_creation_score", "activity_drop_14d",
        "cross_team_interaction_rate_30d", "meeting_load_hours_30d",
        "active_project_count", "activity_score_30d", "activity_score_90d",
        "collaboration_centrality_30d",
    ]:
        setattr(ns, col, float(getattr(snap, col) or 0))
    ns.role_family = role_family
    return ns


def _apply_move_rules(ns: SimpleNamespace, move: SimulationEmployeeMove) -> None:
    """Apply deterministic re-weighting rules in-place."""
    alloc_change = float(move.allocation_pct_change or 0)
    if alloc_change != 0:
        ns.project_allocation_utilization_score = clamp01(
            ns.project_allocation_utilization_score + alloc_change * _ALLOC_SENSITIVITY
        )

    if move.from_team_id != move.to_team_id:
        # Team transfer: cross-team interaction rises; collaboration breadth adjusts
        ns.cross_team_interaction_rate_30d = clamp01(ns.cross_team_interaction_rate_30d + 0.10)
        direction = 1 if alloc_change >= 0 else -1
        ns.collaboration_breadth_30d = max(0.0, ns.collaboration_breadth_30d + direction * 5)


def compute_simulation_outcomes(
    simulation_run_id: uuid.UUID,
    session: Session,
    model_version: str = "wsip-0.1",
) -> int:
    """Compute and persist outcomes for all moves in a simulation run.

    Returns the number of SimulationOutcome rows written.
    """
    from models.canonical import Employee

    sim_run: SimulationRun | None = session.get(SimulationRun, simulation_run_id)
    if sim_run is None:
        raise ValueError(f"SimulationRun {simulation_run_id} not found")

    moves: list[SimulationEmployeeMove] = (
        session.query(SimulationEmployeeMove)
        .filter(SimulationEmployeeMove.simulation_run_id == simulation_run_id)
        .all()
    )
    if not moves:
        sim_run.status = "computed"
        session.flush()
        return 0

    snapshot_date = sim_run.snapshot_date

    # Delete any prior outcomes for this run (idempotent)
    session.execute(
        text("DELETE FROM simulation_outcomes WHERE simulation_run_id = :rid"),
        {"rid": simulation_run_id},
    )
    session.flush()

    outcome_rows: list[SimulationOutcome] = []

    for move in moves:
        snap: EmployeeFeatureSnapshot | None = session.get(
            EmployeeFeatureSnapshot, (move.employee_id, snapshot_date)
        )
        if snap is None:
            # No baseline snapshot — skip this move
            continue

        emp: Employee | None = session.get(Employee, move.employee_id)
        role_family = emp.role_family if emp else "engineering"

        baseline_ns = _clone_snap(snap, role_family)
        simulated_ns = _clone_snap(snap, role_family)
        _apply_move_rules(simulated_ns, move)

        for metric_name, compute_fn in _METRICS:
            baseline_val = float(getattr(snap, metric_name) or 0)
            simulated_val = round(compute_fn(simulated_ns), 4)
            delta = round(simulated_val - baseline_val, 4)

            outcome_rows.append(SimulationOutcome(
                id=uuid.uuid4(),
                simulation_run_id=simulation_run_id,
                employee_id=move.employee_id,
                metric_name=metric_name,
                baseline_value=round(baseline_val, 4),
                simulated_value=simulated_val,
                delta=delta,
                team_scope_id=move.to_team_id,
                model_version=model_version,
            ))

    session.bulk_save_objects(outcome_rows)

    sim_run.status = "computed"
    session.flush()
    return len(outcome_rows)
