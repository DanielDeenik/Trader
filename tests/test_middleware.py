"""Tests for API middleware."""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path):
    import os
    db_path = str(tmp_path / "test.db")
    os.environ["SOCIAL_ARB_DB"] = db_path
    from social_arb.config import Config
    from social_arb.api import deps
    cfg = Config()
    deps.config = cfg
    deps.ensure_db()
    from social_arb.api.main import create_app
    app = create_app()
    return TestClient(app)


def test_health_not_rate_limited(client):
    for _ in range(20):
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200


def test_request_logging_middleware(client):
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json()["status"] in ("healthy", "unhealthy", "degraded")
