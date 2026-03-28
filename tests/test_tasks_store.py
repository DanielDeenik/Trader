"""Tests for task store functions."""
import json
import tempfile
import pytest
from social_arb.db.schema import init_db, DEFAULT_DB_PATH
from social_arb.db import store


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    init_db(db_path)
    yield db_path
    import os
    os.unlink(db_path)


def test_insert_task_pending(temp_db):
    """Test inserting a new task."""
    task_id = store.insert_task(
        task_type="collect",
        params_json=json.dumps({"sources": ["yfinance"], "symbols": ["AAPL"]}),
        db_path=temp_db,
    )
    assert task_id > 0


def test_query_tasks_by_status(temp_db):
    """Test querying tasks by status."""
    store.insert_task(
        task_type="collect",
        params_json=json.dumps({"sources": ["yfinance"]}),
        db_path=temp_db,
    )
    tasks = store.query_tasks_by_status(status="pending", db_path=temp_db)
    assert len(tasks) == 1
    assert tasks[0]["status"] == "pending"
    assert tasks[0]["task_type"] == "collect"


def test_claim_task_atomic(temp_db):
    """Test claiming a task (atomically mark as running)."""
    tid1 = store.insert_task(
        task_type="collect",
        params_json=json.dumps({"sources": ["yfinance"]}),
        db_path=temp_db,
    )
    tid2 = store.insert_task(
        task_type="analyze",
        params_json=json.dumps({}),
        db_path=temp_db,
    )

    # Claim first pending task
    claimed = store.claim_task(db_path=temp_db)
    assert claimed is not None
    assert claimed["id"] == tid1
    assert claimed["status"] == "running"

    # Verify DB shows it as running
    all_tasks = store.query_tasks(db_path=temp_db)
    running_tasks = [t for t in all_tasks if t["status"] == "running"]
    assert len(running_tasks) == 1


def test_update_task_started_at(temp_db):
    """Test updating started_at timestamp."""
    task_id = store.insert_task(
        task_type="collect",
        params_json=json.dumps({}),
        db_path=temp_db,
    )
    from datetime import datetime
    now = datetime.utcnow().isoformat()
    store.update_task_started_at(task_id=task_id, started_at=now, db_path=temp_db)

    tasks = store.query_tasks(db_path=temp_db)
    task = next(t for t in tasks if t["id"] == task_id)
    assert task["started_at"] == now


def test_complete_task_with_result(temp_db):
    """Test completing a task with result_json."""
    task_id = store.insert_task(
        task_type="collect",
        params_json=json.dumps({}),
        db_path=temp_db,
    )
    result = {"signal_count": 42, "errors": []}
    store.complete_task(
        task_id=task_id,
        result_json=json.dumps(result),
        db_path=temp_db,
    )

    tasks = store.query_tasks(db_path=temp_db)
    task = next(t for t in tasks if t["id"] == task_id)
    assert task["status"] == "completed"
    assert json.loads(task["result_json"]) == result


def test_fail_task_with_retry(temp_db):
    """Test failing a task and incrementing attempts."""
    task_id = store.insert_task(
        task_type="collect",
        params_json=json.dumps({}),
        max_attempts=3,
        db_path=temp_db,
    )

    error_msg = "Connection timeout"
    store.fail_task(
        task_id=task_id,
        error=error_msg,
        next_retry_at="2026-03-26T12:00:00Z",
        db_path=temp_db,
    )

    tasks = store.query_tasks(db_path=temp_db)
    task = next(t for t in tasks if t["id"] == task_id)
    assert task["status"] == "pending"  # Not failed yet, has retries left
    assert task["error"] == error_msg
    assert task["attempts"] == 1
    assert task["next_retry_at"] == "2026-03-26T12:00:00Z"


def test_fail_task_exhausted(temp_db):
    """Test that task is marked as failed when max_attempts exhausted."""
    task_id = store.insert_task(
        task_type="collect",
        params_json=json.dumps({}),
        max_attempts=1,
        db_path=temp_db,
    )

    store.fail_task(
        task_id=task_id,
        error="Permanent failure",
        db_path=temp_db,
    )

    tasks = store.query_tasks(db_path=temp_db)
    task = next(t for t in tasks if t["id"] == task_id)
    assert task["status"] == "failed"
    assert task["attempts"] == 1


def test_query_source_health(temp_db):
    """Test querying per-source health based on recent task outcomes."""
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    store.insert_signal(
        timestamp=now,
        symbol="AAPL",
        source="yfinance",
        direction="bullish",
        strength=0.8,
        confidence=0.9,
        signal_type="price",
        raw_json="{}",
        data_class="public",
        db_path=temp_db,
    )
    store.insert_signal(
        timestamp=now,
        symbol="AAPL",
        source="reddit",
        direction="neutral",
        strength=0.5,
        confidence=0.7,
        signal_type="sentiment",
        raw_json="{}",
        data_class="public",
        db_path=temp_db,
    )

    health = store.query_source_health(db_path=temp_db)
    assert len(health) == 2
    assert any(h["source"] == "yfinance" for h in health)
    assert any(h["source"] == "reddit" for h in health)
