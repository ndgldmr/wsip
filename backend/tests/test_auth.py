"""
Sprint 1 + Sprint 4 acceptance tests — auth + RBAC.

Covers:
  - /health requires no auth
  - Protected routes require a valid Bearer token
  - Invalid/missing tokens → 401
  - analyst-token on employee profile → 403
  - manager-token on non-direct-report → 403
  - admin-token on employee profile → 200 + audit log (integration)
"""

import uuid

import pytest


class TestHealth:
    def test_health_no_auth(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


class TestAuthRequired:
    def test_no_auth_header(self, client):
        resp = client.get("/orgs/some-org-id/overview", params={"as_of": "2026-04-06"})
        assert resp.status_code == 401

    def test_malformed_auth_header(self, client):
        resp = client.get(
            "/orgs/some-org-id/overview",
            headers={"Authorization": "Basic abc123"},
            params={"as_of": "2026-04-06"},
        )
        assert resp.status_code == 401

    def test_bad_token(self, client):
        resp = client.get(
            "/orgs/some-org-id/overview",
            headers={"Authorization": "Bearer totally-invalid-token"},
            params={"as_of": "2026-04-06"},
        )
        assert resp.status_code == 401

    def test_empty_bearer(self, client):
        resp = client.get(
            "/orgs/some-org-id/overview",
            headers={"Authorization": "Bearer "},
            params={"as_of": "2026-04-06"},
        )
        assert resp.status_code == 401


class TestValidTokenRouting:
    def test_admin_token_reaches_handler(self, client):
        """Valid admin token gets past auth → not 401 or 403."""
        resp = client.get(
            f"/orgs/{uuid.uuid4()}/overview",
            headers={"Authorization": "Bearer admin-token"},
            params={"as_of": "2026-04-06"},
        )
        assert resp.status_code not in (401, 403)

    def test_manager_token_reaches_handler(self, client):
        resp = client.get(
            f"/teams/{uuid.uuid4()}/health",
            headers={"Authorization": "Bearer manager-token"},
            params={"week_key": 202610},
        )
        assert resp.status_code not in (401, 403)

    def test_analyst_token_reaches_handler(self, client):
        resp = client.get(
            f"/orgs/{uuid.uuid4()}/overview",
            headers={"Authorization": "Bearer analyst-token"},
            params={"as_of": "2026-04-06"},
        )
        assert resp.status_code not in (401, 403)


class TestRBACDenials:
    def test_analyst_denied_employee_profile(self, client):
        """analyst-token (org_analytics only) must not access individual employee profiles."""
        resp = client.get(
            f"/employees/{uuid.uuid4()}/profile",
            headers={"Authorization": "Bearer analyst-token"},
            params={"as_of": "2026-04-06"},
        )
        # require_employee_access checks viewer_permissions and manager chain;
        # analyst has neither → 403
        assert resp.status_code == 403

    def test_analyst_denied_admin_generate(self, client):
        """analyst-token must not trigger data generation (admin only)."""
        resp = client.post(
            "/admin/generate",
            headers={"Authorization": "Bearer analyst-token"},
            params={"seed": 1, "start_date": "2025-01-01", "end_date": "2026-01-01"},
        )
        assert resp.status_code == 403

    def test_manager_denied_admin_generate(self, client):
        """manager-token must not trigger data generation."""
        resp = client.post(
            "/admin/generate",
            headers={"Authorization": "Bearer manager-token"},
            params={"seed": 1, "start_date": "2025-01-01", "end_date": "2026-01-01"},
        )
        assert resp.status_code == 403

    def test_admin_can_generate(self, client):
        """admin-token reaches the generate endpoint (not 403)."""
        resp = client.post(
            "/admin/generate",
            headers={"Authorization": "Bearer admin-token"},
            params={"seed": 1, "start_date": "2025-01-01", "end_date": "2026-01-01"},
        )
        assert resp.status_code not in (401, 403)


class TestRBACManagerChain:
    """Stub-DB tests for manager-chain RBAC on employee endpoints.

    The stub session returns None for all queries, so:
      - AppUser lookup for manager-token → None → manager chain fails → denied (403)
      - analyst-token has org_analytics role only → denied (403)
    """

    def test_manager_denied_non_report_profile(self, client):
        """manager-token cannot access a random employee (not a direct report)."""
        import uuid
        resp = client.get(
            f"/employees/{uuid.uuid4()}/profile",
            headers={"Authorization": "Bearer manager-token"},
            params={"as_of": "2026-01-15"},
        )
        assert resp.status_code == 403

    def test_analyst_denied_employee_timeline(self, client):
        """org_analytics role must not access individual timelines."""
        import uuid
        resp = client.get(
            f"/employees/{uuid.uuid4()}/timeline",
            headers={"Authorization": "Bearer analyst-token"},
            params={"from_date": "2026-01-01", "to_date": "2026-01-15"},
        )
        assert resp.status_code == 403

    def test_analyst_denied_employee_insights(self, client):
        """org_analytics role must not access individual insights."""
        import uuid
        resp = client.get(
            f"/employees/{uuid.uuid4()}/insights",
            headers={"Authorization": "Bearer analyst-token"},
            params={"as_of": "2026-01-15"},
        )
        assert resp.status_code == 403


@pytest.mark.integration
class TestRBACEmployeeIntegration:
    """Integration tests requiring real Postgres.

    Seeds a minimal employee + feature snapshot, then verifies:
      - admin-token → 200 + audit log row outcome="success"
      - manager-token (non-report) → 403 + audit log row outcome="denied"
    """

    def test_admin_can_read_profile_and_audit_logged(self, real_client, real_db):
        import uuid
        from datetime import date

        from models.canonical import Employee, Team, Org
        from models.features import EmployeeFeatureSnapshot
        from models.auth import AccessAuditLog, AppUser

        # seed minimal org, team, employee
        org = Org(org_name="Test Org S4")
        real_db.add(org)
        real_db.flush()

        team = Team(team_name="Test Team S4", org_id=org.org_id, function_type="engineering")
        real_db.add(team)
        real_db.flush()

        emp = Employee(
            external_employee_ref=f"s4-test-{uuid.uuid4().hex[:8]}",
            full_name="Sprint Four Tester",
            email=f"s4.{uuid.uuid4().hex[:6]}@test.local",
            role_title="Senior Engineer",
            role_family="engineering",
            job_level="L4",
            team_id=team.team_id,
            org_id=org.org_id,
            hire_date=date(2023, 1, 1),
        )
        real_db.add(emp)
        real_db.flush()

        snap_date = date(2026, 1, 15)
        snap = EmployeeFeatureSnapshot(
            employee_id=emp.employee_id,
            snapshot_date=snap_date,
            underutilization_score=0.30,
            overload_score=0.20,
            disengagement_risk_score=0.15,
            glue_person_score=0.45,
        )
        real_db.add(snap)
        real_db.commit()

        resp = real_client.get(
            f"/employees/{emp.employee_id}/profile",
            headers={"Authorization": "Bearer admin-token"},
            params={"as_of": str(snap_date)},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["employee_id"] == str(emp.employee_id)
        assert 0.0 <= body["underutilization_score"] <= 1.0

        # audit log row must exist with outcome="success"
        audit = (
            real_db.query(AccessAuditLog)
            .filter_by(accessed_id=emp.employee_id, action="read_profile", outcome="success")
            .first()
        )
        assert audit is not None, "Expected audit log row with outcome='success'"

    def test_manager_denied_non_report_audit_logged(self, real_client, real_db):
        """manager-token on a non-direct-report employee → 403 + audit log denied."""
        import uuid
        from datetime import date

        from models.canonical import Employee, Team, Org
        from models.auth import AccessAuditLog

        # seed minimal org/team/employee to ensure the employee exists
        org = Org(org_name="Test Org S4 Deny")
        real_db.add(org)
        real_db.flush()

        team = Team(team_name="Test Team S4 Deny", org_id=org.org_id, function_type="engineering")
        real_db.add(team)
        real_db.flush()

        emp = Employee(
            external_employee_ref=f"s4-deny-{uuid.uuid4().hex[:8]}",
            full_name="Not My Report",
            email=f"s4deny.{uuid.uuid4().hex[:6]}@test.local",
            role_title="Engineer",
            role_family="engineering",
            job_level="L3",
            team_id=team.team_id,
            org_id=org.org_id,
            hire_date=date(2023, 6, 1),
        )
        real_db.add(emp)
        real_db.commit()

        resp = real_client.get(
            f"/employees/{emp.employee_id}/profile",
            headers={"Authorization": "Bearer manager-token"},
            params={"as_of": "2026-01-15"},
        )
        assert resp.status_code == 403, resp.text

        audit = (
            real_db.query(AccessAuditLog)
            .filter_by(accessed_id=emp.employee_id, action="read_profile", outcome="denied")
            .first()
        )
        assert audit is not None, "Expected audit log row with outcome='denied'"


class TestOpenAPIDocs:
    def test_swagger_ui_accessible(self, client):
        resp = client.get("/docs")
        assert resp.status_code == 200

    def test_redoc_accessible(self, client):
        resp = client.get("/redoc")
        assert resp.status_code == 200

    def test_openapi_json(self, client):
        resp = client.get("/openapi.json")
        assert resp.status_code == 200
        data = resp.json()
        # All expected route prefixes present
        paths = data["paths"]
        assert any(p.startswith("/admin") for p in paths)
        assert any(p.startswith("/orgs") for p in paths)
        assert any(p.startswith("/teams") for p in paths)
        assert any(p.startswith("/employees") for p in paths)
        assert any(p.startswith("/insights") for p in paths)
        assert any(p.startswith("/recommendations") for p in paths)
        assert any(p.startswith("/simulations") for p in paths)
