"""
Sentinel Agent — L0 Collection Orchestration (Peripheral Vision)

Subscribes to: TASK_COMPLETED (to detect when collection finishes), SOURCE_STALE
Tick: Every 60s, checks source freshness via DB query on signals table (latest timestamp per source)
If any source is stale (>4h old), enqueues a collect task for those sources only
When collection task completes, publishes SIGNALS_COLLECTED with stats (signal_count, sources, symbols)

Role: Ensures raw signals stay fresh across all configured sources.
The Sentinel is the entry point to the pipeline — without fresh data, nothing moves.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from social_arb.db.schema import get_connection, DEFAULT_DB_PATH
from social_arb.db.adapter import get_placeholder
from social_arb.tasks.workers import handle_collect
from social_arb.tasks.queue import TaskQueue

from .base import BaseAgent
from .context import adapt
from .events import Event, EventBus, EventType
from .knowledge import KnowledgeStore
from .researcher import ResearchOrchestrator

logger = logging.getLogger(__name__)


class Sentinel(BaseAgent):
    """
    L0 Collection Orchestration Agent.

    Watches for stale data sources and enqueues collection tasks.
    Publishes SIGNALS_COLLECTED events when collection completes.

    Config keys:
        stale_threshold_hours: int (default 4)
        sources: List[str] (default all configured sources)
        task_queue: TaskQueue instance for enqueueing
    """

    def __init__(
        self,
        event_bus: EventBus,
        db_path: str = DEFAULT_DB_PATH,
        task_queue: Optional[TaskQueue] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        config = config or {}
        super().__init__(
            name="sentinel",
            layer="L0",
            event_bus=event_bus,
            db_path=db_path,
            config=config,
        )
        self.task_queue = task_queue
        self.stale_threshold_hours = config.get("stale_threshold_hours", 4)
        self.sources = config.get("sources", [
            "yfinance",
            "reddit",
            "sec_edgar",
            "google_trends",
        ])
        self._active_collect_task: Optional[int] = None

        # Research mode: set by setup.py
        self.knowledge: Optional[KnowledgeStore] = None
        self.researcher: Optional[ResearchOrchestrator] = None

    def subscriptions(self) -> List[EventType]:
        """Watch for collection task completion."""
        return [EventType.TASK_COMPLETED, EventType.SOURCE_STALE]

    async def handle_event(self, event: Event):
        """
        React to task completion or stale source signals.
        If a collect task completed, publish SIGNALS_COLLECTED.
        If a source is explicitly marked stale, trigger immediate collection.
        """
        if event.type == EventType.TASK_COMPLETED:
            await self._on_task_completed(event)
        elif event.type == EventType.SOURCE_STALE:
            await self._on_source_stale(event)

    async def _on_task_completed(self, event: Event):
        """Handle a completed task. If it's our collect task, publish SIGNALS_COLLECTED."""
        payload = event.payload or {}
        task_id = payload.get("task_id")
        task_type = payload.get("task_type")

        # Only care about our collect tasks
        if task_id != self._active_collect_task or task_type != "collect":
            return

        self._active_collect_task = None

        result = payload.get("result", {})
        signal_count = result.get("signal_count", 0)
        source_results = result.get("source_results", {})
        sources_collected = list(source_results.keys())

        logger.info(
            f"Collection task completed: {signal_count} signals from {sources_collected}"
        )

        # Get list of symbols in the fresh signals
        symbols = self._get_symbols_from_recent_signals(db_path=self.db_path)

        await self.emit(
            EventType.SIGNALS_COLLECTED,
            {
                "signal_count": signal_count,
                "sources": sources_collected,
                "symbols": symbols,
                "task_id": task_id,
            },
        )

    async def _on_source_stale(self, event: Event):
        """Handle explicit stale source notification. Enqueue immediate collection."""
        payload = event.payload or {}
        stale_sources = payload.get("sources", [])

        if stale_sources:
            logger.info(f"Sentinel triggered by stale source event: {stale_sources}")
            await self._enqueue_collect(stale_sources)

    def adapt_params(self):
        """
        Adapt collection behavior based on pipeline conditions.

        High divergence pressure → collect more frequently (tick 15s)
        Signal velocity already high → back off (tick 120s)
        Hot symbols exist → prioritize their sources
        """
        if not self.ctx:
            return None

        pipeline = self.ctx.get_context()

        # Adapt tick interval: when divergence is spiking, collect faster
        # Combine divergence pressure + divergence velocity for urgency
        urgency = max(pipeline.divergence_pressure.value, pipeline.divergence_velocity.value)

        # But if signal velocity is already high, don't flood the pipeline
        # Reduce urgency when signals are flowing fast AND pipeline is backed up
        if pipeline.signal_velocity.value > 0.7 and pipeline.pipeline_throughput.value < 0.3:
            urgency *= 0.5  # Back off — plenty of signals, pipeline can't keep up

        new_tick = adapt(urgency, calm_value=120.0, urgent_value=15.0)
        self._tick_interval = max(10.0, new_tick)

        # Adapt stale threshold: when divergence is high, tolerate less staleness
        self.stale_threshold_hours = adapt(urgency, calm_value=6.0, urgent_value=1.5)

        # Prioritize sources that feed into hot symbols
        hot = pipeline.hot_symbols[:5]
        if hot:
            logger.debug(f"Sentinel: hot symbols = {[h['symbol'] for h in hot]}")

        adapted = {
            "tick_interval": round(self._tick_interval, 1),
            "stale_threshold_hours": round(self.stale_threshold_hours, 1),
            "urgency": round(urgency, 3),
            "signal_velocity": pipeline.signal_velocity.trend,
            "divergence_pressure": round(pipeline.divergence_pressure.value, 3),
        }
        self.metrics.last_adapted_params = adapted
        logger.info(f"Sentinel adapted: tick={adapted['tick_interval']}s, stale_threshold={adapted['stale_threshold_hours']}h")
        return adapted

    async def tick(self):
        """
        Periodic check (dynamically adapted interval).

        Two modes:
        1. Pipeline mode: check for stale sources, enqueue collection
        2. Research mode: when pipeline is idle, investigate gap_fill hypotheses
        """
        # Don't check if we have an active collect task
        if self._active_collect_task:
            logger.debug("Sentinel: collect task in progress, skipping tick")
            return

        stale_sources = self._get_stale_sources(
            threshold_hours=self.stale_threshold_hours,
            db_path=self.db_path,
        )

        if stale_sources:
            logger.info(f"Sentinel detected stale sources: {stale_sources}")
            await self._enqueue_collect(stale_sources)
        else:
            # Pipeline idle → enter research mode
            await self._research_tick()

    async def _research_tick(self):
        """
        Research mode: claim and investigate gap_fill hypotheses.
        Called when no stale sources need collection.
        """
        if not self.knowledge or not self.researcher:
            return

        # Generate gap hypotheses from hot symbols
        if self.ctx:
            pipeline = self.ctx.get_context()
            if pipeline.hot_symbols:
                self.researcher.generate_gap_hypotheses(pipeline.hot_symbols)

        # Claim and investigate a pending hypothesis
        hypothesis = self.knowledge.claim_hypothesis(
            agent_name="sentinel",
            question_types=["gap_fill"],
        )
        if hypothesis:
            logger.info(f"Sentinel researching: {hypothesis['hypothesis'][:80]}")
            try:
                result = self.researcher.investigate_hypothesis(hypothesis)
                self.knowledge.complete_hypothesis(hypothesis["id"], result)
                logger.info(f"Sentinel completed research hypothesis {hypothesis['id']}")
            except Exception as e:
                logger.error(f"Sentinel research failed: {e}")
                self.knowledge.complete_hypothesis(
                    hypothesis["id"], {"error": str(e)}, status="failed"
                )

    async def _enqueue_collect(self, sources: List[str]):
        """Enqueue a collect task for given sources."""
        if not self.task_queue:
            logger.warning("Sentinel: no task_queue configured, cannot enqueue")
            return

        if not sources:
            return

        task_id = await self.task_queue.enqueue(
            task_type="collect",
            params={
                "sources": sources,
                "symbols": None,  # None = all tracked symbols
                "domain": "public",
            },
            max_attempts=3,
        )

        self._active_collect_task = task_id
        logger.info(f"Sentinel enqueued collect task: id={task_id}, sources={sources}")

    @staticmethod
    def _get_stale_sources(
        threshold_hours: int = 4,
        db_path: str = DEFAULT_DB_PATH,
    ) -> List[str]:
        """
        Query signals table to find sources with no fresh data.
        Returns list of sources that haven't received signals in last N hours.
        """
        try:
            with get_connection(db_path) as conn:
                cursor = conn.execute(
                    """
                    SELECT DISTINCT source, MAX(timestamp) as latest_ts
                    FROM signals
                    GROUP BY source
                    """
                )
                source_rows = cursor.fetchall()

            stale = []
            now = datetime.now(timezone.utc)
            cutoff = now - timedelta(hours=threshold_hours)
            cutoff_iso = cutoff.isoformat()

            for row in source_rows:
                row_dict = dict(row)
                source = row_dict.get("source")
                latest_ts = row_dict.get("latest_ts")

                # Parse ISO string and compare
                if latest_ts and latest_ts < cutoff_iso:
                    stale.append(source)

            return stale

        except Exception as e:
            logger.error(f"Error querying stale sources: {e}")
            return []

    @staticmethod
    def _get_symbols_from_recent_signals(
        db_path: str = DEFAULT_DB_PATH,
        hours_back: int = 1,
    ) -> List[str]:
        """
        Get list of unique symbols from signals created in the last N hours.
        Used to track which symbols got fresh data.
        """
        try:
            with get_connection(db_path) as conn:
                cutoff = datetime.now(timezone.utc) - timedelta(hours=hours_back)
                cutoff_iso = cutoff.isoformat()

                ph = get_placeholder()
                cursor = conn.execute(
                    f"SELECT DISTINCT symbol FROM signals WHERE created_at > {ph}",
                    (cutoff_iso,),
                )
                symbols = [row[0] for row in cursor.fetchall()]
            return symbols
        except Exception as e:
            logger.error(f"Error querying recent symbols: {e}")
            return []
