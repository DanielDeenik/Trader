"""
Assembler Agent — L1→L2 Analysis Pipeline (Pattern Recognition)

Subscribes to: SIGNALS_COLLECTED
When fresh signals arrive, queries DB to find symbols with new signals since last analysis
Enqueues analyze task filtered to those symbols only
When analysis completes, publishes MOSAICS_ASSEMBLED with stats (mosaics_created, theses_created)
Also publishes HITL_REQUIRED if any mosaics need human review (action != 'pass')

Role: Converts raw signal fragments into mosaic patterns (L1) and investment theses (L2).
The Assembler is the pattern recognition layer — it finds coherence in noise.
"""

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from social_arb.db.schema import get_connection, DEFAULT_DB_PATH
from social_arb.db.adapter import get_placeholder
from social_arb.tasks.queue import TaskQueue

from .base import BaseAgent
from .context import adapt
from .events import Event, EventBus, EventType
from .knowledge import KnowledgeStore
from .researcher import ResearchOrchestrator

logger = logging.getLogger(__name__)


class Assembler(BaseAgent):
    """
    L1→L2 Analysis Pipeline Agent.

    Watches for fresh signals and enqueues analysis jobs.
    Publishes MOSAICS_ASSEMBLED and HITL_REQUIRED events.

    Config keys:
        min_signals_for_analysis: int (default 3) — minimum signals per symbol to trigger analysis
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
            name="assembler",
            layer="L1-L2",
            event_bus=event_bus,
            db_path=db_path,
            config=config,
        )
        self.task_queue = task_queue
        self.min_signals_for_analysis = config.get("min_signals_for_analysis", 3)
        self._active_analyze_task: Optional[int] = None
        self._last_analysis_at: Optional[datetime] = None

        # Research mode
        self.knowledge: Optional[KnowledgeStore] = None
        self.researcher: Optional[ResearchOrchestrator] = None

    def subscriptions(self) -> List[EventType]:
        """Watch for fresh signals and analysis task completion."""
        return [EventType.SIGNALS_COLLECTED, EventType.TASK_COMPLETED]

    async def handle_event(self, event: Event):
        """
        React to fresh signals or task completion.
        SIGNALS_COLLECTED: Find symbols with new signals and enqueue analysis.
        TASK_COMPLETED: If analysis finished, publish MOSAICS_ASSEMBLED and HITL_REQUIRED.
        """
        if event.type == EventType.SIGNALS_COLLECTED:
            await self._on_signals_collected(event)
        elif event.type == EventType.TASK_COMPLETED:
            await self._on_task_completed(event)

    async def _on_signals_collected(self, event: Event):
        """
        Fresh signals arrived. Adapt thresholds based on pipeline context,
        then find symbols with enough new signals and enqueue analysis.
        """
        # Adapt before processing
        if self.ctx:
            self._adapt_for_analysis()

        payload = event.payload or {}
        symbols_with_fresh_data = payload.get("symbols", [])

        if not symbols_with_fresh_data:
            logger.debug("Assembler: no symbols with fresh data, skipping analysis")
            return

        # Prioritize hot symbols from context if available
        if self.ctx:
            pipeline = self.ctx.get_context()
            hot_set = {h["symbol"] for h in pipeline.hot_symbols}
            # Put hot symbols first in the analysis queue
            hot_first = [s for s in symbols_with_fresh_data if s in hot_set]
            rest = [s for s in symbols_with_fresh_data if s not in hot_set]
            symbols_with_fresh_data = hot_first + rest

        # Filter to symbols that have enough signals
        symbols_to_analyze = self._filter_symbols_by_signal_count(
            symbols_with_fresh_data,
            min_count=self.min_signals_for_analysis,
            db_path=self.db_path,
        )

        if not symbols_to_analyze:
            logger.info(
                f"Assembler: no symbols meet min signal threshold ({self.min_signals_for_analysis})"
            )
            return

        logger.info(f"Assembler: analyzing {len(symbols_to_analyze)} symbols (threshold={self.min_signals_for_analysis})")
        await self._enqueue_analysis(symbols_to_analyze)

    def _adapt_for_analysis(self):
        """
        Adapt analysis thresholds based on pipeline conditions.

        Pipeline clear + many emerging signals → lower threshold (process eagerly)
        Pipeline backed up (mosaics waiting) → raise threshold (be selective)
        High divergence velocity → lower threshold (don't miss emerging trends)
        """
        pipeline = self.ctx.get_context()

        # When divergence is accelerating and lifecycle is fresh, cast a wider net
        eagerness = max(
            pipeline.divergence_velocity.value,
            pipeline.lifecycle_freshness.value,
        )

        # But if the pipeline is backed up, be more selective
        backpressure = pipeline.hitl_backlog.value
        if backpressure > 0.7:
            eagerness *= 0.5  # Halve eagerness when HITL queue is overloaded

        # Also back off if we're the identified bottleneck
        if pipeline.bottleneck_agent == "assembler":
            eagerness *= 0.3

        # Adapt min_signals: calm=5 (selective), urgent=2 (eager)
        self.min_signals_for_analysis = max(2, int(adapt(eagerness, calm_value=5, urgent_value=2)))

        adapted = {
            "min_signals": self.min_signals_for_analysis,
            "eagerness": round(eagerness, 3),
            "backpressure": round(backpressure, 3),
            "is_bottleneck": pipeline.bottleneck_agent == "assembler",
        }
        self.metrics.last_adapted_params = adapted
        logger.info(f"Assembler adapted: min_signals={self.min_signals_for_analysis}, eagerness={eagerness:.2f}")

    async def _on_task_completed(self, event: Event):
        """Handle completed analysis task. Publish MOSAICS_ASSEMBLED and check for HITL."""
        payload = event.payload or {}
        task_id = payload.get("task_id")
        task_type = payload.get("task_type")

        # Only care about our analyze tasks
        if task_id != self._active_analyze_task or task_type != "analyze":
            return

        self._active_analyze_task = None
        self._last_analysis_at = datetime.now(timezone.utc)

        result = payload.get("result", {})
        analyzed_count = result.get("analyzed_count", 0)
        mosaic_count = result.get("mosaic_count", 0)
        thesis_count = result.get("thesis_count", 0)
        errors = result.get("errors", [])

        logger.info(
            f"Analysis task completed: {analyzed_count} symbols analyzed, "
            f"{mosaic_count} mosaics, {thesis_count} theses"
        )

        # Publish MOSAICS_ASSEMBLED event
        await self.emit(
            EventType.MOSAICS_ASSEMBLED,
            {
                "mosaics_created": mosaic_count,
                "theses_created": thesis_count,
                "symbols_analyzed": analyzed_count,
                "task_id": task_id,
                "errors": errors,
            },
        )

        # Check if any mosaics need human review
        mosaics_for_hitl = self._get_mosaics_requiring_review(db_path=self.db_path)
        if mosaics_for_hitl:
            logger.info(f"Assembler: {len(mosaics_for_hitl)} mosaics require HITL review")
            await self.emit(
                EventType.HITL_REQUIRED,
                {
                    "gate": "mosaic_review",
                    "mosaics": mosaics_for_hitl,
                    "count": len(mosaics_for_hitl),
                },
            )

        # Research mode: generate correlation hypotheses from analyzed symbols
        symbols = payload.get("symbols", [])
        if self.researcher and symbols:
            try:
                self.researcher.generate_correlation_hypotheses(symbols[:20])
            except Exception as e:
                logger.warning(f"Assembler: correlation hypothesis generation failed: {e}")

    async def _enqueue_analysis(self, symbols: List[str]):
        """Enqueue an analyze task for given symbols."""
        if not self.task_queue:
            logger.warning("Assembler: no task_queue configured, cannot enqueue")
            return

        if not symbols:
            return

        task_id = await self.task_queue.enqueue(
            task_type="analyze",
            params={
                "symbols": symbols,
            },
            max_attempts=3,
        )

        self._active_analyze_task = task_id
        logger.info(f"Assembler enqueued analyze task: id={task_id}, symbols={symbols}")

    @staticmethod
    def _filter_symbols_by_signal_count(
        symbols: List[str],
        min_count: int = 3,
        db_path: str = DEFAULT_DB_PATH,
    ) -> List[str]:
        """
        Filter symbols to only those with >= min_count recent signals.
        "Recent" = signals created in last hour.
        """
        if not symbols:
            return []

        try:
            with get_connection(db_path) as conn:
                ph = get_placeholder()
                cutoff = datetime.now(timezone.utc) - timedelta(hours=1)
                cutoff_iso = cutoff.isoformat()

                # Build query for signal counts
                placeholders = ", ".join([ph] * len(symbols))
                cursor = conn.execute(
                    f"""
                    SELECT symbol, COUNT(*) as signal_count
                    FROM signals
                    WHERE created_at > {ph}
                    AND symbol IN ({placeholders})
                    GROUP BY symbol
                    HAVING COUNT(*) >= {ph}
                    """,
                    [cutoff_iso] + symbols + [min_count],
                )

                result_symbols = [row[0] for row in cursor.fetchall()]
            return result_symbols

        except Exception as e:
            logger.error(f"Error filtering symbols by signal count: {e}")
            return []

    @staticmethod
    def _get_mosaics_requiring_review(
        db_path: str = DEFAULT_DB_PATH,
    ) -> List[Dict[str, Any]]:
        """
        Query mosaics where action != 'pass' (i.e., action is 'build_thesis' or 'investigate').
        These require human review at the HITL gate.
        """
        try:
            with get_connection(db_path) as conn:
                ph = get_placeholder()
                cursor = conn.execute(
                    f"""
                    SELECT id, symbol, domain, action, coherence_score, divergence_strength, narrative
                    FROM mosaics
                    WHERE action != {ph}
                    ORDER BY created_at DESC
                    LIMIT 100
                    """,
                    ("pass",),
                )

                mosaics = []
                for row in cursor.fetchall():
                    row_dict = dict(row)
                    mosaics.append(row_dict)

            return mosaics

        except Exception as e:
            logger.error(f"Error querying mosaics for HITL review: {e}")
            return []
