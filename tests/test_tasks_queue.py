"""Tests for TaskQueue class."""
import asyncio
import json
import tempfile
import pytest
from datetime import datetime

from social_arb.db.schema import init_db
from social_arb.db import store
from social_arb.tasks.queue import TaskQueue


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
def queue(temp_db):
    """Create a TaskQueue instance."""
    return TaskQueue(db_path=temp_db, worker_interval=0.1)


@pytest.mark.asyncio
async def test_enqueue_task(queue, temp_db):
    """Test enqueueing a task."""
    task_id = await queue.enqueue(
        task_type="collect",
        params={"sources": ["yfinance"], "symbols": ["AAPL"]},
    )
    assert task_id > 0

    tasks = store.query_tasks_by_status(status="pending", db_path=temp_db)
    assert len(tasks) == 1
    assert tasks[0]["id"] == task_id


@pytest.mark.asyncio
async def test_register_and_execute_handler(queue, temp_db):
    """Test registering and executing a handler."""
    executed = []

    async def mock_collect_handler(params):
        executed.append(params)
        return {"signal_count": 42}

    queue.register_handler("collect", mock_collect_handler)

    params = {"sources": ["yfinance"]}
    task_id = await queue.enqueue(task_type="collect", params=params)

    await queue.start()
    await asyncio.sleep(0.5)
    await queue.stop()

    assert len(executed) == 1
    assert executed[0] == params

    tasks = store.query_tasks(db_path=temp_db)
    task = next(t for t in tasks if t["id"] == task_id)
    assert task["status"] == "completed"
    result = json.loads(task["result_json"])
    assert result["signal_count"] == 42


@pytest.mark.asyncio
async def test_handler_failure_and_retry(queue, temp_db):
    """Test task failure and exponential backoff."""
    async def failing_handler(params):
        raise ValueError("Simulated failure")

    queue.register_handler("analyze", failing_handler)

    task_id = await queue.enqueue(task_type="analyze", params={}, max_attempts=2)

    await queue.start()
    await asyncio.sleep(0.5)
    await queue.stop()

    tasks = store.query_tasks(db_path=temp_db)
    task = next(t for t in tasks if t["id"] == task_id)
    assert task["status"] == "pending"
    assert task["attempts"] == 1
    assert task["next_retry_at"] is not None
    assert "Simulated failure" in task["error"]


@pytest.mark.asyncio
async def test_max_attempts_exhausted(queue, temp_db):
    """Test that task fails permanently after max attempts."""
    async def failing_handler(params):
        raise ValueError("Permanent failure")

    queue.register_handler("backfill", failing_handler)

    task_id = await queue.enqueue(task_type="backfill", params={}, max_attempts=1)

    await queue.start()
    await asyncio.sleep(0.5)
    await queue.stop()

    tasks = store.query_tasks(db_path=temp_db)
    task = next(t for t in tasks if t["id"] == task_id)
    assert task["status"] == "failed"
    assert task["attempts"] == 1


@pytest.mark.asyncio
async def test_concurrent_limit(queue, temp_db):
    """Test that max_concurrent limit is respected."""
    running_count = 0
    max_running = 0
    lock = asyncio.Lock()

    async def slow_handler(params):
        nonlocal running_count, max_running
        async with lock:
            running_count += 1
            max_running = max(max_running, running_count)
        await asyncio.sleep(0.2)
        async with lock:
            running_count -= 1
        return {}

    queue = TaskQueue(db_path=temp_db, worker_interval=0.05, max_concurrent=2)
    queue.register_handler("collect", slow_handler)

    for _ in range(5):
        await queue.enqueue(task_type="collect", params={})

    await queue.start()
    await asyncio.sleep(2.0)
    await queue.stop()

    assert max_running <= 2
