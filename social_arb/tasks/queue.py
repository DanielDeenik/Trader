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
        self.db_path = db_path
        self.worker_interval = worker_interval
        self.max_concurrent = max_concurrent
        self.running = False
        self.worker_task: Optional[asyncio.Task] = None
        self.semaphore = asyncio.Semaphore(max_concurrent)
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

                task = store.claim_task(db_path=self.db_path)
                if not task:
                    continue

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
            now = datetime.utcnow().isoformat()
            store.update_task_started_at(task_id=task_id, started_at=now, db_path=self.db_path)

            handler = self.handlers.get(task_type)
            if not handler:
                raise ValueError(f"No handler registered for task_type={task_type}")

            params = json.loads(task.get("params_json", "{}"))
            logger.info(f"Executing task id={task_id} type={task_type}")

            result = await handler(params)

            store.complete_task(
                task_id=task_id,
                result_json=json.dumps(result),
                db_path=self.db_path,
            )
            logger.info(f"Task id={task_id} completed")

        except Exception as e:
            logger.error(f"Task id={task_id} failed: {e}", exc_info=True)

            attempts = (task.get("attempts") or 0) + 1
            max_attempts = task.get("max_attempts", 3)

            if attempts < max_attempts:
                backoff_secs = 60 * (2 ** (attempts - 1))
                next_retry = (datetime.utcnow() + timedelta(seconds=backoff_secs)).isoformat()
            else:
                next_retry = None

            store.fail_task(
                task_id=task_id,
                error=str(e),
                next_retry_at=next_retry,
                db_path=self.db_path,
            )

        finally:
            self.semaphore.release()
