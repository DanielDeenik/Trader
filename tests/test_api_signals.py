"""Tests for signals API."""
import pytest
from fastapi.testclient import TestClient
from social_arb.api.main import create_app


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


def test_list_signals(client):
    resp = client.get("/api/v1/signals")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_list_signals_filter_symbol(client):
    resp = client.get("/api/v1/signals?symbol=NVDA")
    assert resp.status_code == 200


def test_signals_grouped(client):
    resp = client.get("/api/v1/signals/grouped")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
