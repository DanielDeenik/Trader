"""Tests for API health endpoint."""
import pytest
from fastapi.testclient import TestClient
from social_arb.api.main import create_app


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


def test_health_endpoint(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("healthy", "degraded", "unhealthy")
    assert "db_backend" in data
    assert "table_counts" in data


def test_health_has_table_counts(client):
    response = client.get("/api/v1/health")
    data = response.json()
    assert "signals" in data["table_counts"]
    assert "mosaics" in data["table_counts"]


def test_root_redirect(client):
    response = client.get("/", follow_redirects=False)
    assert response.status_code in (200, 307)
