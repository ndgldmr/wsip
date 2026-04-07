"""
FastAPI dependencies:
  - get_db()               — yields a SQLAlchemy Session per request
  - get_current_user()     — validates Bearer token, returns user dict
  - require_role(*roles)   — returns a Depends() that enforces role membership
  - require_employee_access() — checks viewer_permissions + manager chain, writes audit log
"""

import uuid
from collections.abc import Generator
from typing import Annotated

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    authorization: Annotated[str | None, Header()] = None,
    db: Session = Depends(get_db),
) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    token = authorization.removeprefix("Bearer ").strip()
    user = settings.token_map.get(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    return user


def require_role(*roles: str) -> Depends:
    """
    Returns a FastAPI Depends() that passes if the current user has ANY of the given roles.

    Usage:
        current_user: dict = require_role("admin", "org_analytics")
    """

    def _check(current_user: dict = Depends(get_current_user)) -> dict:
        if not any(r in current_user.get("roles", []) for r in roles):
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return current_user

    return Depends(_check)


def require_employee_access(
    employee_id: uuid.UUID,
    current_user: dict,
    db: Session,
) -> None:
    """
    Checks whether current_user may access a specific employee's individual data.
    Writes an AccessAuditLog row regardless of outcome.

    Access is granted if the user has any of:
      - role 'admin' or 'hrbp'
      - role 'manager' AND employee.manager_employee_id matches user's employee_id
      - a viewer_permissions row (target_scope='employee', target_id=employee_id,
        permission_type='view_individual')

    Raises HTTP 403 on denial.
    """
    from models.auth import AccessAuditLog, AppUser, ViewerPermission
    from models.canonical import Employee

    roles = current_user.get("roles", [])
    user_id_str = current_user.get("user_id")
    user_uuid = uuid.UUID(user_id_str) if user_id_str else None

    granted = False

    # admin / hrbp always allowed
    if "admin" in roles or "hrbp" in roles:
        granted = True

    # manager can see their direct reports
    if not granted and "manager" in roles and user_uuid:
        app_user = db.query(AppUser).filter_by(user_id=user_uuid).first()
        if app_user and app_user.employee_id:
            target_emp = db.query(Employee).filter_by(employee_id=employee_id).first()
            if target_emp and target_emp.manager_employee_id == app_user.employee_id:
                granted = True

    # explicit viewer_permissions grant
    if not granted and user_uuid:
        perm = (
            db.query(ViewerPermission)
            .filter_by(
                viewer_user_id=user_uuid,
                target_scope="employee",
                target_id=employee_id,
                permission_type="view_individual",
            )
            .first()
        )
        if perm:
            granted = True

    outcome = "success" if granted else "denied"

    # always write audit log
    if user_uuid:
        log_entry = AccessAuditLog(
            viewer_user_id=user_uuid,
            accessed_scope="employee",
            accessed_id=employee_id,
            action="read_profile",
            outcome=outcome,
        )
        db.add(log_entry)
        db.commit()

    if not granted:
        raise HTTPException(status_code=403, detail="Access denied to employee data")
