"""Tests for instruments CRUD API."""
import pytest
import uuid
from fastapi.testclient import TestClient
from social_arb.api.main import create_app


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


@pytest.fixture
def unique_symbol():
    """Generate unique symbol to avoid test conflicts."""
    return f"TST{uuid.uuid4().hex[:6].upper()}"


def test_list_instruments_empty(client):
    resp = client.get("/api/v1/instruments")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert isinstance(data["items"], list)
    assert "total" in data


def test_create_instrument(client, unique_symbol):
    resp = client.post("/api/v1/instruments", json={
        "symbol": unique_symbol, "name": "Test Corp", "type": "stock",
    })
    assert resp.status_code == 201
    assert resp.json()["symbol"] == unique_symbol


def test_create_and_list(client, unique_symbol):
    client.post("/api/v1/instruments", json={
        "symbol": unique_symbol, "name": "Test2", "type": "crypto",
    })
    resp = client.get("/api/v1/instruments?type=crypto")
    data = resp.json()
    symbols = [i["symbol"] for i in data["items"]]
    assert unique_symbol in symbols


def test_delete_instrument(client, unique_symbol):
    resp = client.post("/api/v1/instruments", json={
        "symbol": unique_symbol, "name": "Delete Me", "type": "stock",
    })
    inst_id = resp.json()["id"]
    del_resp = client.delete(f"/api/v1/instruments/{inst_id}")
    assert del_resp.status_code == 204
