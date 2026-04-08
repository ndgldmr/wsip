"""
Admin router — data generation, ETL pipeline triggers, and operational queries.

All endpoints require the "admin" role.
"""

import time
from datetime import date, datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.dependencies import get_db, require_role
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
    db: Session = Depends(get_db),
) -> dict:
    """Trigger the daily ETL pipeline for snapshot_date."""
    from etl.pipeline import run_daily_pipeline

    t0 = time.perf_counter()
    counts = run_daily_pipeline(snapshot_date, db)

    if run_ml:
        from ml.archetypes import run_archetype_clustering
        from ml.trajectory import run_trajectory_predictions

        counts["archetypes"] = run_archetype_clustering(snapshot_date, db)
        counts["trajectories"] = run_trajectory_predictions(snapshot_date, db)
        db.commit()

    elapsed = round(time.perf_counter() - t0, 2)
    return {
        "status": "completed",
        "snapshot_date": str(snapshot_date),
        "elapsed_seconds": elapsed,
        "rows_written": counts,
    }


@router.get("/run_history")
def get_run_history(
    limit: int = 50,
    current_user: dict = require_role("admin"),
    db: Session = Depends(get_db),
) -> list:
    """List data generation runs, newest first."""
    from models.canonical import DataGenerationRun

    rows = (
        db.query(DataGenerationRun)
        .order_by(DataGenerationRun.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "run_id": str(r.run_id),
            "seed": r.seed,
            "start_date": str(r.start_date),
            "end_date": str(r.end_date),
            "employee_count": r.employee_count,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


@router.get("/audit-log")
def get_audit_log(
    accessed_id: Optional[UUID] = None,
    from_ts: Optional[datetime] = None,
    to_ts: Optional[datetime] = None,
    outcome: Optional[str] = None,
    limit: int = 100,
    current_user: dict = require_role("admin"),
    db: Session = Depends(get_db),
) -> list:
    """Retrieve access audit log entries with optional filters."""
    from models.auth import AccessAuditLog

    q = db.query(AccessAuditLog).order_by(AccessAuditLog.access_ts.desc())

    if accessed_id is not None:
        q = q.filter(AccessAuditLog.accessed_id == accessed_id)
    if from_ts is not None:
        q = q.filter(AccessAuditLog.access_ts >= from_ts)
    if to_ts is not None:
        q = q.filter(AccessAuditLog.access_ts <= to_ts)
    if outcome is not None:
        q = q.filter(AccessAuditLog.outcome == outcome)

    rows = q.limit(limit).all()
    return [
        {
            "audit_id": str(r.audit_id),
            "viewer_user_id": str(r.viewer_user_id) if r.viewer_user_id else None,
            "accessed_scope": r.accessed_scope,
            "accessed_id": str(r.accessed_id) if r.accessed_id else None,
            "access_ts": r.access_ts.isoformat() if r.access_ts else None,
            "action": r.action,
            "outcome": r.outcome,
            "request_id": r.request_id,
        }
        for r in rows
    ]
