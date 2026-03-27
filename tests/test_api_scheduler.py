"""Tests for scheduler API routes."""

import pytest
from unittest.mock import MagicMock, AsyncMock
from fastapi.testclient import TestClient
from social_arb.api.main import create_app


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

    # Mock scheduler if lifespan hasn't run
    if not hasattr(app.state, 'scheduler'):
        mock_scheduler = MagicMock()
        mock_scheduler.running = True
        mock_scheduler.collect_interval = 4 * 3600
        mock_scheduler.analyze_interval = 6 * 3600
        mock_scheduler.train_stepps_interval = 7 * 24 * 3600
        mock_scheduler.private_collect_interval = 24 * 3600
        mock_scheduler.enrich_sentiment_interval = 5 * 3600
        mock_scheduler.last_collect_at = None
        mock_scheduler.last_analyze_at = None
        mock_scheduler.last_train_stepps_at = None
        mock_scheduler.last_private_collect_at = None
        mock_scheduler.last_enrich_sentiment_at = None
        mock_scheduler.get_status = MagicMock(return_value={
            "running": True,
            "schedules": {
                "collect": {
                    "interval_seconds": 4 * 3600,
                    "interval_human": "4h",
                    "last_run": None,
                    "next_run": "2026-03-27T12:00:00",
                },
                "analyze": {
                    "interval_seconds": 6 * 3600,
                    "interval_human": "6h",
                    "last_run": None,
                    "next_run": "2026-03-27T12:00:00",
                },
                "train_stepps": {
                    "interval_seconds": 7 * 24 * 3600,
                    "interval_human": "7d",
                    "last_run": None,
                    "next_run": "2026-04-03T00:00:00",
                },
                "private_collect": {
                    "interval_seconds": 24 * 3600,
                    "interval_human": "1d",
                    "last_run": None,
                    "next_run": "2026-03-28T00:00:00",
                },
                "enrich_sentiment": {
                    "interval_seconds": 5 * 3600,
                    "interval_human": "5h",
                    "last_run": None,
                    "next_run": "2026-03-27T12:00:00",
                },
            },
        })
        mock_scheduler._create_collect_task = AsyncMock()
        mock_scheduler._create_analyze_task = AsyncMock()
        mock_scheduler._create_train_stepps_task = AsyncMock()
        mock_scheduler._create_private_collect_task = AsyncMock()
        mock_scheduler._create_enrich_sentiment_task = AsyncMock()
        mock_scheduler.update_interval = MagicMock()
        app.state.scheduler = mock_scheduler

    return TestClient(app)


def test_get_scheduler_status(client):
    """Test GET /api/v1/scheduler/status returns schedule info."""
    resp = client.get("/api/v1/scheduler/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "running" in data
    assert "schedules" in data
    assert "collect" in data["schedules"]
    assert "train_stepps" in data["schedules"]
    assert "enrich_sentiment" in data["schedules"]
    collect = data["schedules"]["collect"]
    assert "interval_seconds" in collect
    assert "interval_human" in collect


def test_trigger_task(client):
    """Test POST /api/v1/scheduler/trigger to manually fire a schedule."""
    resp = client.post("/api/v1/scheduler/trigger", json={
        "schedule_name": "enrich_sentiment"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["triggered"] == "enrich_sentiment"


def test_trigger_invalid_schedule(client):
    """Test POST /api/v1/scheduler/trigger with invalid name."""
    resp = client.post("/api/v1/scheduler/trigger", json={
        "schedule_name": "nonexistent"
    })
    assert resp.status_code == 400


def test_update_interval(client):
    """Test PUT /api/v1/scheduler/interval to update a schedule interval."""
    resp = client.put("/api/v1/scheduler/interval", json={
        "schedule_name": "collect",
        "interval_seconds": 7200,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["schedule_name"] == "collect"
    assert data["interval_seconds"] == 7200


def test_update_interval_invalid_name(client):
    """Test PUT /api/v1/scheduler/interval with invalid name."""
    resp = client.put("/api/v1/scheduler/interval", json={
        "schedule_name": "nonexistent",
        "interval_seconds": 3600,
    })
    assert resp.status_code == 400


def test_update_interval_too_short(client):
    """Test PUT /api/v1/scheduler/interval rejects very short intervals."""
    resp = client.put("/api/v1/scheduler/interval", json={
        "schedule_name": "collect",
        "interval_seconds": 30,
    })
    assert resp.status_code == 422 or resp.status_code == 400
