"""
Strategist Agent — L2→L3 Thesis Generation (Divergence + Conviction)

This agent implements Layer 3 of Camillo's cognitive architecture:
the transformation of mosaics (L2: assembled signals) into investment theses
with conviction scoring based on coherence and Kelly fraction.

The agent:
1. Subscribes to MOSAICS_ASSEMBLED and DECISIONS_MADE (feedback loop)
2. Queries for mosaics with action='build_thesis' lacking theses
3. Verifies theses were created by the analysis pipeline
4. Scores theses by conviction (kelly_fraction × coherence_score)
5. Publishes THESES_FORGED (ranked) and HITL_REQUIRED (for review gates)

Flow:
  MOSAICS_ASSEMBLED (trigger)
    → Query mosaics table for action='build_thesis' without theses
    → Verify theses exist in DB (created by pipeline.py)
    → Score/rank by conviction
    → Publish THESES_FORGED with ranked list
    → Publish HITL_REQUIRED for theses needing L3_conviction gate review

Feedback loop:
  DECISIONS_MADE (trigger)
    → Allows strategist to refine theses based on human feedback
"""

import json
import logging
import sqlite3
from typing import Any, Dict, List, Optional

from .base import BaseAgent
from .context import adapt
from .events import Event, EventType
from .knowledge import KnowledgeStore
from .researcher import ResearchOrchestrator

logger = logging.getLogger(__name__)


class StrategistAgent(BaseAgent):
    """
    L2→L3: Transform mosaics into ranked theses with conviction scoring.

    Config:
      min_coherence (float): Minimum coherence score to consider (default 0.5)
      min_kelly (float): Minimum kelly_fraction to rank (default 0.02)
    """

    def __init__(self, name: str, event_bus, db_path: str, config: Optional[Dict[str, Any]] = None):
        super().__init__(
            name=name or "strategist",
            layer="L2→L3",
            event_bus=event_bus,
            db_path=db_path,
            config=config or {},
        )
        self.min_coherence = self.config.get("min_coherence", 0.5)
        self.min_kelly = self.config.get("min_kelly", 0.02)

        # Research mode
        self.knowledge: Optional[KnowledgeStore] = None
        self.researcher: Optional[ResearchOrchestrator] = None

    def subscriptions(self) -> List[EventType]:
        """Listen for mosaic assembly and decision feedback."""
        return [EventType.MOSAICS_ASSEMBLED, EventType.DECISIONS_MADE]

    async def handle_event(self, event: Event):
        """
        React to MOSAICS_ASSEMBLED (primary) or DECISIONS_MADE (feedback).
        """
        if event.type == EventType.MOSAICS_ASSEMBLED:
            await self._process_assembled_mosaics(event)
        elif event.type == EventType.DECISIONS_MADE:
            await self._process_decision_feedback(event)

    def adapt_params(self):
        """
        Adapt conviction thresholds based on pipeline conditions.

        Portfolio skews confirmed/saturated + fresh emerging signals → widen net
        Pipeline already pushing many theses → tighten filter
        High divergence pressure → lower coherence threshold to catch early
        """
        if not self.ctx:
            return None

        pipeline = self.ctx.get_context()

        # When lifecycle is fresh (many emerging) and divergence is high,
        # lower thresholds to let more through
        opportunity = max(
            pipeline.lifecycle_freshness.value,
            pipeline.divergence_pressure.value,
        )

        # But when HITL is already overloaded, tighten
        if pipeline.hitl_backlog.value > 0.7:
            opportunity *= 0.4

        # Adapt coherence threshold: calm=0.6 (strict), urgent=0.3 (wider net)
        self.min_coherence = adapt(opportunity, calm_value=0.6, urgent_value=0.3)

        # Adapt kelly threshold: calm=0.05 (strict), urgent=0.01 (more permissive)
        self.min_kelly = adapt(opportunity, calm_value=0.05, urgent_value=0.01)

        adapted = {
            "min_coherence": round(self.min_coherence, 3),
            "min_kelly": round(self.min_kelly, 4),
            "opportunity": round(opportunity, 3),
            "lifecycle_freshness": round(pipeline.lifecycle_freshness.value, 3),
            "hitl_backlog": round(pipeline.hitl_backlog.value, 3),
        }
        self.metrics.last_adapted_params = adapted
        logger.info(f"Strategist adapted: coherence>={self.min_coherence:.2f}, kelly>={self.min_kelly:.3f}")
        return adapted

    async def _process_assembled_mosaics(self, event: Event):
        """
        Main flow: Query for mosaics with action='build_thesis', verify theses
        exist, score by conviction, and publish THESES_FORGED.
        """
        # Adapt before processing
        if self.ctx:
            adapted = self.adapt_params()
            if adapted:
                self.metrics.last_adapted_params = adapted

        logger.info(f"Processing assembled mosaics from {event.source_agent}")

        try:
            # Query mosaics marked for thesis building
            mosaics = self._query_mosaics_to_forge()
            if not mosaics:
                logger.debug("No mosaics with action='build_thesis' found")
                return

            logger.info(f"Found {len(mosaics)} mosaics to forge into theses")

            theses = []
            for mosaic in mosaics:
                thesis = self._forge_thesis_from_mosaic(mosaic)
                if thesis:
                    theses.append(thesis)

            if not theses:
                logger.debug("No theses created after processing mosaics")
                return

            # Score and rank by conviction
            ranked_theses = self._score_and_rank_theses(theses)

            logger.info(f"Forged {len(ranked_theses)} theses with conviction scores")

            # Publish THESES_FORGED event with ranked list
            await self.emit(
                EventType.THESES_FORGED,
                {
                    "count": len(ranked_theses),
                    "theses": ranked_theses,
                    "source_event_id": event.event_id,
                },
            )

            # Identify theses requiring HITL review and publish HITL_REQUIRED
            await self._publish_hitl_requirements(ranked_theses, event.event_id)

            # Research mode: generate thesis-based hypotheses
            if self.researcher and ranked_theses:
                try:
                    self.researcher.generate_thesis_hypotheses(ranked_theses)
                except Exception as re:
                    logger.warning(f"Strategist: thesis hypothesis generation failed: {re}")

        except Exception as e:
            logger.error(f"Error processing mosaics: {e}", exc_info=True)
            raise

    async def _process_decision_feedback(self, event: Event):
        """
        Feedback loop: React to human decisions to refine thesis status.
        """
        logger.debug(f"Processing decision feedback from {event.source_agent}")

        payload = event.payload or {}
        decisions = payload.get("decisions", [])

        if not decisions:
            return

        # Update thesis status based on decision feedback
        for decision in decisions:
            thesis_id = decision.get("thesis_id")
            decision_text = decision.get("decision")
            confidence = decision.get("confidence", 0)

            if not thesis_id:
                continue

            # Map decision to thesis status
            if decision_text == "approve":
                status = "approved"
            elif decision_text == "reject":
                status = "rejected"
            elif decision_text in ("defer", "defer"):
                status = "deferred"
            else:
                status = "pending_review"

            try:
                self._update_thesis_status(thesis_id, status, confidence)
                logger.info(f"Updated thesis {thesis_id} status to {status}")
            except Exception as e:
                logger.error(f"Error updating thesis {thesis_id}: {e}")

    # ── Database Queries ───────────────────────────────────────

    def _query_mosaics_to_forge(self) -> List[Dict[str, Any]]:
        """
        Fetch mosaics with action='build_thesis' that lack theses.
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            c = conn.cursor()

            c.execute("""
                SELECT m.id, m.symbol, m.domain, m.coherence_score,
                       m.divergence_strength, m.fragments_json, m.narrative
                FROM mosaics m
                WHERE m.action = 'build_thesis'
                  AND NOT EXISTS (
                    SELECT 1 FROM theses t WHERE t.mosaic_id = m.id
                  )
                ORDER BY m.coherence_score DESC, m.divergence_strength DESC
            """)

            rows = c.fetchall()
            return [dict(row) for row in rows]

    def _forge_thesis_from_mosaic(self, mosaic: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Verify a thesis exists for this mosaic (created by pipeline.py),
        and return its details with conviction scoring data attached.
        """
        mosaic_id = mosaic["id"]
        symbol = mosaic["symbol"]
        domain = mosaic["domain"]

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            c = conn.cursor()

            # Check if thesis already exists for this mosaic
            c.execute("""
                SELECT id, kelly_fraction, roi_bear, roi_base, roi_bull,
                       risk_assessment, lifecycle_stage, status
                FROM theses
                WHERE mosaic_id = ?
                ORDER BY id DESC
                LIMIT 1
            """, (mosaic_id,))

            thesis_row = c.fetchone()
            if not thesis_row:
                logger.debug(f"No thesis found for mosaic {mosaic_id}; skipping")
                return None

            thesis = dict(thesis_row)
            thesis["mosaic_id"] = mosaic_id
            thesis["symbol"] = symbol
            thesis["domain"] = domain
            thesis["coherence_score"] = mosaic["coherence_score"]
            thesis["divergence_strength"] = mosaic["divergence_strength"]

            return thesis

    def _score_and_rank_theses(self, theses: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Score theses by conviction: kelly_fraction × coherence_score.
        Filter by min_coherence and min_kelly, then rank by conviction.
        """
        scored = []

        for thesis in theses:
            coherence = thesis.get("coherence_score", 0.5)
            kelly = thesis.get("kelly_fraction", 0.02)

            # Apply filters
            if coherence < self.min_coherence or kelly < self.min_kelly:
                logger.debug(
                    f"Thesis {thesis['id']} filtered: coherence={coherence}, kelly={kelly}"
                )
                continue

            conviction = kelly * coherence
            thesis["conviction_score"] = conviction

            scored.append(thesis)

        # Rank by conviction (descending)
        scored.sort(key=lambda t: t["conviction_score"], reverse=True)

        return scored

    async def _publish_hitl_requirements(self, theses: List[Dict[str, Any]], event_id: str):
        """
        Identify theses requiring L3_conviction gate review and publish HITL_REQUIRED.
        """
        hitl_required = []

        for thesis in theses:
            conviction = thesis.get("conviction_score", 0)
            status = thesis.get("status", "pending_review")

            # Theses pending review need L3_conviction gate
            if status == "pending_review":
                hitl_required.append({
                    "thesis_id": thesis["id"],
                    "symbol": thesis["symbol"],
                    "domain": thesis["domain"],
                    "conviction_score": conviction,
                    "gate": "L3_conviction",
                    "kelly_fraction": thesis.get("kelly_fraction", 0),
                    "coherence_score": thesis.get("coherence_score", 0),
                })

        if hitl_required:
            logger.info(f"Publishing HITL_REQUIRED for {len(hitl_required)} theses")
            await self.emit(
                EventType.HITL_REQUIRED,
                {
                    "gate": "L3_conviction",
                    "count": len(hitl_required),
                    "theses": hitl_required,
                    "source_event_id": event_id,
                },
            )

    def _update_thesis_status(self, thesis_id: int, status: str, confidence: float = 0):
        """
        Update thesis status based on human decision feedback.
        """
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute("""
                UPDATE theses
                SET status = ?
                WHERE id = ?
            """, (status, thesis_id))
            conn.commit()
