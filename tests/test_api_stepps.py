"""Tests for STEPPS API routes."""
import json
import tempfile
import pytest
from fastapi.testclient import TestClient
from social_arb.db.schema import init_db, DEFAULT_DB_PATH
from social_arb.db import store
from social_arb.api.main import app
from social_arb.api.routes import stepps
from social_arb.engine.stepps_classifier import SteppsClassifier


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    init_db(db_path)
    yield db_path
    import os
    os.unlink(db_path)


@pytest.fixture
def client(temp_db):
    """Create test client with dependency override."""
    # Override the get_classifier dependency
    def get_classifier_override() -> SteppsClassifier:
        return SteppsClassifier(db_path=temp_db)

    app.dependency_overrides[stepps.get_classifier] = get_classifier_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


def test_post_score_not_found(client):
    """Test scoring a non-existent signal."""
    response = client.post("/api/v1/stepps/score?signal_id=999")
    assert response.status_code == 404


def test_get_scores_empty(client):
    """Test getting scores when none exist."""
    response = client.get("/api/v1/stepps/scores")
    assert response.status_code == 200
    assert response.json() == []


def test_post_correction(client, temp_db):
    """Test submitting a HITL correction."""
    # Create signal first
    signal_id = store.insert_signal(
        timestamp="2026-03-26T10:00:00Z",
        symbol="AAPL",
        source="reddit",
        direction="bullish",
        strength=0.75,
        confidence=0.8,
        signal_type="general",
        raw_json=json.dumps({"text": "bullish"}),
        data_class="public",
        db_path=temp_db,
    )

    payload = {
        "signal_id": signal_id,
        "social_currency": 0.8,
        "triggers": 0.7,
        "emotion": 0.9,
        "public_visibility": 0.6,
        "practical_value": 0.5,
        "stories": 0.85,
    }

    response = client.post("/api/v1/stepps/correct", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data.get("success") is True


def test_post_train(client):
    """Test triggering retraining."""
    response = client.post("/api/v1/stepps/train")
    assert response.status_code == 200
    data = response.json()
    assert "success" in data
