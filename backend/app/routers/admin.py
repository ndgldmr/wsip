import time
from datetime import date

from fastapi import APIRouter, HTTPException

from app.config import settings
from app.dependencies import require_role
from synthetic.generate import SyntheticGenerator

router = APIRouter()


@router.post("/generate")
def trigger_generate(
    seed: int,
    start_date: date,
    end_date: date,
    n_employees: int = 300,
    current_user: dict = require_role("admin"),
) -> dict:
    """Generate a seeded synthetic dataset and persist to the database."""
    if end_date <= start_date:
        raise HTTPException(status_code=422, detail="end_date must be after start_date")
    t0 = time.perf_counter()
    gen = SyntheticGenerator(seed=seed, db_url=settings.database_url)
    run_id = gen.generate(
        start_date=start_date,
        end_date=end_date,
        n_employees=n_employees,
    )
    elapsed = round(time.perf_counter() - t0, 2)
    return {
        "run_id": str(run_id),
        "status": "completed",
        "elapsed_seconds": elapsed,
        "seed": seed,
        "n_employees": n_employees,
    }


@router.post("/run_pipeline")
def trigger_pipeline(
    snapshot_date: date,
    run_ml: bool = False,
    current_user: dict = require_role("admin"),
) -> dict:
    """Trigger the daily ETL pipeline. Implemented in S3."""
    return {"status": "not_implemented", "sprint": "S3"}


@router.get("/run_history")
def get_run_history(current_user: dict = require_role("admin")) -> list:
    """List data generation runs. Implemented in S9."""
    return []


@router.get("/audit-log")
def get_audit_log(
    accessed_id: str | None = None,
    current_user: dict = require_role("admin"),
) -> list:
    """Retrieve audit log entries. Implemented in S9."""
    return []
