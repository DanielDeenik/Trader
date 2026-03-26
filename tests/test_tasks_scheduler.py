"""Tests for TaskScheduler."""
import asyncio
import tempfile
import pytest
from datetime import datetime, timedelta

from social_arb.db.schema import init_db
from social_arb.db import store
from social_arb.tasks.queue import TaskQueue
from social_arb.tasks.scheduler import TaskScheduler


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    init_db(db_path)
    yield db_path
    import os
    os.unlink(db_path)


@pytest.mark.asyncio
async def test_scheduler_creates_collect_task(temp_db):
    """Test that scheduler creates a collect task on first run."""
    store.insert_instrument(
        symbol="AAPL", name="Apple Inc", type="stock",
        data_class="public", db_path=temp_db,
    )

    queue = TaskQueue(db_path=temp_db, worker_interval=0.1)
    scheduler = TaskScheduler(queue=queue, db_path=temp_db)

    # Override sleep to make it faster
    scheduler.collect_interval = 0  # Should run immediately
    scheduler.analyze_interval = 0

    await scheduler.start()
    await asyncio.sleep(2.0)
    await scheduler.stop()

    tasks = store.query_tasks(db_path=temp_db)
    collect_tasks = [t for t in tasks if t["task_type"] == "collect"]
    assert len(collect_tasks) > 0


@pytest.mark.asyncio
async def test_should_collect_first_run(temp_db):
    """Test that scheduler schedules collection on first run."""
    queue = TaskQueue(db_path=temp_db)
    scheduler = TaskScheduler(queue=queue, db_path=temp_db)

    assert scheduler._should_collect(datetime.utcnow()) is True


@pytest.mark.asyncio
async def test_should_collect_after_interval(temp_db):
    """Test that scheduler detects when interval has passed."""
    queue = TaskQueue(db_path=temp_db)
    scheduler = TaskScheduler(queue=queue, db_path=temp_db)
    scheduler.collect_interval = 3600

    past = datetime.utcnow() - timedelta(seconds=7200)
    scheduler.last_collect_at = past

    assert scheduler._should_collect(datetime.utcnow()) is True


@pytest.mark.asyncio
async def test_should_not_collect_before_interval(temp_db):
    """Test that scheduler waits if interval hasn't passed."""
    queue = TaskQueue(db_path=temp_db)
    scheduler = TaskScheduler(queue=queue, db_path=temp_db)
    scheduler.collect_interval = 3600

    recent = datetime.utcnow() - timedelta(seconds=60)
    scheduler.last_collect_at = recent

    assert scheduler._should_collect(datetime.utcnow()) is False


@pytest.mark.asyncio
async def test_should_analyze_first_run(temp_db):
    """Test that scheduler schedules analysis on first run."""
    queue = TaskQueue(db_path=temp_db)
    scheduler = TaskScheduler(queue=queue, db_path=temp_db)

    assert scheduler._should_analyze(datetime.utcnow()) is True
