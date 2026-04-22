"""Tests for sentiment API routes."""

import pytest
from fastapi.testclient import TestClient
from social_arb.api.main import create_app
from social_arb.db.schema import init_db


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
    app = create_app()
    return TestClient(app)


def test_score_text_endpoint(client):
    """Test on-demand text scoring."""
    resp = client.post("/api/v1/sentiment/score", json={
        "text": "Amazing earnings growth, revenue smashing expectations"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "compound" in data
    assert "direction" in data
    assert data["direction"] in ("bullish", "bearish", "neutral")


def test_score_empty_text(client):
    resp = client.post("/api/v1/sentiment/score", json={"text": ""})
    assert resp.status_code == 200
    data = resp.json()
    assert data["direction"] == "neutral"


def test_score_batch_endpoint(client):
    resp = client.post("/api/v1/sentiment/score-batch", json={
        "texts": [
            "Great earnings beat",
            "Massive layoffs announced",
            "Filed quarterly report",
        ]
    })
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["results"]) == 3
