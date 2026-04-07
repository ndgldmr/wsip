import uuid

from fastapi import APIRouter, HTTPException

from app.dependencies import require_role

router = APIRouter()

_ROLES = ("admin", "manager", "hrbp")


@router.post("/")
def create_simulation(
    current_user: dict = require_role(*_ROLES),
) -> dict:
    """Create a new simulation run. Implemented in S6."""
    raise HTTPException(status_code=404, detail="Not found")


@router.post("/{simulation_run_id}/moves")
def add_simulation_move(
    simulation_run_id: uuid.UUID,
    current_user: dict = require_role(*_ROLES),
) -> dict:
    """Add an employee move to a simulation. Implemented in S6."""
    raise HTTPException(status_code=404, detail="Not found")


@router.post("/{simulation_run_id}/compute")
def compute_simulation(
    simulation_run_id: uuid.UUID,
    current_user: dict = require_role(*_ROLES),
) -> dict:
    """Compute simulation outcomes synchronously. Implemented in S6."""
    raise HTTPException(status_code=404, detail="Not found")


@router.get("/{simulation_run_id}/outcomes")
def get_simulation_outcomes(
    simulation_run_id: uuid.UUID,
    current_user: dict = require_role(*_ROLES),
) -> list:
    """Get computed outcomes for a simulation. Implemented in S6."""
    raise HTTPException(status_code=404, detail="Not found")
