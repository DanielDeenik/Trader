# Auto-Retrain Scheduler & Scheduler API Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add scheduled sentiment enrichment after every collection cycle, a scheduler status/control API, and configurable intervals — turning the existing scheduler from a fire-and-forget loop into an observable, controllable subsystem.

**Architecture:** Extend `TaskScheduler` with: (1) post-collection sentiment enrichment scheduling (runs after each collect cycle), (2) a new `/api/v1/scheduler` route group exposing status, manual trigger, and interval config, (3) scheduler state persistence so intervals survive restarts. The existing `_should_*` / `_create_*` pattern is preserved and extended.

**Tech Stack:** Python asyncio, FastAPI, SQLite (existing stack — no new deps)

---

## File Structure

| File | Responsibility |
|------|---------------|
| `social_arb/tasks/scheduler.py` | Extend: add sentiment enrichment scheduling, configurable intervals, state export |
| `social_arb/api/routes/scheduler.py` | Create: scheduler status, trigger, config API routes |
| `social_arb/api/main.py` | Modify: register scheduler routes, pass scheduler to app.state |
| `tests/test_scheduler_sentiment.py` | Create: test sentiment enrichment scheduling |
| `tests/test_api_scheduler.py` | Create: test scheduler API routes |

---

## Task 1: Scheduled Sentiment Enrichment

**Files:**
- Modify: `social_arb/tasks/scheduler.py`
- Test: `tests/test_scheduler_sentiment.py`

- [ ] **Step 1: Write test file**

`tests/test_scheduler_sentiment.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /sessions/laughing-serene-mendel/mnt/Trader && python -m pytest tests/test_scheduler_sentiment.py -v`
Expected: FAIL — `_should_enrich_sentiment` not found

- [ ] **Step 3: Implement changes to scheduler.py**

Add to `TaskScheduler.__init__()` after existing interval attrs:

```python
        self.enrich_sentiment_interval = 5 * 3600  # 5 hours (after each collect cycle)
        self.last_enrich_sentiment_at: Optional[datetime] = None
```

Add to `_scheduler_loop()` after the private_collect block:

```python
                if self._should_enrich_sentiment(now):
                    await self._create_enrich_sentiment_task()
                    self.last_enrich_sentiment_at = now
```

Add these new methods to the class:

```python
    def _should_enrich_sentiment(self, now: datetime) -> bool:
        """Check if it's time to run sentiment enrichment."""
        if self.last_enrich_sentiment_at is None:
            return True
        return (now - self.last_enrich_sentiment_at).total_seconds() >= self.enrich_sentiment_interval

    async def _create_enrich_sentiment_task(self) -> None:
        """Create a sentiment enrichment task."""
        logger.info("Scheduler: creating sentiment enrichment task")
        try:
            await self.queue.enqueue(
                task_type="enrich_sentiment",
                params={"use_finbert": False},
                max_attempts=2,
            )
            logger.info("Scheduled sentiment enrichment task")
        except Exception as e:
            logger.error(f"Failed to create sentiment enrichment task: {e}", exc_info=True)

    def get_status(self) -> Dict[str, Any]:
        """Export scheduler status for API."""
        now = datetime.utcnow()

        def _schedule_info(name: str, interval: float, last_at: Optional[datetime]) -> Dict:
            next_at = (last_at + timedelta(seconds=interval)) if last_at else now
            return {
                "interval_seconds": interval,
                "interval_human": _format_interval(interval),
                "last_run": last_at.isoformat() if last_at else None,
                "next_run": next_at.isoformat(),
            }

        return {
            "running": self.running,
            "schedules": {
                "collect": _schedule_info("collect", self.collect_interval, self.last_collect_at),
                "analyze": _schedule_info("analyze", self.analyze_interval, self.last_analyze_at),
                "train_stepps": _schedule_info("train_stepps", self.train_stepps_interval, self.last_train_stepps_at),
                "private_collect": _schedule_info("private_collect", self.private_collect_interval, self.last_private_collect_at),
                "enrich_sentiment": _schedule_info("enrich_sentiment", self.enrich_sentiment_interval, self.last_enrich_sentiment_at),
            },
        }

    def update_interval(self, schedule_name: str, interval_seconds: int) -> None:
        """Update interval for a named schedule."""
        attr_name = f"{schedule_name}_interval"
        if not hasattr(self, attr_name):
            raise ValueError(f"Unknown schedule: {schedule_name}")
        setattr(self, attr_name, interval_seconds)
        logger.info(f"Updated {schedule_name} interval to {interval_seconds}s")
```

Also add at the top of the file, after the imports:

```python
from typing import Optional, Dict, Any
```

And add a module-level helper function before the class:

```python
def _format_interval(seconds: float) -> str:
    """Format seconds into human-readable interval."""
    if seconds >= 86400:
        return f"{seconds / 86400:.0f}d"
    elif seconds >= 3600:
        return f"{seconds / 3600:.0f}h"
    elif seconds >= 60:
        return f"{seconds / 60:.0f}m"
    return f"{seconds:.0f}s"
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_scheduler_sentiment.py -v`
Expected: All pass

- [ ] **Step 5: Commit**

```bash
git add social_arb/tasks/scheduler.py tests/test_scheduler_sentiment.py
git commit -m "feat: add scheduled sentiment enrichment and scheduler status/config methods"
```

---

## Task 2: Scheduler API Routes

**Files:**
- Create: `social_arb/api/routes/scheduler.py`
- Modify: `social_arb/api/main.py`
- Test: `tests/test_api_scheduler.py`

- [ ] **Step 1: Write test file**

`tests/test_api_scheduler.py`:

```python
"""Tests for scheduler API routes."""

import pytest
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
    # Each schedule has interval info
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_api_scheduler.py -v`
Expected: FAIL — routes not found (404)

- [ ] **Step 3: Create scheduler routes**

`social_arb/api/routes/scheduler.py`:

```python
"""Scheduler status and control API routes."""

import logging
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/scheduler", tags=["scheduler"])

# Valid schedule names that can be triggered or configured
VALID_SCHEDULES = {
    "collect", "analyze", "train_stepps", "private_collect", "enrich_sentiment",
}

# Manual trigger dispatchers — maps schedule name to the scheduler method that creates its task
TRIGGER_METHODS = {
    "collect": "_create_collect_task",
    "analyze": "_create_analyze_task",
    "train_stepps": "_create_train_stepps_task",
    "private_collect": "_create_private_collect_task",
    "enrich_sentiment": "_create_enrich_sentiment_task",
}


class TriggerRequest(BaseModel):
    schedule_name: str


class IntervalUpdateRequest(BaseModel):
    schedule_name: str
    interval_seconds: int = Field(ge=60, description="Minimum 60 seconds")


@router.get("/status")
async def get_scheduler_status(request: Request):
    """Get current scheduler status and schedule configuration."""
    scheduler = request.app.state.scheduler
    return scheduler.get_status()


@router.post("/trigger")
async def trigger_schedule(req: TriggerRequest, request: Request):
    """Manually trigger a scheduled task immediately."""
    if req.schedule_name not in VALID_SCHEDULES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid schedule: {req.schedule_name}. Valid: {sorted(VALID_SCHEDULES)}",
        )

    scheduler = request.app.state.scheduler
    method_name = TRIGGER_METHODS[req.schedule_name]

    try:
        method = getattr(scheduler, method_name)
        await method()
        logger.info(f"Manually triggered schedule: {req.schedule_name}")
        return {"triggered": req.schedule_name, "status": "enqueued"}
    except Exception as e:
        logger.error(f"Failed to trigger {req.schedule_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/interval")
async def update_interval(req: IntervalUpdateRequest, request: Request):
    """Update the interval for a scheduled task."""
    if req.schedule_name not in VALID_SCHEDULES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid schedule: {req.schedule_name}. Valid: {sorted(VALID_SCHEDULES)}",
        )

    scheduler = request.app.state.scheduler
    try:
        scheduler.update_interval(req.schedule_name, req.interval_seconds)
        return {
            "schedule_name": req.schedule_name,
            "interval_seconds": req.interval_seconds,
            "status": "updated",
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
```

- [ ] **Step 4: Register routes in main.py**

In `social_arb/api/main.py`:

Add `scheduler` to the routes import:
```python
from social_arb.api.routes import (
    health, instruments, signals, reviews, analysis, mosaics, theses, positions, tasks, stepps, sentiment, scheduler,
)
```

Add router registration after `app.include_router(sentiment.router)`:
```python
    app.include_router(scheduler.router)
```

- [ ] **Step 5: Run tests**

Run: `python -m pytest tests/test_api_scheduler.py -v`
Expected: All pass

- [ ] **Step 6: Run full test suite**

Run: `python -m pytest tests/test_scheduler_sentiment.py tests/test_api_scheduler.py tests/test_tasks_scheduler.py tests/test_api_sentiment.py -v`
Expected: All pass — no regressions

- [ ] **Step 7: Commit**

```bash
git add social_arb/api/routes/scheduler.py social_arb/api/main.py tests/test_api_scheduler.py
git commit -m "feat: add scheduler status/trigger/config API routes"
```

---

## Summary

| Task | File(s) | Type |
|------|---------|------|
| 1. Scheduled Sentiment Enrichment | `scheduler.py` | Modify |
| 2. Scheduler API Routes | `scheduler.py`, `main.py` | Create + Modify |

## Architecture Notes

- **Sentiment enrichment runs every 5 hours** (just after the 4-hour collect cycle, so new signals get scored)
- **STEPPS retraining stays at 7 days** (already in place, untouched)
- **Scheduler status** is exported as a dict — all schedule names, intervals, last/next run times
- **Manual trigger** lets the user fire any schedule on demand via POST `/api/v1/scheduler/trigger`
- **Interval config** lets the user tune intervals via PUT `/api/v1/scheduler/interval` (minimum 60s)
- **No new DB tables** — scheduler state is in-memory (resets on restart, first cycle runs immediately on startup by design)
- **Follows existing patterns**: `_should_*` / `_create_*` methods, same scheduler loop structure

---

**Generated:** 2026-03-27
**Status:** Ready to implement
