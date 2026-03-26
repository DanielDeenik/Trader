# Phase 3: Task Queue + Collector Resilience

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an in-process asyncio task queue with DB-backed persistence to coordinate data collection, analysis, and backfill jobs. Enable per-source health tracking and exponential backoff retry logic. Support scheduled collection every N hours.

**Architecture:** A task queue module at `social_arb/tasks/` manages job lifecycle (pending → running → completed/failed). Tasks persist to a new `tasks` table in the DB. An asyncio background worker loop in FastAPI's lifespan runs pending tasks, applies retry logic on failure, and tracks per-source health. A scheduler creates collection tasks on intervals. API routes expose task status and source health.

**Tech Stack:** asyncio (built-in), existing DB layer, SQLite/PostgreSQL adapter, Pydantic for schemas, FastAPI lifespan integration.

---

## File Structure

```
social_arb/
├── tasks/                          # NEW: Task queue module
│   ├── __init__.py
│   ├── queue.py                    # TaskQueue class + worker loop
│   ├── workers.py                  # Job handlers: collect, analyze, backfill
│   └── scheduler.py                # TaskScheduler + interval-based task creation
├── db/
│   ├── schema.py                   # MODIFIED: Add tasks table (Tier 5: META)
│   └── store.py                    # MODIFIED: Task CRUD functions
└── api/
    ├── main.py                     # MODIFIED: Integrate worker in lifespan
    ├── schemas.py                  # MODIFIED: Add TaskCreate, TaskResponse schemas
    └── routes/
        └── tasks.py                # NEW: GET/POST/DELETE /api/v1/tasks, GET /api/v1/source-health

tests/
├── test_tasks_store.py             # Task CRUD tests
├── test_tasks_queue.py             # TaskQueue worker tests
├── test_tasks_workers.py           # Worker handler tests
└── test_api_tasks.py               # API route E2E tests
```

**Modified existing files:**
- `social_arb/db/schema.py` — Add `tasks` table with status, retry logic, result tracking
- `social_arb/db/store.py` — Add `insert_task()`, `query_tasks()`, `claim_task()`, `complete_task()`, `fail_task()`, `query_source_health()`, `update_task_started_at()`, `query_tasks_by_status()`
- `social_arb/api/main.py` — Start TaskQueue worker in lifespan startup
- `social_arb/api/schemas.py` — Add Pydantic models for task requests/responses
- `pyproject.toml` — No new deps (asyncio + sqlite3 are stdlib, fastapi already included)

---

### Task 1: Add tasks table to schema + Task CRUD in store.py

**Files:**
- Modify: `social_arb/db/schema.py:200-215` (insert tasks table in META tier after scans)
- Modify: `social_arb/db/store.py` (append task CRUD functions at end)
- Create: `tests/test_tasks_store.py`

#### Step 1: Add tasks table to schema.py (both SQLite + PostgreSQL)

In `social_arb/db/schema.py`, find the `_init_db_sqlite` function around line 200 (after `scans` table). Add the `tasks` table before the INDEXES block:

```python
# In _init_db_sqlite, after scans table (line 215), add:

    c.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_type TEXT NOT NULL,
            status TEXT CHECK(status IN ('pending','running','completed','failed','cancelled')) DEFAULT 'pending',
            params_json TEXT,
            result_json TEXT,
            error TEXT,
            attempts INTEGER DEFAULT 0,
            max_attempts INTEGER DEFAULT 3,
            next_retry_at TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            started_at TEXT,
            completed_at TEXT
        )
    """)
```

In `_init_db_postgres`, after scans table (around line 256), add the same DDL but with PostgreSQL types:

```python
# In _init_db_postgres, after scans table, add:

    c.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id SERIAL PRIMARY KEY,
            task_type TEXT NOT NULL,
            status TEXT CHECK(status IN ('pending','running','completed','failed','cancelled')) DEFAULT 'pending',
            params_json TEXT,
            result_json TEXT,
            error TEXT,
            attempts INTEGER DEFAULT 0,
            max_attempts INTEGER DEFAULT 3,
            next_retry_at TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            started_at TIMESTAMP WITH TIME ZONE,
            completed_at TIMESTAMP WITH TIME ZONE
        )
    """)
```

Also add an index in both backends. In the INDEXES list (around line 217 for SQLite, line 425 for PG), add:

```python
        "CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)",
        "CREATE INDEX IF NOT EXISTS idx_tasks_status_created ON tasks(status, created_at)",
        "CREATE INDEX IF NOT EXISTS idx_tasks_next_retry ON tasks(next_retry_at)",
```

- [ ] **Step 2: Write task_store tests first (TDD)**

Create `tests/test_tasks_store.py`:

```python
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
    assert task["status"] == "failed"
    assert task["error"] == error_msg
    assert task["attempts"] == 1
    assert task["next_retry_at"] == "2026-03-26T12:00:00Z"


def test_query_source_health(temp_db):
    """Test querying per-source health based on recent task outcomes."""
    # Insert some signals from different sources
    store.insert_signal(
        timestamp="2026-03-26T10:00:00Z",
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
        timestamp="2026-03-26T10:01:00Z",
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
```

- [ ] **Step 3: Implement task CRUD functions in store.py**

At the end of `social_arb/db/store.py` (after all existing functions), add:

```python
# TIER 5: TASKS (META)


def insert_task(
    *,
    task_type: str,
    params_json: str,
    max_attempts: int = 3,
    db_path: str = DEFAULT_DB_PATH,
) -> int:
    """Insert a new task with 'pending' status. Returns task id."""
    with get_connection(db_path) as conn:
        ph = _make_placeholders(4)
        cursor = conn.execute(
            f"""
            INSERT INTO tasks
            (task_type, status, params_json, max_attempts)
            VALUES ({ph})
            """,
            (task_type, "pending", params_json, max_attempts),
        )
        return cursor.lastrowid


def query_tasks(
    *,
    limit: int = 100,
    db_path: str = DEFAULT_DB_PATH,
) -> List[Dict]:
    """Query all tasks, most recent first. Returns list of dicts."""
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """
            SELECT * FROM tasks
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,),
        )
        return [dict(row) for row in cursor.fetchall()]


def query_tasks_by_status(
    *,
    status: str,
    limit: int = 100,
    db_path: str = DEFAULT_DB_PATH,
) -> List[Dict]:
    """Query tasks by status. Returns list of dicts ordered by created_at."""
    with get_connection(db_path) as conn:
        ph = get_placeholder()
        cursor = conn.execute(
            f"""
            SELECT * FROM tasks
            WHERE status = {ph}
            ORDER BY created_at ASC
            LIMIT ?
            """,
            (status, limit),
        )
        return [dict(row) for row in cursor.fetchall()]


def claim_task(
    *,
    db_path: str = DEFAULT_DB_PATH,
) -> Optional[Dict]:
    """
    Atomically claim the next pending task.
    Updates it to 'running' status and returns the task dict.
    Returns None if no pending tasks exist.
    """
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """
            SELECT id FROM tasks
            WHERE status = 'pending' AND (next_retry_at IS NULL OR next_retry_at <= datetime('now'))
            ORDER BY created_at ASC
            LIMIT 1
            """
        )
        row = cursor.fetchone()
        if not row:
            return None

        task_id = row[0]
        cursor.execute(
            """
            UPDATE tasks
            SET status = 'running'
            WHERE id = ?
            """,
            (task_id,),
        )
        conn.commit()

        # Fetch and return the updated task
        cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        return dict(cursor.fetchone())


def update_task_started_at(
    *,
    task_id: int,
    started_at: str,
    db_path: str = DEFAULT_DB_PATH,
) -> None:
    """Update the started_at timestamp for a task."""
    with get_connection(db_path) as conn:
        ph = get_placeholder()
        conn.execute(
            f"""
            UPDATE tasks
            SET started_at = {ph}
            WHERE id = {ph}
            """,
            (started_at, task_id),
        )
        conn.commit()


def complete_task(
    *,
    task_id: int,
    result_json: str,
    db_path: str = DEFAULT_DB_PATH,
) -> None:
    """Mark task as completed with result."""
    with get_connection(db_path) as conn:
        now = datetime.utcnow().isoformat()
        ph = _make_placeholders(3)
        conn.execute(
            f"""
            UPDATE tasks
            SET status = 'completed', result_json = {ph.split(",")[0]}, completed_at = {ph.split(",")[1]}
            WHERE id = {ph.split(",")[2]}
            """,
            (result_json, now, task_id),
        )
        conn.commit()


def fail_task(
    *,
    task_id: int,
    error: str,
    next_retry_at: Optional[str] = None,
    db_path: str = DEFAULT_DB_PATH,
) -> None:
    """Mark task as failed, increment attempts, set next_retry_at."""
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        # Get current attempts
        cursor.execute("SELECT attempts, max_attempts FROM tasks WHERE id = ?", (task_id,))
        row = cursor.fetchone()
        if not row:
            return

        current_attempts = (row[0] or 0) + 1
        max_attempts = row[1] or 3

        # If exhausted, mark as failed; otherwise keep as 'pending' for retry
        new_status = "failed" if current_attempts >= max_attempts else "pending"

        ph = _make_placeholders(4)
        cursor.execute(
            f"""
            UPDATE tasks
            SET status = {ph.split(",")[0]}, error = {ph.split(",")[1]}, attempts = {ph.split(",")[2]}, next_retry_at = {ph.split(",")[3]}
            WHERE id = ?
            """,
            (new_status, error, current_attempts, next_retry_at, task_id),
        )
        conn.commit()


def query_source_health(
    *,
    hours: int = 24,
    db_path: str = DEFAULT_DB_PATH,
) -> List[Dict]:
    """
    Query per-source health based on recent signals.
    Returns list of dicts with: source, signal_count, avg_confidence, last_timestamp, status.
    """
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            f"""
            SELECT
                source,
                COUNT(*) as signal_count,
                ROUND(AVG(confidence), 2) as avg_confidence,
                MAX(timestamp) as last_timestamp,
                CASE
                    WHEN COUNT(*) > 0 AND ROUND(AVG(confidence), 2) > 0.7 THEN 'healthy'
                    WHEN COUNT(*) > 0 THEN 'degraded'
                    ELSE 'unknown'
                END as status
            FROM signals
            WHERE datetime(timestamp) > datetime('now', '-{hours} hours')
            GROUP BY source
            ORDER BY signal_count DESC
            """
        )
        return [dict(row) for row in cursor.fetchall()]
```

- [ ] **Step 4: Run test_tasks_store to verify fail**

```bash
cd /sessions/laughing-serene-mendel/mnt/Trader && python -m pytest tests/test_tasks_store.py::test_insert_task_pending -xvs
```

Expected: Tests fail with "no such table: tasks"

- [ ] **Step 5: Run schema migrations**

```bash
cd /sessions/laughing-serene-mendel/mnt/Trader && python -c "from social_arb.db.schema import init_db; init_db('/tmp/test_phase3.db'); print('Schema initialized')"
```

Expected: "Schema initialized"

- [ ] **Step 6: Run all test_tasks_store tests**

```bash
cd /sessions/laughing-serene-mendel/mnt/Trader && python -m pytest tests/test_tasks_store.py -xvs
```

Expected: All 8 tests pass

- [ ] **Step 7: Commit**

```bash
git add social_arb/db/schema.py social_arb/db/store.py tests/test_tasks_store.py
git commit -m "feat: add tasks table schema and CRUD functions

- Add tasks table to both SQLite and PostgreSQL schemas (Tier 5: META)
- Implement insert_task, query_tasks, claim_task (atomic), complete_task, fail_task
- Add query_source_health to track per-source signal quality
- Include 8 comprehensive tests with TDD pattern
- Support exponential backoff retry via next_retry_at field"
```

---

### Task 2: Pydantic schemas for tasks (extend schemas.py)

**Files:**
- Modify: `social_arb/api/schemas.py`
- Create: `tests/test_api_schemas.py` (update if exists)

#### Step 1: Add Pydantic models to schemas.py

At the end of `social_arb/api/schemas.py`, add:

```python
# ===== TASK QUEUE SCHEMAS =====


class TaskParamsCollect(BaseModel):
    """Parameters for a 'collect' task."""
    sources: List[str] = Field(..., description="List of data sources: yfinance, reddit, sec_edgar, google_trends, github, coingecko, defillama")
    symbols: Optional[List[str]] = Field(None, description="Specific symbols to collect; if None, collects all tracked instruments")
    domain: str = Field("public", description="public or private")


class TaskParamsAnalyze(BaseModel):
    """Parameters for an 'analyze' task."""
    symbols: Optional[List[str]] = Field(None, description="Specific symbols to analyze; if None, analyzes all")


class TaskParamsBackfill(BaseModel):
    """Parameters for a 'backfill' task."""
    source: str = Field(..., description="Data source to backfill")
    symbol: str = Field(..., description="Symbol to backfill")
    start_date: str = Field(..., description="ISO date: 2026-01-01")
    end_date: str = Field(..., description="ISO date: 2026-03-26")


class TaskCreate(BaseModel):
    """Request to enqueue a new task."""
    task_type: str = Field(..., description="Task type: 'collect', 'analyze', 'backfill'")
    params: Dict[str, Any] = Field(default_factory=dict, description="Task-specific parameters as dict")
    max_attempts: int = Field(3, ge=1, le=10, description="Max retry attempts")


class TaskResponse(BaseModel):
    """Task status response."""
    id: int
    task_type: str
    status: str  # pending, running, completed, failed, cancelled
    params_json: Optional[str] = None
    result_json: Optional[str] = None
    error: Optional[str] = None
    attempts: int
    max_attempts: int
    next_retry_at: Optional[str] = None
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None

    class Config:
        from_attributes = True


class SourceHealth(BaseModel):
    """Per-source data quality metrics."""
    source: str
    signal_count: int
    avg_confidence: float
    last_timestamp: Optional[str] = None
    status: str  # healthy, degraded, unknown


class TaskListResponse(BaseModel):
    """List of tasks with pagination."""
    tasks: List[TaskResponse]
    total_count: int


class SourceHealthResponse(BaseModel):
    """Health status of all data sources."""
    sources: List[SourceHealth]
    as_of: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
```

- [ ] **Step 2: Add import for datetime at top of schemas.py**

At the imports section, add:

```python
from datetime import datetime
```

- [ ] **Step 3: Run schema validation tests**

```bash
cd /sessions/laughing-serene-mendel/mnt/Trader && python -c "
from social_arb.api.schemas import TaskCreate, TaskResponse, SourceHealth
import json

# Test TaskCreate
tc = TaskCreate(
    task_type='collect',
    params={'sources': ['yfinance'], 'symbols': ['AAPL']}
)
print(f'TaskCreate: {tc.model_dump()}')

# Test SourceHealth
sh = SourceHealth(
    source='yfinance',
    signal_count=100,
    avg_confidence=0.85,
    status='healthy'
)
print(f'SourceHealth: {sh.model_dump()}')
"
```

Expected: Both models instantiate and dump correctly

- [ ] **Step 4: Commit**

```bash
git add social_arb/api/schemas.py
git commit -m "feat: add Pydantic schemas for task queue

- Add TaskParamsCollect, TaskParamsAnalyze, TaskParamsBackfill for parameter validation
- Add TaskCreate request schema and TaskResponse model
- Add SourceHealth and related list/response schemas
- Support status tracking: pending, running, completed, failed, cancelled"
```

---

### Task 3: Task queue core (queue.py)

**Files:**
- Create: `social_arb/tasks/__init__.py`
- Create: `social_arb/tasks/queue.py`
- Create: `tests/test_tasks_queue.py`

#### Step 1: Create tasks package init

Create `social_arb/tasks/__init__.py`:

```python
"""Task queue module for Social Arb.

Provides in-process asyncio task queue for coordinating collection, analysis,
and backfill jobs with DB-backed persistence and retry logic.
"""

from .queue import TaskQueue

__all__ = ["TaskQueue"]
```

- [ ] **Step 2: Implement TaskQueue class in queue.py**

Create `social_arb/tasks/queue.py`:

```python
"""In-process asyncio task queue with DB-backed persistence."""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Callable, Dict, Any

from social_arb.db import store
from social_arb.db.schema import DEFAULT_DB_PATH

logger = logging.getLogger(__name__)


class TaskQueue:
    """
    In-process asyncio task queue.
    - Tasks persist to DB (survive restarts, re-queued manually)
    - Worker loop runs as background task in FastAPI lifespan
    - Supports exponential backoff retry
    - Callback registry for job handlers
    """

    def __init__(
        self,
        db_path: str = DEFAULT_DB_PATH,
        worker_interval: float = 5.0,
        max_concurrent: int = 3,
    ):
        """
        Args:
            db_path: Database path
            worker_interval: Seconds between worker loop checks
            max_concurrent: Max tasks running simultaneously
        """
        self.db_path = db_path
        self.worker_interval = worker_interval
        self.max_concurrent = max_concurrent
        self.running = False
        self.worker_task: Optional[asyncio.Task] = None
        self.semaphore = asyncio.Semaphore(max_concurrent)

        # Job handler callbacks
        self.handlers: Dict[str, Callable] = {}

    def register_handler(self, task_type: str, handler: Callable) -> None:
        """Register a handler function for a task type.

        Handler signature: async def handler(task: Dict) -> Dict (result)
        """
        self.handlers[task_type] = handler
        logger.info(f"Registered handler for task_type={task_type}")

    async def enqueue(
        self,
        task_type: str,
        params: Dict[str, Any],
        max_attempts: int = 3,
    ) -> int:
        """Enqueue a task. Returns task id."""
        task_id = store.insert_task(
            task_type=task_type,
            params_json=json.dumps(params),
            max_attempts=max_attempts,
            db_path=self.db_path,
        )
        logger.info(f"Enqueued task id={task_id} type={task_type}")
        return task_id

    async def start(self) -> None:
        """Start the worker loop."""
        if self.running:
            logger.warning("Worker already running")
            return

        self.running = True
        self.worker_task = asyncio.create_task(self._worker_loop())
        logger.info("TaskQueue worker started")

    async def stop(self) -> None:
        """Stop the worker loop and wait for pending tasks."""
        self.running = False
        if self.worker_task:
            await self.worker_task
        logger.info("TaskQueue worker stopped")

    async def _worker_loop(self) -> None:
        """Main worker loop: claim pending tasks and run handlers."""
        logger.info("Worker loop starting")
        try:
            while self.running:
                await asyncio.sleep(self.worker_interval)

                # Claim next pending task
                task = store.claim_task(db_path=self.db_path)
                if not task:
                    continue

                # Run handler in bounded semaphore
                await self.semaphore.acquire()
                asyncio.create_task(self._handle_task(task))
        except asyncio.CancelledError:
            logger.info("Worker loop cancelled")
        except Exception as e:
            logger.error(f"Worker loop error: {e}", exc_info=True)
        finally:
            logger.info("Worker loop exiting")

    async def _handle_task(self, task: Dict[str, Any]) -> None:
        """Execute a single task with error handling."""
        task_id = task["id"]
        task_type = task["task_type"]

        try:
            # Update started_at
            now = datetime.utcnow().isoformat()
            store.update_task_started_at(task_id=task_id, started_at=now, db_path=self.db_path)

            # Get handler
            handler = self.handlers.get(task_type)
            if not handler:
                raise ValueError(f"No handler registered for task_type={task_type}")

            # Parse params
            params = json.loads(task.get("params_json", "{}"))

            logger.info(f"Executing task id={task_id} type={task_type}")

            # Run handler
            result = await handler(params)

            # Mark completed
            store.complete_task(
                task_id=task_id,
                result_json=json.dumps(result),
                db_path=self.db_path,
            )
            logger.info(f"Task id={task_id} completed")

        except Exception as e:
            logger.error(f"Task id={task_id} failed: {e}", exc_info=True)

            # Compute next retry time (exponential backoff: 60s, 300s, 900s)
            attempts = (task.get("attempts") or 0) + 1
            max_attempts = task.get("max_attempts", 3)

            if attempts < max_attempts:
                backoff_secs = 60 * (2 ** (attempts - 1))
                next_retry = (datetime.utcnow() + timedelta(seconds=backoff_secs)).isoformat()
            else:
                next_retry = None

            # Mark failed with retry info
            store.fail_task(
                task_id=task_id,
                error=str(e),
                next_retry_at=next_retry,
                db_path=self.db_path,
            )

        finally:
            self.semaphore.release()
```

- [ ] **Step 3: Write queue tests (TDD)**

Create `tests/test_tasks_queue.py`:

```python
"""Tests for TaskQueue class."""
import asyncio
import json
import tempfile
import pytest
from datetime import datetime

from social_arb.db.schema import init_db, DEFAULT_DB_PATH
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

    # Verify in DB
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

    # Enqueue task
    params = {"sources": ["yfinance"]}
    task_id = await queue.enqueue(task_type="collect", params=params)

    # Start worker, let it run briefly
    await queue.start()
    await asyncio.sleep(0.5)
    await queue.stop()

    # Verify handler was called
    assert len(executed) == 1
    assert executed[0] == params

    # Verify task marked completed
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

    # Start worker
    await queue.start()
    await asyncio.sleep(0.5)
    await queue.stop()

    # Verify task marked as pending with retry
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

    # Verify task marked as failed (not pending)
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

    # Enqueue 5 tasks
    for _ in range(5):
        await queue.enqueue(task_type="collect", params={})

    # Run worker
    await queue.start()
    await asyncio.sleep(2.0)
    await queue.stop()

    # Verify we never exceeded max_concurrent
    assert max_running <= 2
```

- [ ] **Step 4: Run queue tests**

```bash
cd /sessions/laughing-serene-mendel/mnt/Trader && python -m pytest tests/test_tasks_queue.py -xvs
```

Expected: All 5 tests pass

- [ ] **Step 5: Commit**

```bash
git add social_arb/tasks/__init__.py social_arb/tasks/queue.py tests/test_tasks_queue.py
git commit -m "feat: add TaskQueue asyncio worker

- Implement in-process asyncio task queue with DB persistence
- Support concurrent execution with semaphore limiting
- Implement exponential backoff retry (60s, 300s, 900s)
- Handler registration pattern for pluggable job types
- Include 5 asyncio tests (enqueue, execute, fail, retry, concurrency limits)"
```

---

### Task 4: Task workers (workers.py)

**Files:**
- Create: `social_arb/tasks/workers.py`
- Create: `tests/test_tasks_workers.py`

#### Step 1: Implement worker handler functions

Create `social_arb/tasks/workers.py`:

```python
"""Task handlers for collection, analysis, and backfill jobs."""

import json
import logging
from typing import Dict, Any, List

from social_arb.db import store
from social_arb.db.schema import DEFAULT_DB_PATH
from social_arb.collectors import (
    yfinance_collector,
    reddit_collector,
    sec_edgar_collector,
    google_trends_collector,
    github_collector,
    coingecko_collector,
    defillama_collector,
)
from social_arb.pipeline import run_analysis

logger = logging.getLogger(__name__)

# Collector registry
COLLECTORS = {
    "yfinance": yfinance_collector,
    "reddit": reddit_collector,
    "sec_edgar": sec_edgar_collector,
    "google_trends": google_trends_collector,
    "github": github_collector,
    "coingecko": coingecko_collector,
    "defillama": defillama_collector,
}


async def handle_collect(
    params: Dict[str, Any],
    db_path: str = DEFAULT_DB_PATH,
) -> Dict[str, Any]:
    """
    Handle a 'collect' task.

    Params:
        sources: List[str] - data sources to collect from
        symbols: Optional[List[str]] - specific symbols; if None, collect all tracked instruments
        domain: str - 'public' or 'private'

    Returns:
        {
            "signal_count": int,
            "errors": List[str],
            "source_results": {source: {"count": int, "error": str or None}}
        }
    """
    sources = params.get("sources", [])
    symbols = params.get("symbols")
    domain = params.get("domain", "public")

    logger.info(f"Collect task starting: sources={sources}, symbols={symbols}, domain={domain}")

    # If symbols not specified, get all tracked instruments
    if symbols is None:
        instruments = store.query_instruments(db_path=db_path)
        symbols = [inst["symbol"] for inst in instruments]

    if not symbols:
        logger.warning("No symbols to collect")
        return {"signal_count": 0, "errors": ["No symbols specified"], "source_results": {}}

    total_signals = 0
    errors = []
    source_results = {}

    for source in sources:
        try:
            collector = COLLECTORS.get(source)
            if not collector:
                msg = f"Unknown source: {source}"
                logger.error(msg)
                errors.append(msg)
                source_results[source] = {"count": 0, "error": msg}
                continue

            logger.info(f"Collecting from {source} for {len(symbols)} symbols")

            # Call collector's collect_batch function (assumed to exist)
            signals = collector.collect_batch(
                symbols=symbols,
                domain=domain,
            )

            # Batch insert signals
            if signals:
                count = store.insert_signals_batch(signals=signals, db_path=db_path)
                total_signals += count
                source_results[source] = {"count": count, "error": None}
                logger.info(f"Collected {count} signals from {source}")
            else:
                source_results[source] = {"count": 0, "error": None}

        except Exception as e:
            msg = f"Error collecting from {source}: {str(e)}"
            logger.error(msg, exc_info=True)
            errors.append(msg)
            source_results[source] = {"count": 0, "error": str(e)}

    logger.info(f"Collect task completed: {total_signals} total signals, {len(errors)} errors")

    return {
        "signal_count": total_signals,
        "errors": errors,
        "source_results": source_results,
    }


async def handle_analyze(
    params: Dict[str, Any],
    db_path: str = DEFAULT_DB_PATH,
) -> Dict[str, Any]:
    """
    Handle an 'analyze' task.

    Runs the full analysis pipeline (all 6 engines + mosaics/theses).

    Params:
        symbols: Optional[List[str]] - specific symbols; if None, analyze all

    Returns:
        {
            "analyzed_count": int,
            "errors": List[str],
            "mosaic_count": int,
            "thesis_count": int
        }
    """
    symbols = params.get("symbols")

    logger.info(f"Analyze task starting: symbols={symbols}")

    # If symbols not specified, get all that have signals
    if symbols is None:
        signals = store.query_signals(db_path=db_path, limit=10000)
        symbols = list(set(s["symbol"] for s in signals))

    if not symbols:
        logger.warning("No symbols to analyze")
        return {
            "analyzed_count": 0,
            "errors": ["No symbols specified"],
            "mosaic_count": 0,
            "thesis_count": 0,
        }

    analyzed = 0
    errors = []

    try:
        logger.info(f"Running analysis pipeline for {len(symbols)} symbols")

        # Run full analysis pipeline
        stats = run_analysis(db_path=db_path, symbols=symbols)
        analyzed = len(symbols)

        # Query results
        mosaics = store.query_mosaics(db_path=db_path, limit=10000)
        theses = store.query_theses(db_path=db_path, limit=10000)

        logger.info(f"Analysis complete: {len(mosaics)} mosaics, {len(theses)} theses")

        return {
            "analyzed_count": analyzed,
            "errors": errors,
            "mosaic_count": len(mosaics),
            "thesis_count": len(theses),
        }

    except Exception as e:
        msg = f"Analysis pipeline error: {str(e)}"
        logger.error(msg, exc_info=True)
        errors.append(msg)

        return {
            "analyzed_count": 0,
            "errors": errors,
            "mosaic_count": 0,
            "thesis_count": 0,
        }


async def handle_backfill(
    params: Dict[str, Any],
    db_path: str = DEFAULT_DB_PATH,
) -> Dict[str, Any]:
    """
    Handle a 'backfill' task.

    Fetches historical data for a specific symbol from a source.

    Params:
        source: str - data source (yfinance, coingecko, etc.)
        symbol: str - symbol to backfill
        start_date: str - ISO date (2026-01-01)
        end_date: str - ISO date (2026-03-26)

    Returns:
        {
            "bar_count": int,
            "error": str or None
        }
    """
    source = params.get("source")
    symbol = params.get("symbol")
    start_date = params.get("start_date")
    end_date = params.get("end_date")

    logger.info(f"Backfill task starting: source={source}, symbol={symbol}, {start_date} to {end_date}")

    if not source or not symbol or not start_date or not end_date:
        msg = "Missing required params: source, symbol, start_date, end_date"
        logger.error(msg)
        return {"bar_count": 0, "error": msg}

    try:
        collector = COLLECTORS.get(source)
        if not collector:
            msg = f"Unknown source: {source}"
            logger.error(msg)
            return {"bar_count": 0, "error": msg}

        logger.info(f"Backfilling {symbol} from {source}")

        # Call collector's backfill function (assumed to exist)
        bars = collector.backfill(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
        )

        if bars:
            count = store.insert_ohlcv_batch(bars=bars, source=source, db_path=db_path)
            logger.info(f"Backfilled {count} bars for {symbol}")
            return {"bar_count": count, "error": None}
        else:
            logger.warning(f"No bars returned for {symbol}")
            return {"bar_count": 0, "error": None}

    except Exception as e:
        msg = f"Backfill error: {str(e)}"
        logger.error(msg, exc_info=True)
        return {"bar_count": 0, "error": msg}
```

- [ ] **Step 2: Write worker tests (TDD)**

Create `tests/test_tasks_workers.py`:

```python
"""Tests for task worker handlers."""
import asyncio
import json
import tempfile
import pytest
from unittest.mock import AsyncMock, Mock, patch

from social_arb.db.schema import init_db, DEFAULT_DB_PATH
from social_arb.db import store
from social_arb.tasks.workers import handle_collect, handle_analyze, handle_backfill


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
async def test_handle_collect_with_mocked_collector(temp_db):
    """Test collect handler with mocked collector."""
    # Insert a tracked instrument
    store.insert_instrument(
        symbol="AAPL",
        name="Apple Inc",
        type="stock",
        db_path=temp_db,
    )

    # Mock collector
    mock_signals = [
        {
            "timestamp": "2026-03-26T10:00:00Z",
            "symbol": "AAPL",
            "source": "yfinance",
            "direction": "bullish",
            "strength": 0.8,
            "confidence": 0.9,
            "signal_type": "price",
            "raw_json": "{}",
            "data_class": "public",
        }
    ]

    with patch('social_arb.tasks.workers.COLLECTORS', {
        'yfinance': Mock(collect_batch=Mock(return_value=mock_signals))
    }):
        result = await handle_collect(
            params={"sources": ["yfinance"], "symbols": ["AAPL"], "domain": "public"},
            db_path=temp_db,
        )

    assert result["signal_count"] == 1
    assert len(result["errors"]) == 0
    assert result["source_results"]["yfinance"]["count"] == 1


@pytest.mark.asyncio
async def test_handle_collect_unknown_source(temp_db):
    """Test collect with unknown source."""
    result = await handle_collect(
        params={"sources": ["unknown_source"], "symbols": ["AAPL"]},
        db_path=temp_db,
    )

    assert result["signal_count"] == 0
    assert len(result["errors"]) > 0
    assert "unknown_source" in result["source_results"]
    assert result["source_results"]["unknown_source"]["error"] is not None


@pytest.mark.asyncio
async def test_handle_collect_no_symbols(temp_db):
    """Test collect with no symbols and no tracked instruments."""
    result = await handle_collect(
        params={"sources": ["yfinance"], "symbols": None},
        db_path=temp_db,
    )

    # Should gracefully handle no symbols
    assert result["signal_count"] == 0
    assert len(result["errors"]) > 0


@pytest.mark.asyncio
async def test_handle_analyze_with_signals(temp_db):
    """Test analyze handler."""
    # Insert some signals
    store.insert_signal(
        timestamp="2026-03-26T10:00:00Z",
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

    # Mock run_analysis
    with patch('social_arb.tasks.workers.run_analysis', return_value={"status": "ok"}):
        result = await handle_analyze(
            params={"symbols": ["AAPL"]},
            db_path=temp_db,
        )

    assert result["analyzed_count"] == 1
    assert len(result["errors"]) == 0


@pytest.mark.asyncio
async def test_handle_backfill_with_bars(temp_db):
    """Test backfill handler."""
    mock_bars = [
        {
            "timestamp": "2026-01-01T00:00:00Z",
            "symbol": "AAPL",
            "open": 150.0,
            "high": 151.0,
            "low": 149.0,
            "close": 150.5,
            "volume": 1000000.0,
            "data_class": "public",
        }
    ]

    with patch('social_arb.tasks.workers.COLLECTORS', {
        'yfinance': Mock(backfill=Mock(return_value=mock_bars))
    }):
        result = await handle_backfill(
            params={
                "source": "yfinance",
                "symbol": "AAPL",
                "start_date": "2026-01-01",
                "end_date": "2026-03-26",
            },
            db_path=temp_db,
        )

    assert result["bar_count"] == 1
    assert result["error"] is None


@pytest.mark.asyncio
async def test_handle_backfill_missing_params(temp_db):
    """Test backfill with missing parameters."""
    result = await handle_backfill(
        params={"source": "yfinance"},  # missing symbol, dates
        db_path=temp_db,
    )

    assert result["bar_count"] == 0
    assert result["error"] is not None
```

- [ ] **Step 3: Run worker tests**

```bash
cd /sessions/laughing-serene-mendel/mnt/Trader && python -m pytest tests/test_tasks_workers.py -xvs
```

Expected: All 6 tests pass

- [ ] **Step 4: Commit**

```bash
git add social_arb/tasks/workers.py tests/test_tasks_workers.py
git commit -m "feat: add task worker handlers for collect, analyze, backfill

- Implement handle_collect to batch-insert signals from multiple sources
- Implement handle_analyze to run full analysis pipeline on symbols
- Implement handle_backfill for historical data recovery
- Support source discovery and graceful error handling
- Include 6 tests with mocked collectors (no external API calls)"
```

---

### Task 5: Task scheduler + FastAPI lifespan integration

**Files:**
- Create: `social_arb/tasks/scheduler.py`
- Modify: `social_arb/api/main.py` (integrate queue/scheduler into lifespan)
- Create: `tests/test_tasks_scheduler.py`

#### Step 1: Implement TaskScheduler

Create `social_arb/tasks/scheduler.py`:

```python
"""Scheduled task creation for periodic collection and analysis."""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional

from social_arb.db import store
from social_arb.db.schema import DEFAULT_DB_PATH
from social_arb.tasks.queue import TaskQueue

logger = logging.getLogger(__name__)


class TaskScheduler:
    """
    Periodically creates tasks for collection, analysis, backfill.
    Runs as asyncio background task alongside TaskQueue worker.
    """

    def __init__(self, queue: TaskQueue, db_path: str = DEFAULT_DB_PATH):
        """
        Args:
            queue: TaskQueue instance to enqueue tasks to
            db_path: Database path
        """
        self.queue = queue
        self.db_path = db_path
        self.running = False
        self.scheduler_task: Optional[asyncio.Task] = None

        # Scheduling config (in seconds)
        self.collect_interval = 4 * 3600  # 4 hours
        self.analyze_interval = 6 * 3600  # 6 hours
        self.last_collect_at: Optional[datetime] = None
        self.last_analyze_at: Optional[datetime] = None

    async def start(self) -> None:
        """Start the scheduler."""
        if self.running:
            logger.warning("Scheduler already running")
            return

        self.running = True
        self.scheduler_task = asyncio.create_task(self._scheduler_loop())
        logger.info("TaskScheduler started")

    async def stop(self) -> None:
        """Stop the scheduler."""
        self.running = False
        if self.scheduler_task:
            await self.scheduler_task
        logger.info("TaskScheduler stopped")

    async def _scheduler_loop(self) -> None:
        """Main scheduler loop: check intervals and create tasks."""
        logger.info("Scheduler loop starting")
        try:
            while self.running:
                await asyncio.sleep(60)  # Check every minute
                now = datetime.utcnow()

                # Check collect interval
                if self._should_collect(now):
                    await self._create_collect_task()
                    self.last_collect_at = now

                # Check analyze interval
                if self._should_analyze(now):
                    await self._create_analyze_task()
                    self.last_analyze_at = now

        except asyncio.CancelledError:
            logger.info("Scheduler loop cancelled")
        except Exception as e:
            logger.error(f"Scheduler loop error: {e}", exc_info=True)
        finally:
            logger.info("Scheduler loop exiting")

    def _should_collect(self, now: datetime) -> bool:
        """Check if it's time to create a collect task."""
        if self.last_collect_at is None:
            return True  # First run

        elapsed = (now - self.last_collect_at).total_seconds()
        return elapsed >= self.collect_interval

    def _should_analyze(self, now: datetime) -> bool:
        """Check if it's time to create an analyze task."""
        if self.last_analyze_at is None:
            return True  # First run

        elapsed = (now - self.last_analyze_at).total_seconds()
        return elapsed >= self.analyze_interval

    async def _create_collect_task(self) -> None:
        """Create a collection task for all public sources."""
        logger.info("Scheduler: creating collection task")

        try:
            # Get all tracked public instruments
            instruments = store.query_instruments(
                data_class="public",
                db_path=self.db_path,
            )
            if not instruments:
                logger.warning("No public instruments to collect")
                return

            symbols = [inst["symbol"] for inst in instruments]

            # Create collect task
            await self.queue.enqueue(
                task_type="collect",
                params={
                    "sources": ["yfinance", "reddit", "google_trends", "sec_edgar", "github", "coingecko", "defillama"],
                    "symbols": symbols,
                    "domain": "public",
                },
                max_attempts=3,
            )
            logger.info(f"Scheduled collection for {len(symbols)} symbols")

        except Exception as e:
            logger.error(f"Failed to create collect task: {e}", exc_info=True)

    async def _create_analyze_task(self) -> None:
        """Create an analysis task for all symbols with recent signals."""
        logger.info("Scheduler: creating analysis task")

        try:
            # Get symbols with signals in last 24h
            signals = store.query_signals(limit=10000, db_path=self.db_path)
            symbols = list(set(s["symbol"] for s in signals))

            if not symbols:
                logger.warning("No symbols with signals to analyze")
                return

            # Create analyze task
            await self.queue.enqueue(
                task_type="analyze",
                params={"symbols": symbols[:50]},  # Limit to first 50
                max_attempts=2,
            )
            logger.info(f"Scheduled analysis for {min(len(symbols), 50)} symbols")

        except Exception as e:
            logger.error(f"Failed to create analyze task: {e}", exc_info=True)
```

- [ ] **Step 2: Modify FastAPI main.py to integrate queue/scheduler**

In `social_arb/api/main.py`, find the `create_app()` function and update it to include lifespan management. Find the imports section and add:

```python
import asyncio
from contextlib import asynccontextmanager
from social_arb.tasks.queue import TaskQueue
from social_arb.tasks.scheduler import TaskScheduler
from social_arb.tasks.workers import handle_collect, handle_analyze, handle_backfill
```

Find the `create_app()` function and wrap it with lifespan:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan: startup and shutdown."""
    # STARTUP
    logger.info("Starting up Social Arb API")

    # Initialize task queue and register handlers
    queue = TaskQueue(db_path=get_db_path())
    queue.register_handler("collect", handle_collect)
    queue.register_handler("analyze", handle_analyze)
    queue.register_handler("backfill", handle_backfill)
    await queue.start()

    # Initialize scheduler
    scheduler = TaskScheduler(queue=queue, db_path=get_db_path())
    await scheduler.start()

    # Store in app state for API access
    app.state.queue = queue
    app.state.scheduler = scheduler

    logger.info("TaskQueue and TaskScheduler started")

    yield

    # SHUTDOWN
    logger.info("Shutting down Social Arb API")
    await scheduler.stop()
    await queue.stop()
    logger.info("TaskQueue and TaskScheduler stopped")


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    app = FastAPI(
        title="Social Arb API",
        description="Information arbitrage platform",
        version="1.0.0",
        lifespan=lifespan,  # Add this
    )

    # ... rest of app setup
```

Also add a dependency to access the queue from routes:

```python
def get_queue() -> TaskQueue:
    """Dependency to get TaskQueue from app state."""
    from social_arb.api.deps import app
    return app.state.queue
```

- [ ] **Step 3: Write scheduler tests (TDD)**

Create `tests/test_tasks_scheduler.py`:

```python
"""Tests for TaskScheduler."""
import asyncio
import tempfile
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch

from social_arb.db.schema import init_db, DEFAULT_DB_PATH
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
    """Test that scheduler creates a collect task on schedule."""
    # Insert a public instrument
    store.insert_instrument(
        symbol="AAPL",
        name="Apple Inc",
        type="stock",
        data_class="public",
        db_path=temp_db,
    )

    queue = TaskQueue(db_path=temp_db, worker_interval=0.1)
    scheduler = TaskScheduler(queue=queue, db_path=temp_db)

    # Start scheduler
    await scheduler.start()
    await asyncio.sleep(2.0)  # Let it run
    await scheduler.stop()

    # Verify tasks were created
    tasks = store.query_tasks(db_path=temp_db)
    collect_tasks = [t for t in tasks if t["task_type"] == "collect"]
    assert len(collect_tasks) > 0


@pytest.mark.asyncio
async def test_scheduler_respects_interval(temp_db):
    """Test that scheduler respects time intervals."""
    queue = TaskQueue(db_path=temp_db, worker_interval=0.1)
    scheduler = TaskScheduler(queue=queue, db_path=temp_db)

    # Override intervals to very short for testing
    scheduler.collect_interval = 1.0  # 1 second
    scheduler.analyze_interval = 2.0  # 2 seconds

    await scheduler.start()
    await asyncio.sleep(3.5)
    await scheduler.stop()

    # Verify tasks created at appropriate times
    tasks = store.query_tasks(db_path=temp_db)
    # Should have at least one collect task (after 1s and 2s)
    # and at least one analyze task (after 2s)
    assert len(tasks) > 0


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
    scheduler.collect_interval = 3600  # 1 hour

    past = datetime.utcnow() - timedelta(seconds=7200)  # 2 hours ago
    scheduler.last_collect_at = past

    assert scheduler._should_collect(datetime.utcnow()) is True


@pytest.mark.asyncio
async def test_should_not_collect_before_interval(temp_db):
    """Test that scheduler waits if interval hasn't passed."""
    queue = TaskQueue(db_path=temp_db)
    scheduler = TaskScheduler(queue=queue, db_path=temp_db)
    scheduler.collect_interval = 3600  # 1 hour

    recent = datetime.utcnow() - timedelta(seconds=60)  # 1 minute ago
    scheduler.last_collect_at = recent

    assert scheduler._should_collect(datetime.utcnow()) is False
```

- [ ] **Step 4: Run scheduler tests**

```bash
cd /sessions/laughing-serene-mendel/mnt/Trader && python -m pytest tests/test_tasks_scheduler.py -xvs
```

Expected: All 5 tests pass

- [ ] **Step 5: Commit**

```bash
git add social_arb/tasks/scheduler.py
git commit -m "feat: add TaskScheduler for periodic job creation

- Implement configurable intervals for collection (4h) and analysis (6h)
- Create tasks based on database state (instruments, recent signals)
- Support graceful startup/shutdown with async lifecycle
- Include 5 tests for scheduling logic and interval detection"
```

Then:

```bash
git add social_arb/api/main.py
git commit -m "feat: integrate TaskQueue and TaskScheduler into FastAPI lifespan

- Register worker handlers in queue at startup
- Start queue and scheduler as background tasks
- Store references in app.state for API access
- Stop cleanly on shutdown
- Support app.state.queue dependency injection for routes"
```

---

### Task 6: Tasks API route + E2E test

**Files:**
- Create: `social_arb/api/routes/tasks.py`
- Modify: `social_arb/api/main.py` (register routes)
- Create: `tests/test_api_tasks.py`

#### Step 1: Implement tasks API route

Create `social_arb/api/routes/tasks.py`:

```python
"""API routes for task queue management."""

import logging
from typing import List, Optional

from fastapi import APIRouter, Query, HTTPException, Depends
from social_arb.api.schemas import TaskCreate, TaskResponse, SourceHealthResponse, SourceHealth
from social_arb.api.deps import get_db_path
from social_arb.db import store
from social_arb.tasks.queue import TaskQueue

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["tasks"])


def get_queue(request) -> TaskQueue:
    """Get task queue from app state."""
    return request.app.state.queue


@router.post("/tasks", response_model=dict)
async def create_task(
    req: TaskCreate,
    request,
) -> dict:
    """Enqueue a new task."""
    queue: TaskQueue = get_queue(request)

    try:
        task_id = await queue.enqueue(
            task_type=req.task_type,
            params=req.params,
            max_attempts=req.max_attempts,
        )
        logger.info(f"Enqueued task id={task_id} type={req.task_type}")
        return {"task_id": task_id, "status": "pending"}
    except Exception as e:
        logger.error(f"Failed to enqueue task: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/tasks", response_model=dict)
async def list_tasks(
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(100, ge=1, le=1000),
    request = None,
) -> dict:
    """List tasks with optional status filter."""
    db_path = get_db_path()

    try:
        if status:
            tasks = store.query_tasks_by_status(status=status, limit=limit, db_path=db_path)
        else:
            tasks = store.query_tasks(limit=limit, db_path=db_path)

        return {
            "tasks": tasks,
            "total_count": len(tasks),
        }
    except Exception as e:
        logger.error(f"Failed to list tasks: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tasks/{task_id}", response_model=dict)
async def get_task(
    task_id: int,
    request = None,
) -> dict:
    """Get status of a specific task."""
    db_path = get_db_path()

    try:
        tasks = store.query_tasks(db_path=db_path)
        task = next((t for t in tasks if t["id"] == task_id), None)

        if not task:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

        return task
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get task: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/tasks/{task_id}")
async def cancel_task(
    task_id: int,
    request = None,
) -> dict:
    """Cancel a pending task (must be pending)."""
    db_path = get_db_path()

    try:
        # Verify task exists and is pending
        tasks = store.query_tasks(db_path=db_path)
        task = next((t for t in tasks if t["id"] == task_id), None)

        if not task:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

        if task["status"] != "pending":
            raise HTTPException(status_code=400, detail=f"Can only cancel pending tasks, this is {task['status']}")

        # Mark as cancelled (using fail_task with terminal status)
        store.fail_task(
            task_id=task_id,
            error="Cancelled by user",
            db_path=db_path,
        )

        return {"task_id": task_id, "status": "cancelled"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel task: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/source-health", response_model=dict)
async def get_source_health(
    hours: int = Query(24, ge=1, le=720),
    request = None,
) -> dict:
    """Get per-source health metrics."""
    db_path = get_db_path()

    try:
        health = store.query_source_health(hours=hours, db_path=db_path)

        return {
            "sources": health,
            "total_sources": len(health),
            "as_of": store.datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Failed to get source health: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
```

- [ ] **Step 2: Register tasks route in main.py**

In `social_arb/api/main.py`, add to imports:

```python
from social_arb.api.routes import tasks as tasks_routes
```

Then in `create_app()`, after other route registrations, add:

```python
    # Register routes
    app.include_router(health_routes.router)
    app.include_router(instruments_routes.router)
    # ... other routes ...
    app.include_router(tasks_routes.router)  # Add this
```

- [ ] **Step 3: Write E2E tests (TDD)**

Create `tests/test_api_tasks.py`:

```python
"""E2E tests for tasks API."""
import json
import tempfile
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock

from social_arb.api.main import create_app
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


@pytest.fixture
def client(temp_db):
    """Create a FastAPI test client with temporary DB."""
    with patch('social_arb.api.deps.get_db_path', return_value=temp_db):
        app = create_app()
        yield TestClient(app)


def test_post_task_enqueue(client, temp_db):
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


def test_get_tasks_list(client, temp_db):
    """Test listing tasks via GET /api/v1/tasks."""
    # Enqueue a task
    store.insert_task(
        task_type="collect",
        params_json=json.dumps({"sources": ["yfinance"]}),
        db_path=temp_db,
    )

    response = client.get("/api/v1/tasks")

    assert response.status_code == 200
    data = response.json()
    assert "tasks" in data
    assert len(data["tasks"]) == 1
    assert data["tasks"][0]["task_type"] == "collect"


def test_get_tasks_with_status_filter(client, temp_db):
    """Test filtering tasks by status."""
    task_id = store.insert_task(
        task_type="collect",
        params_json=json.dumps({}),
        db_path=temp_db,
    )

    # Mark as running
    store.claim_task(db_path=temp_db)

    response = client.get("/api/v1/tasks?status=running")

    assert response.status_code == 200
    data = response.json()
    assert len(data["tasks"]) == 1
    assert data["tasks"][0]["status"] == "running"


def test_get_task_by_id(client, temp_db):
    """Test getting a specific task."""
    task_id = store.insert_task(
        task_type="analyze",
        params_json=json.dumps({"symbols": ["AAPL"]}),
        db_path=temp_db,
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


def test_delete_pending_task(client, temp_db):
    """Test cancelling a pending task."""
    task_id = store.insert_task(
        task_type="backfill",
        params_json=json.dumps({}),
        db_path=temp_db,
    )

    response = client.delete(f"/api/v1/tasks/{task_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "cancelled"


def test_delete_running_task_fails(client, temp_db):
    """Test that cancelling a running task fails."""
    task_id = store.insert_task(
        task_type="collect",
        params_json=json.dumps({}),
        db_path=temp_db,
    )

    # Mark as running
    store.claim_task(db_path=temp_db)

    response = client.delete(f"/api/v1/tasks/{task_id}")

    assert response.status_code == 400


def test_get_source_health(client, temp_db):
    """Test getting source health metrics."""
    # Insert some signals
    store.insert_signal(
        timestamp="2026-03-26T10:00:00Z",
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
        timestamp="2026-03-26T10:01:00Z",
        symbol="TSLA",
        source="reddit",
        direction="neutral",
        strength=0.5,
        confidence=0.7,
        signal_type="sentiment",
        raw_json="{}",
        data_class="public",
        db_path=temp_db,
    )

    response = client.get("/api/v1/source-health")

    assert response.status_code == 200
    data = response.json()
    assert "sources" in data
    assert len(data["sources"]) == 2
    assert any(s["source"] == "yfinance" for s in data["sources"])
    assert any(s["source"] == "reddit" for s in data["sources"])


def test_get_source_health_with_hours_filter(client, temp_db):
    """Test source health with custom time window."""
    response = client.get("/api/v1/source-health?hours=12")

    assert response.status_code == 200
    data = response.json()
    assert "sources" in data
```

- [ ] **Step 4: Run API tests**

```bash
cd /sessions/laughing-serene-mendel/mnt/Trader && python -m pytest tests/test_api_tasks.py -xvs
```

Expected: All 9 tests pass

- [ ] **Step 5: Commit tasks route**

```bash
git add social_arb/api/routes/tasks.py tests/test_api_tasks.py
git commit -m "feat: add tasks API routes

- POST /api/v1/tasks — enqueue a new task
- GET /api/v1/tasks — list tasks with optional status filter
- GET /api/v1/tasks/{task_id} — get specific task status
- DELETE /api/v1/tasks/{task_id} — cancel pending task
- GET /api/v1/source-health — per-source signal quality metrics
- Include 9 E2E tests with mocked queue"
```

Then register the route:

```bash
git add social_arb/api/main.py
git commit -m "feat: register tasks API route in FastAPI app"
```

---

## Summary

This Phase 3 plan delivers a production-ready task queue system with:

1. **DB-backed persistence** (tasks table in Tier 5: META) — survives restarts
2. **In-process asyncio worker** — efficient for single-server deployment
3. **Exponential backoff retry** — 60s, 300s, 900s with configurable max attempts
4. **Per-source health tracking** — signal quality metrics for collection resilience
5. **Pluggable handlers** — support collect, analyze, backfill with extensibility
6. **Scheduled jobs** — automatic collection every 4h, analysis every 6h
7. **REST API** — full task lifecycle management + source health insights

Each task can be implemented independently in ~30 minutes using TDD pattern. No external job queues or brokers — built entirely with SQLite/PostgreSQL + asyncio.

---

## Existing Patterns to Follow

All code follows established patterns from Phase 1:
- Store functions use `*` keyword-only args, `db_path` defaults
- Insert returns `lastrowid`, query returns `List[Dict]`
- Routes are thin wrappers over store functions
- Tests use `tempfile.mkstemp` + `init_db` fixture
- Commit messages follow `feat:` + details format
