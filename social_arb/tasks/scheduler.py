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
    Periodically creates tasks for collection and analysis.
    Runs as asyncio background task alongside TaskQueue worker.
    """

    def __init__(self, queue: TaskQueue, db_path: str = DEFAULT_DB_PATH):
        self.queue = queue
        self.db_path = db_path
        self.running = False
        self.scheduler_task: Optional[asyncio.Task] = None

        # Scheduling config (in seconds)
        self.collect_interval = 4 * 3600  # 4 hours
        self.analyze_interval = 6 * 3600  # 6 hours
        self.train_stepps_interval = 7 * 24 * 3600  # 7 days
        self.private_collect_interval = 24 * 3600  # Daily
        self.last_collect_at: Optional[datetime] = None
        self.last_analyze_at: Optional[datetime] = None
        self.last_train_stepps_at: Optional[datetime] = None
        self.last_private_collect_at: Optional[datetime] = None

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

                if self._should_collect(now):
                    await self._create_collect_task()
                    self.last_collect_at = now

                if self._should_analyze(now):
                    await self._create_analyze_task()
                    self.last_analyze_at = now

                if self._should_train_stepps(now):
                    await self._create_train_stepps_task()
                    self.last_train_stepps_at = now

                if self._should_private_collect(now):
                    await self._create_private_collect_task()
                    self.last_private_collect_at = now

        except asyncio.CancelledError:
            logger.info("Scheduler loop cancelled")
        except Exception as e:
            logger.error(f"Scheduler loop error: {e}", exc_info=True)
        finally:
            logger.info("Scheduler loop exiting")

    def _should_collect(self, now: datetime) -> bool:
        """Check if it's time to create a collect task."""
        if self.last_collect_at is None:
            return True
        return (now - self.last_collect_at).total_seconds() >= self.collect_interval

    def _should_analyze(self, now: datetime) -> bool:
        """Check if it's time to create an analyze task."""
        if self.last_analyze_at is None:
            return True
        return (now - self.last_analyze_at).total_seconds() >= self.analyze_interval

    def _should_train_stepps(self, now: datetime) -> bool:
        """Check if it's time to create a train_stepps task."""
        if self.last_train_stepps_at is None:
            return True
        return (now - self.last_train_stepps_at).total_seconds() >= self.train_stepps_interval

    def _should_private_collect(self, now: datetime) -> bool:
        """Check if it's time to create a private company collection task."""
        if self.last_private_collect_at is None:
            return True
        return (now - self.last_private_collect_at).total_seconds() >= self.private_collect_interval

    async def _create_collect_task(self) -> None:
        """Create a collection task for all public sources."""
        logger.info("Scheduler: creating collection task")
        try:
            instruments = store.query_instruments(
                data_class="public",
                db_path=self.db_path,
            )
            if not instruments:
                logger.warning("No public instruments to collect")
                return

            symbols = [inst["symbol"] for inst in instruments]

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
        """Create an analysis task for all symbols with signals."""
        logger.info("Scheduler: creating analysis task")
        try:
            signals = store.query_signals(limit=10000, db_path=self.db_path)
            symbols = list(set(s["symbol"] for s in signals))

            if not symbols:
                logger.warning("No symbols with signals to analyze")
                return

            await self.queue.enqueue(
                task_type="analyze",
                params={"symbols": symbols[:50]},
                max_attempts=2,
            )
            logger.info(f"Scheduled analysis for {min(len(symbols), 50)} symbols")

        except Exception as e:
            logger.error(f"Failed to create analyze task: {e}", exc_info=True)

    async def _create_train_stepps_task(self) -> None:
        """Create a weekly STEPPS retraining task."""
        logger.info("Scheduler: creating STEPPS training task")
        try:
            await self.queue.enqueue(
                task_type="train_stepps",
                params={},
                max_attempts=2,
            )
            logger.info("Scheduled STEPPS training task")

        except Exception as e:
            logger.error(f"Failed to create STEPPS training task: {e}", exc_info=True)

    async def _create_private_collect_task(self) -> None:
        """Create a collection task for private company sources."""
        logger.info("Scheduler: creating private company collection task")
        try:
            from social_arb.config import config

            symbols = config.private_symbols

            if not symbols:
                logger.warning("No private company symbols to collect")
                return

            await self.queue.enqueue(
                task_type="collect",
                params={
                    "sources": ["news", "hiring", "patents", "appstore", "web_presence"],
                    "symbols": symbols,
                    "domain": "private",
                },
                max_attempts=3,
            )
            logger.info(f"Scheduled private company collection for {len(symbols)} symbols")

        except Exception as e:
            logger.error(f"Failed to create private collect task: {e}", exc_info=True)
