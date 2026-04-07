"""
Shock injection functions — DB-level modifications to simulate discrete life events.

All functions operate on already-inserted rows via the provided SQLAlchemy session.
They are called by SyntheticGenerator after bulk insert, and can also be invoked
independently for ad-hoc scenario testing.
"""

import uuid
from datetime import date, datetime, timedelta

import sqlalchemy as sa

from models.canonical import Employee, EmployeeChangeEvent, EmployeeProjectAssignment
from models.raw_events import (
    ChatMetadataEvent,
    CodeReviewEvent,
    DocumentEvent,
    ExperimentRunEvent,
    GitCommitEvent,
    MeetingEvent,
    PullRequestEvent,
    ResearchArtifactEvent,
    TaskEvent,
    TrainingCompletionEvent,
)

# Tables that carry per-employee, per-day activity rows (all deletable by date range)
_ACTIVITY_TABLES_AND_TS: list[tuple[type, str]] = [
    (GitCommitEvent, "commit_ts"),
    (PullRequestEvent, "opened_at"),
    (CodeReviewEvent, "review_ts"),
    (ExperimentRunEvent, "started_at"),
    (ResearchArtifactEvent, "created_at"),
    (DocumentEvent, "event_ts"),
    (TaskEvent, "event_ts"),
    (MeetingEvent, "start_ts"),
    (ChatMetadataEvent, "event_ts"),
    (TrainingCompletionEvent, "completed_at"),
]


def inject_manager_change(
    employee_id: uuid.UUID,
    new_manager_id: uuid.UUID,
    event_date: date,
    session: sa.orm.Session,
) -> None:
    """Record a manager change and update the employee's manager FK."""
    employee = session.get(Employee, employee_id)
    if employee is None:
        return

    old_manager_id = employee.manager_employee_id

    event = EmployeeChangeEvent(
        employee_id=employee_id,
        change_type="manager_change",
        event_date=event_date,
        from_value=str(old_manager_id) if old_manager_id else None,
        to_value=str(new_manager_id),
    )
    session.add(event)

    employee.manager_employee_id = new_manager_id
    session.flush()


def inject_project_reassignment(
    employee_id: uuid.UUID,
    from_project_id: uuid.UUID,
    to_project_id: uuid.UUID,
    event_date: date,
    session: sa.orm.Session,
) -> None:
    """End the employee's assignment on from_project; start one on to_project."""
    # Close the old assignment
    old = session.execute(
        sa.select(EmployeeProjectAssignment).where(
            EmployeeProjectAssignment.employee_id == employee_id,
            EmployeeProjectAssignment.project_id == from_project_id,
        )
    ).scalar_one_or_none()
    if old is not None:
        old.end_date = event_date

    # Open a new assignment
    new_assignment = EmployeeProjectAssignment(
        employee_id=employee_id,
        project_id=to_project_id,
        assignment_role="contributor",
        allocation_pct=1.0,
        start_date=event_date,
        staffing_source="internal",
    )
    session.add(new_assignment)

    session.add(
        EmployeeChangeEvent(
            employee_id=employee_id,
            change_type="project_reassignment",
            event_date=event_date,
            from_value=str(from_project_id),
            to_value=str(to_project_id),
        )
    )
    session.flush()


def inject_burnout_episode(
    employee_id: uuid.UUID,
    start_date: date,
    end_date: date,
    session: sa.orm.Session,
    keep_fraction: float = 0.25,
) -> None:
    """
    Simulate burnout by deleting ~75 % of activity rows in the window.

    keep_fraction controls how much activity survives (default 25 %).
    Deletion is deterministic: rows are ordered by PK and we keep the first
    keep_fraction fraction, deleting the rest — no RNG needed here.
    """
    start_dt = datetime(start_date.year, start_date.month, start_date.day)
    end_dt = datetime(end_date.year, end_date.month, end_date.day, 23, 59, 59)

    for model, ts_col in _ACTIVITY_TABLES_AND_TS:
        pk_col = list(model.__table__.primary_key.columns)[0]
        ts_column = model.__table__.c[ts_col]
        emp_col = _get_employee_col(model)

        rows = session.execute(
            sa.select(pk_col).where(
                emp_col == employee_id,
                ts_column >= start_dt,
                ts_column <= end_dt,
            ).order_by(pk_col)
        ).scalars().all()

        keep_n = max(0, int(len(rows) * keep_fraction))
        ids_to_delete = rows[keep_n:]
        if ids_to_delete:
            session.execute(
                sa.delete(model).where(pk_col.in_(ids_to_delete))
            )

    session.add(
        EmployeeChangeEvent(
            employee_id=employee_id,
            change_type="burnout_episode",
            event_date=start_date,
            from_value=str(start_date),
            to_value=str(end_date),
        )
    )
    session.flush()


def inject_research_breakthrough(
    employee_id: uuid.UUID,
    event_date: date,
    project_id: uuid.UUID | None,
    session: sa.orm.Session,
    window_days: int = 14,
) -> None:
    """
    Simulate a research breakthrough by inserting a burst of high-value research
    and experiment events in a window around event_date.
    """
    for offset in range(window_days):
        ts = datetime(
            event_date.year, event_date.month, event_date.day, 9, 0, 0
        ) + timedelta(days=offset)

        session.add(
            ResearchArtifactEvent(
                employee_id=employee_id,
                project_id=project_id,
                created_at=ts,
                artifact_type="report",
                collaboration_count=2,
                word_count=3000 + offset * 200,
            )
        )
        session.add(
            ExperimentRunEvent(
                employee_id=employee_id,
                project_id=project_id,
                started_at=ts,
                completed_at=ts + timedelta(hours=4),
                experiment_type="model_train",
                status="completed",
                compute_hours=4.0,
                outcome_metric_name="accuracy",
                outcome_metric_value=0.80 + offset * 0.005,
            )
        )

    session.add(
        EmployeeChangeEvent(
            employee_id=employee_id,
            change_type="research_breakthrough",
            event_date=event_date,
            from_value=None,
            to_value=str(project_id) if project_id else None,
        )
    )
    session.flush()


def inject_leave_of_absence(
    employee_id: uuid.UUID,
    start_date: date,
    end_date: date,
    session: sa.orm.Session,
) -> None:
    """Delete all activity rows for the employee during the leave window."""
    start_dt = datetime(start_date.year, start_date.month, start_date.day)
    end_dt = datetime(end_date.year, end_date.month, end_date.day, 23, 59, 59)

    for model, ts_col in _ACTIVITY_TABLES_AND_TS:
        ts_column = model.__table__.c[ts_col]
        emp_col = _get_employee_col(model)
        session.execute(
            sa.delete(model).where(
                emp_col == employee_id,
                ts_column >= start_dt,
                ts_column <= end_dt,
            )
        )

    session.add(
        EmployeeChangeEvent(
            employee_id=employee_id,
            change_type="leave_of_absence",
            event_date=start_date,
            from_value=str(start_date),
            to_value=str(end_date),
        )
    )
    session.flush()


def _get_employee_col(model: type) -> sa.Column:
    """Return the employee_id column for a raw event model."""
    table = model.__table__
    # Most tables use employee_id; code_review uses reviewer_employee_id
    if "employee_id" in table.c:
        return table.c["employee_id"]
    return table.c["reviewer_employee_id"]
