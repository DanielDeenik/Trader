"""Tests for reviews API."""

import pytest
from fastapi.testclient import TestClient
from social_arb.api.main import create_app


@pytest.fixture
def client():
    """Create test client."""
    app = create_app()
    return TestClient(app)


def test_list_reviews_empty(client):
    """Test listing reviews when empty."""
    resp = client.get("/api/v1/reviews")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_submit_review(client):
    """Test submitting a review."""
    resp = client.post(
        "/api/v1/reviews",
        json={
            "gate": "L1_triage",
            "symbol": "NVDA",
            "entity_id": 1,
            "entity_type": "signal_cluster",
            "scores": {
                "signal_quality": 4,
                "source_diversity": 3,
                "divergence_magnitude": 5,
                "timeliness": 4,
            },
            "decision": "promote",
            "dominant_narrative": "Strong Reddit buzz",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["decision"] == "promote"
    assert data["symbol"] == "NVDA"
    assert data["total_score"] == 16


def test_submit_review_watch(client):
    """Test submitting a watch review."""
    resp = client.post(
        "/api/v1/reviews",
        json={
            "gate": "L1_triage",
            "symbol": "TEST",
            "entity_id": 2,
            "entity_type": "signal_cluster",
            "scores": {
                "signal_quality": 3,
                "source_diversity": 3,
                "divergence_magnitude": 3,
                "timeliness": 3,
            },
            "decision": "watch",
        },
    )
    assert resp.status_code == 201
    assert resp.json()["decision"] == "watch"


def test_list_reviews_after_submit(client):
    """Test listing reviews after submission."""
    client.post(
        "/api/v1/reviews",
        json={
            "gate": "L1_triage",
            "symbol": "TEST",
            "entity_id": 1,
            "entity_type": "signal_cluster",
            "scores": {
                "signal_quality": 3,
                "source_diversity": 3,
                "divergence_magnitude": 3,
                "timeliness": 3,
            },
            "decision": "watch",
        },
    )
    resp = client.get("/api/v1/reviews?gate=L1_triage")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


def test_list_reviews_filtered_by_symbol(client):
    """Test listing reviews filtered by symbol."""
    client.post(
        "/api/v1/reviews",
        json={
            "gate": "L1_triage",
            "symbol": "AAPL",
            "entity_id": 1,
            "entity_type": "signal_cluster",
            "scores": {
                "signal_quality": 4,
                "source_diversity": 4,
                "divergence_magnitude": 4,
                "timeliness": 4,
            },
            "decision": "promote",
        },
    )
    resp = client.get("/api/v1/reviews?symbol=AAPL")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
