"""Tests for instruments CRUD API."""
import pytest
from fastapi.testclient import TestClient
from social_arb.api.main import create_app


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


def test_list_instruments_empty(client):
    resp = client.get("/api/v1/instruments")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_create_instrument(client):
    resp = client.post("/api/v1/instruments", json={
        "symbol": "TEST", "name": "Test Corp", "type": "stock",
    })
    assert resp.status_code == 201
    assert resp.json()["symbol"] == "TEST"


def test_create_and_list(client):
    client.post("/api/v1/instruments", json={
        "symbol": "TEST2", "name": "Test2", "type": "crypto",
    })
    resp = client.get("/api/v1/instruments?type=crypto")
    data = resp.json()
    symbols = [i["symbol"] for i in data]
    assert "TEST2" in symbols


def test_delete_instrument(client):
    resp = client.post("/api/v1/instruments", json={
        "symbol": "DEL", "name": "Delete Me", "type": "stock",
    })
    inst_id = resp.json()["id"]
    del_resp = client.delete(f"/api/v1/instruments/{inst_id}")
    assert del_resp.status_code == 204
