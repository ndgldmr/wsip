"""
pytest fixtures for WSIP tests.

Two tiers:
  - `client`          — FastAPI TestClient with a stub DB (no Postgres required).
                        Sufficient for auth/routing tests (S1).
  - `real_db_engine`  — Real Postgres session (requires wsip_test DB).
                        Used in integration tests (S3+).
"""

import os
import sys
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

# Make backend/ importable when running pytest from backend/
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

TEST_DB_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql://wsip:wsip_dev@localhost:5432/wsip_test",
)


# ---------------------------------------------------------------------------
# Lightweight stub session — no Postgres required
# ---------------------------------------------------------------------------

class _StubSession:
    """
    Minimal DB session stub. query() returns a MagicMock whose .filter_by()
    chain ultimately returns None (simulates empty DB), so RBAC checks
    fall through to "denied" or "not found" cleanly.
    """

    def query(self, *args, **kwargs):
        mock_q = MagicMock()
        mock_q.filter_by.return_value = mock_q
        mock_q.first.return_value = None
        mock_q.all.return_value = []
        return mock_q

    def add(self, obj):
        pass

    def commit(self):
        pass

    def rollback(self):
        pass

    def close(self):
        pass


@pytest.fixture
def stub_db():
    return _StubSession()


@pytest.fixture
def client(stub_db):
    """
    FastAPI TestClient backed by a stub DB session.
    Suitable for auth/routing/RBAC tests that don't need real data.
    """
    from app.dependencies import get_db
    from app.main import app

    def override_get_db():
        yield stub_db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Real Postgres fixtures — used from S3 onward
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def real_db_engine():
    """
    Creates wsip_test, runs migrations, yields engine, then downgrades.
    Requires Postgres to be running (locally or via docker compose).
    """
    import subprocess
    from sqlalchemy import create_engine, text

    root_url = TEST_DB_URL.rsplit("/", 1)[0] + "/postgres"
    root_engine = create_engine(root_url, isolation_level="AUTOCOMMIT")
    with root_engine.connect() as conn:
        db_name = TEST_DB_URL.rsplit("/", 1)[-1]
        exists = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": db_name}
        ).fetchone()
        if not exists:
            conn.execute(text(f'CREATE DATABASE "{db_name}"'))
    root_engine.dispose()

    env = {**os.environ, "DATABASE_URL": TEST_DB_URL}
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    subprocess.run(["alembic", "upgrade", "head"], cwd=backend_dir, env=env, check=True)

    from sqlalchemy import create_engine as _ce
    engine = _ce(TEST_DB_URL, pool_pre_ping=True)
    yield engine

    subprocess.run(["alembic", "downgrade", "base"], cwd=backend_dir, env=env, check=False)
    engine.dispose()


@pytest.fixture
def real_db(real_db_engine):
    from sqlalchemy.orm import sessionmaker
    Session = sessionmaker(bind=real_db_engine, autocommit=False, autoflush=False)
    session = Session()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def real_client(real_db):
    from app.dependencies import get_db
    from app.main import app

    def override():
        yield real_db

    app.dependency_overrides[get_db] = override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
