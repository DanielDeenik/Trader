"""Tests for analysis API."""

import pytest
from fastapi.testclient import TestClient
from social_arb.api.main import create_app


@pytest.fixture
def client():
    """Create test client."""
    app = create_app()
    return TestClient(app)


def test_analyze_endpoint_empty(client):
    """Test analyze endpoint with no symbols (use defaults)."""
    resp = client.post("/api/v1/analyze", json={})
    assert resp.status_code == 200
    data = resp.json()
    assert "symbols_analyzed" in data
    assert "mosaics_created" in data
    assert "theses_created" in data
    assert "errors" in data


def test_analyze_endpoint_with_symbols(client):
    """Test analyze endpoint with specific symbols."""
    resp = client.post(
        "/api/v1/analyze",
        json={"symbols": ["NVDA", "AAPL"]},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data["symbols_analyzed"], int)
    assert isinstance(data["mosaics_created"], int)
    assert isinstance(data["theses_created"], int)
    assert isinstance(data["errors"], list)


def test_engine_endpoint(client):
    """Test engine endpoint."""
    resp = client.get("/api/v1/engine/NVDA")
    assert resp.status_code == 200
    data = resp.json()
    assert data["symbol"] == "NVDA"
    assert "engines" in data
    assert isinstance(data["engines"], dict)


def test_engine_endpoint_lowercase(client):
    """Test engine endpoint with lowercase symbol."""
    resp = client.get("/api/v1/engine/aapl")
    assert resp.status_code == 200
    data = resp.json()
    assert data["symbol"] == "AAPL"
    assert "engines" in data


def test_engine_endpoint_with_portfolio_value(client):
    """Test engine endpoint with custom portfolio value."""
    resp = client.get("/api/v1/engine/NVDA?portfolio_value=50000")
    assert resp.status_code == 200
    data = resp.json()
    assert data["symbol"] == "NVDA"
    assert "engines" in data
