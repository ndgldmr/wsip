"""
Sprint 1 acceptance tests — auth + RBAC.

Covers:
  - /health requires no auth
  - Protected routes require a valid Bearer token
  - Invalid/missing tokens → 401
  - analyst-token on employee profile → 403 (wrong role, no audit log for this path yet)
  - admin-token on stubbed route → 404 (not 401/403)
"""

import uuid


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
    def test_admin_token_reaches_stub(self, client):
        """Valid admin token on a real (stubbed) route → 404, not 401/403."""
        resp = client.get(
            f"/orgs/{uuid.uuid4()}/overview",
            headers={"Authorization": "Bearer admin-token"},
            params={"as_of": "2026-04-06"},
        )
        assert resp.status_code == 404

    def test_manager_token_reaches_stub(self, client):
        resp = client.get(
            f"/teams/{uuid.uuid4()}/health",
            headers={"Authorization": "Bearer manager-token"},
            params={"week_key": 202610},
        )
        assert resp.status_code == 404

    def test_analyst_token_reaches_stub(self, client):
        resp = client.get(
            f"/orgs/{uuid.uuid4()}/overview",
            headers={"Authorization": "Bearer analyst-token"},
            params={"as_of": "2026-04-06"},
        )
        assert resp.status_code == 404


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
        """admin-token reaches the generate endpoint (returns not_implemented, not 403)."""
        resp = client.post(
            "/admin/generate",
            headers={"Authorization": "Bearer admin-token"},
            params={"seed": 1, "start_date": "2025-01-01", "end_date": "2026-01-01"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "not_implemented"


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
