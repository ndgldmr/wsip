"""
Simulations router — workforce simulation run management.

Simulations let managers model the projected impact of employee moves
(reorgs, transfers) on team health metrics before committing changes.
Requires roles: admin, manager, hrbp.

Endpoints:
  POST /simulations/                         — create a simulation run
  POST /simulations/{id}/moves               — add an employee move
  POST /simulations/{id}/compute             — compute outcomes (synchronous)
  GET  /simulations/{id}/outcomes            — retrieve computed outcomes
"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.dependencies import get_db, require_role
from models.simulations import SimulationEmployeeMove, SimulationRun
from schemas.simulations import (
    SimulationCreateIn,
    SimulationMoveIn,
    SimulationMoveOut,
    SimulationOutcomeOut,
    SimulationRunOut,
)

router = APIRouter()

_ROLES = ("admin", "manager", "hrbp")


@router.post("/", response_model=SimulationRunOut)
def create_simulation(
    body: SimulationCreateIn,
    current_user: dict = require_role(*_ROLES),
    db: Session = Depends(get_db),
) -> SimulationRunOut:
    """Create a new simulation run in draft status.

    The run holds a snapshot_date that determines which feature baselines
    will be used when computing outcomes.
    """
    creator = current_user.get("user_id", "unknown")
    sim = SimulationRun(
        id=uuid.uuid4(),
        name=body.name,
        description=body.description,
        created_by=creator,
        status="draft",
        snapshot_date=body.snapshot_date,
    )
    db.add(sim)

    # Audit log entry — simulation creation is sensitive (named employee moves)
    _write_audit_log(db, current_user, "create_simulation", str(sim.id))

    db.commit()
    db.refresh(sim)
    return SimulationRunOut.model_validate(sim)


@router.post("/{simulation_run_id}/moves", response_model=SimulationMoveOut)
def add_simulation_move(
    simulation_run_id: uuid.UUID,
    body: SimulationMoveIn,
    current_user: dict = require_role(*_ROLES),
    db: Session = Depends(get_db),
) -> SimulationMoveOut:
    """Add an employee move to a draft simulation run.

    Raises 404 if the run does not exist, 409 if the run has already been computed.
    """
    sim = db.get(SimulationRun, simulation_run_id)
    if sim is None:
        raise HTTPException(status_code=404, detail="Simulation run not found")
    if sim.status != "draft":
        raise HTTPException(status_code=409, detail="Cannot modify a computed simulation run")

    move = SimulationEmployeeMove(
        id=uuid.uuid4(),
        simulation_run_id=simulation_run_id,
        employee_id=body.employee_id,
        from_team_id=body.from_team_id,
        to_team_id=body.to_team_id,
        allocation_pct_change=body.allocation_pct_change,
        notes=body.notes,
    )
    db.add(move)
    db.commit()
    db.refresh(move)
    return SimulationMoveOut.model_validate(move)


@router.post("/{simulation_run_id}/compute", response_model=SimulationRunOut)
def compute_simulation(
    simulation_run_id: uuid.UUID,
    current_user: dict = require_role(*_ROLES),
    db: Session = Depends(get_db),
) -> SimulationRunOut:
    """Compute outcomes for all moves in the simulation run.

    Runs synchronously (expected < 1s for typical org sizes).
    Sets status to 'computed' on success.  Idempotent — re-computing
    overwrites prior outcomes.
    """
    sim = db.get(SimulationRun, simulation_run_id)
    if sim is None:
        raise HTTPException(status_code=404, detail="Simulation run not found")

    from ml.simulation import compute_simulation_outcomes

    compute_simulation_outcomes(simulation_run_id, db)

    # Update updated_at timestamp
    sim.updated_at = datetime.now(timezone.utc)

    _write_audit_log(db, current_user, "compute_simulation", str(simulation_run_id))
    db.commit()
    db.refresh(sim)
    return SimulationRunOut.model_validate(sim)


@router.get("/{simulation_run_id}/outcomes", response_model=list[SimulationOutcomeOut])
def get_simulation_outcomes(
    simulation_run_id: uuid.UUID,
    current_user: dict = require_role(*_ROLES),
    db: Session = Depends(get_db),
) -> list[SimulationOutcomeOut]:
    """Return all computed outcomes for a simulation run.

    Returns an empty list for draft runs that have not yet been computed.
    """
    from models.simulations import SimulationOutcome

    sim = db.get(SimulationRun, simulation_run_id)
    if sim is None:
        raise HTTPException(status_code=404, detail="Simulation run not found")

    outcomes = (
        db.query(SimulationOutcome)
        .filter(SimulationOutcome.simulation_run_id == simulation_run_id)
        .order_by(SimulationOutcome.employee_id, SimulationOutcome.metric_name)
        .all()
    )
    return [SimulationOutcomeOut.model_validate(o) for o in outcomes]


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _write_audit_log(db, current_user: dict, action: str, target_id: str) -> None:
    """Best-effort audit log write — does not raise on failure."""
    try:
        from models.auth import AccessAuditLog
        import uuid as _uuid

        user_id_str = current_user.get("user_id")
        if not user_id_str:
            return
        log = AccessAuditLog(
            viewer_user_id=_uuid.UUID(user_id_str),
            accessed_scope="simulation",
            accessed_id=_uuid.UUID(target_id),
            action=action,
            outcome="success",
        )
        db.add(log)
    except Exception:
        pass
