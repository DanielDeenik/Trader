"""Tests for scheduled sentiment enrichment."""

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
async def test_should_enrich_sentiment_first_run(temp_db):
    """Sentiment enrichment should run on first scheduler cycle."""
    queue = TaskQueue(db_path=temp_db)
    scheduler = TaskScheduler(queue=queue, db_path=temp_db)
    assert scheduler._should_enrich_sentiment(datetime.utcnow()) is True


@pytest.mark.asyncio
async def test_should_not_enrich_sentiment_before_interval(temp_db):
    """Sentiment enrichment should wait for interval to pass."""
    queue = TaskQueue(db_path=temp_db)
    scheduler = TaskScheduler(queue=queue, db_path=temp_db)
    scheduler.enrich_sentiment_interval = 3600
    recent = datetime.utcnow() - timedelta(seconds=60)
    scheduler.last_enrich_sentiment_at = recent
    assert scheduler._should_enrich_sentiment(datetime.utcnow()) is False


@pytest.mark.asyncio
async def test_should_enrich_sentiment_after_interval(temp_db):
    """Sentiment enrichment should run after interval passes."""
    queue = TaskQueue(db_path=temp_db)
    scheduler = TaskScheduler(queue=queue, db_path=temp_db)
    scheduler.enrich_sentiment_interval = 3600
    past = datetime.utcnow() - timedelta(seconds=7200)
    scheduler.last_enrich_sentiment_at = past
    assert scheduler._should_enrich_sentiment(datetime.utcnow()) is True


@pytest.mark.asyncio
async def test_create_enrich_sentiment_task(temp_db):
    """Test that sentiment enrichment task gets enqueued."""
    queue = TaskQueue(db_path=temp_db)
    scheduler = TaskScheduler(queue=queue, db_path=temp_db)
    await scheduler._create_enrich_sentiment_task()
    tasks = store.query_tasks(db_path=temp_db)
    enrich_tasks = [t for t in tasks if t["task_type"] == "enrich_sentiment"]
    assert len(enrich_tasks) == 1


@pytest.mark.asyncio
async def test_get_status(temp_db):
    """Test scheduler status export."""
    queue = TaskQueue(db_path=temp_db)
    scheduler = TaskScheduler(queue=queue, db_path=temp_db)
    status = scheduler.get_status()
    assert "running" in status
    assert "schedules" in status
    assert "enrich_sentiment" in status["schedules"]
    assert "collect" in status["schedules"]
    assert "train_stepps" in status["schedules"]


@pytest.mark.asyncio
async def test_update_interval(temp_db):
    """Test updating a schedule interval."""
    queue = TaskQueue(db_path=temp_db)
    scheduler = TaskScheduler(queue=queue, db_path=temp_db)
    old_interval = scheduler.collect_interval
    scheduler.update_interval("collect", 7200)
    assert scheduler.collect_interval == 7200
    assert scheduler.collect_interval != old_interval


@pytest.mark.asyncio
async def test_update_interval_invalid_name(temp_db):
    """Test that updating a non-existent schedule raises ValueError."""
    queue = TaskQueue(db_path=temp_db)
    scheduler = TaskScheduler(queue=queue, db_path=temp_db)
    with pytest.raises(ValueError):
        scheduler.update_interval("nonexistent", 3600)
