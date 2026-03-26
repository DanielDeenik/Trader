"""E2E tests for tasks API."""
import json
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient

from social_arb.api.main import create_app
from social_arb.db import store
from social_arb.api.deps import get_db_path


@pytest.fixture
def client():
    """Create a FastAPI test client with mocked queue."""
    app = create_app()
    # Mock queue in app.state for POST endpoint
    mock_queue = MagicMock()
    mock_queue.enqueue = AsyncMock(return_value=1)
    app.state.queue = mock_queue
    return TestClient(app)


def test_get_tasks_list(client):
    """Test listing tasks via GET /api/v1/tasks."""
    db_path = get_db_path()
    store.insert_task(
        task_type="collect",
        params_json=json.dumps({"sources": ["yfinance"]}),
        db_path=db_path,
    )

    response = client.get("/api/v1/tasks")
    assert response.status_code == 200
    data = response.json()
    assert "tasks" in data
    assert data["total_count"] >= 1
    tasks = data["tasks"]
    collect_tasks = [t for t in tasks if t["task_type"] == "collect"]
    assert len(collect_tasks) >= 1


def test_get_tasks_with_status_filter(client):
    """Test filtering tasks by status."""
    db_path = get_db_path()
    store.insert_task(
        task_type="collect",
        params_json=json.dumps({}),
        db_path=db_path,
    )
    store.claim_task(db_path=db_path)

    response = client.get("/api/v1/tasks?status=running")
    assert response.status_code == 200
    data = response.json()
    running_tasks = [t for t in data["tasks"] if t["status"] == "running"]
    assert len(running_tasks) >= 1


def test_get_task_by_id(client):
    """Test getting a specific task."""
    db_path = get_db_path()
    task_id = store.insert_task(
        task_type="analyze",
        params_json=json.dumps({"symbols": ["AAPL"]}),
        db_path=db_path,
    )

    response = client.get(f"/api/v1/tasks/{task_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == task_id
    assert data["task_type"] == "analyze"


def test_get_nonexistent_task(client):
    """Test getting a nonexistent task returns 404."""
    response = client.get("/api/v1/tasks/999999")
    assert response.status_code == 404


def test_post_task_enqueue(client):
    """Test enqueueing a task via POST /api/v1/tasks."""
    response = client.post(
        "/api/v1/tasks",
        json={
            "task_type": "collect",
            "params": {"sources": ["yfinance"], "symbols": ["AAPL"]},
            "max_attempts": 3,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert "task_id" in data
    assert data["status"] == "pending"


def test_delete_pending_task(client):
    """Test cancelling a pending task."""
    db_path = get_db_path()
    task_id = store.insert_task(
        task_type="backfill",
        params_json=json.dumps({}),
        db_path=db_path,
    )

    response = client.delete(f"/api/v1/tasks/{task_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "cancelled"


def test_delete_running_task_fails(client):
    """Test that cancelling a running task fails."""
    db_path = get_db_path()
    task_id = store.insert_task(
        task_type="collect",
        params_json=json.dumps({}),
        db_path=db_path,
    )
    # Directly update status to running to avoid claim_task claiming earlier pending tasks
    from social_arb.db.schema import get_connection
    with get_connection(db_path) as conn:
        conn.execute("UPDATE tasks SET status = 'running' WHERE id = ?", (task_id,))
        conn.commit()

    response = client.delete(f"/api/v1/tasks/{task_id}")
    assert response.status_code == 400


def test_get_source_health(client):
    """Test getting source health metrics."""
    db_path = get_db_path()
    store.insert_signal(
        timestamp="2026-03-26T10:00:00Z",
        symbol="AAPL", source="yfinance",
        direction="bullish", strength=0.8, confidence=0.9,
        signal_type="price", raw_json="{}", data_class="public",
        db_path=db_path,
    )
    store.insert_signal(
        timestamp="2026-03-26T10:01:00Z",
        symbol="TSLA", source="reddit",
        direction="neutral", strength=0.5, confidence=0.7,
        signal_type="sentiment", raw_json="{}", data_class="public",
        db_path=db_path,
    )

    response = client.get("/api/v1/source-health")
    assert response.status_code == 200
    data = response.json()
    assert "sources" in data
    assert "as_of" in data
    assert data["total_sources"] >= 2


def test_get_source_health_with_hours(client):
    """Test source health with custom time window."""
    response = client.get("/api/v1/source-health?hours=12")
    assert response.status_code == 200
    data = response.json()
    assert "sources" in data
    assert "as_of" in data
