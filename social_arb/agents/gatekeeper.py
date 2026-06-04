"""
Gatekeeper Agent — L3→L4 HITL Queue Management

This agent implements the Human-In-The-Loop decision layer of Camillo's
cognitive architecture: managing review queues, prioritizing theses for
human review, and detecting when reviews are submitted.

The agent:
1. Subscribes to THESES_FORGED and HITL_REQUIRED (review queue population)
2. Queries reviews table for pending reviews
3. Ranks by: lifecycle_stage urgency, divergence_strength, age
4. Auto-promotes autonomous reviews (trust_level='autonomous', score above threshold)
5. Polls for completed reviews, publishes DECISIONS_MADE when detected

Flow:
  THESES_FORGED (trigger)
    → Query reviews table for pending gate='L3_conviction'
    → Rank by lifecycle_stage (emerging > validating > confirmed > saturated)
    → Rank by divergence_strength and age
    → If trust_level='autonomous' AND total_score > threshold:
         auto_approve → create decision record
         → publish DECISIONS_MADE
    → Else: keep in queue for human review

  Periodic tick (review_poll_interval):
    → Query for completed reviews (decision != NULL)
    → For each completed review, create decision record
    → Publish DECISIONS_MADE

Config:
  auto_promote_threshold (float): Min total_score for autonomous promotion (default 15)
  review_poll_interval (int): Seconds between review polling (default 30)
"""

import json
import logging
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .base import BaseAgent
from .context import adapt
from .events import Event, EventType
from .knowledge import KnowledgeStore
from .researcher import ResearchOrchestrator

logger = logging.getLogger(__name__)


class GatekeeperAgent(BaseAgent):
    """
    L3→L4: Manage HITL review queue, rank by urgency, auto-promote when appropriate.

    Subscribes to THESES_FORGED, HITL_REQUIRED for queue population.
    Polls reviews table for completed decisions.
    Publishes DECISIONS_MADE when reviews complete or auto-promotions occur.
    """

    def __init__(self, name: str, event_bus, db_path: str, config: Optional[Dict[str, Any]] = None):
        super().__init__(
            name=name or "gatekeeper",
            layer="L3→L4",
            event_bus=event_bus,
            db_path=db_path,
            config=config or {},
        )
        self.auto_promote_threshold = self.config.get("auto_promote_threshold", 15.0)
        self._tick_interval = float(self.config.get("review_poll_interval", 30))

        # Research mode
        self.knowledge: Optional[KnowledgeStore] = None
        self.researcher: Optional[ResearchOrchestrator] = None

    def subscriptions(self) -> List[EventType]:
        """Listen for thesis forging and HITL requirements."""
        return [EventType.THESES_FORGED, EventType.HITL_REQUIRED]

    async def handle_event(self, event: Event):
        """
        React to THESES_FORGED or HITL_REQUIRED to manage the review queue.
        """
        if event.type in (EventType.THESES_FORGED, EventType.HITL_REQUIRED):
            await self._process_review_queue(event)

    def adapt_params(self):
        """
        Adapt HITL queue management based on pipeline conditions.

        Backlog growing → lower auto-promote threshold (more aggressive)
        Divergence spiking on emerging tickers → fast-track those reviews
        Pipeline bottleneck at gatekeeper → increase poll frequency
        """
        if not self.ctx:
            return None

        pipeline = self.ctx.get_context()

        # When backlog is high, lower auto-promote threshold to clear queue
        backlog_pressure = pipeline.hitl_backlog.value
        # calm=18 (strict), urgent=10 (permissive auto-promote)
        self.auto_promote_threshold = adapt(backlog_pressure, calm_value=18.0, urgent_value=10.0)

        # When we're the bottleneck, poll faster
        if pipeline.bottleneck_agent == "gatekeeper":
            self._tick_interval = adapt(pipeline.bottleneck_severity, calm_value=30.0, urgent_value=10.0)
        else:
            # Normal adaptation: faster polling when divergence is high
            self._tick_interval = adapt(
                pipeline.divergence_pressure.value, calm_value=45.0, urgent_value=15.0
            )

        adapted = {
            "auto_promote_threshold": round(self.auto_promote_threshold, 1),
            "tick_interval": round(self._tick_interval, 1),
            "backlog_pressure": round(backlog_pressure, 3),
            "is_bottleneck": pipeline.bottleneck_agent == "gatekeeper",
            "pending_reviews": pipeline.pending_review_count,
        }
        self.metrics.last_adapted_params = adapted
        logger.info(
            f"Gatekeeper adapted: auto_promote>={self.auto_promote_threshold:.0f}, "
            f"poll={self._tick_interval:.0f}s, backlog_pressure={backlog_pressure:.2f}"
        )
        return adapted

    async def tick(self):
        """
        Periodic poll: Check for completed reviews and publish DECISIONS_MADE.
        """
        logger.debug(f"Gatekeeper tick: polling for completed reviews")

        try:
            completed_reviews = self._query_completed_reviews()
            if not completed_reviews:
                return

            logger.info(f"Found {len(completed_reviews)} completed reviews")

            # Process each completed review
            decisions = []
            for review in completed_reviews:
                decision = self._convert_review_to_decision(review)
                if decision:
                    decisions.append(decision)
                    # Mark review as processed
                    self._mark_review_processed(review["id"])

            if decisions:
                await self.emit(
                    EventType.DECISIONS_MADE,
                    {
                        "count": len(decisions),
                        "decisions": decisions,
                        "source": "gatekeeper_poll",
                    },
                )

            # Research mode: when no completed reviews, investigate reinforcement hypotheses
            if not completed_reviews and self.knowledge and self.researcher:
                hypothesis = self.knowledge.claim_hypothesis(
                    agent_name="gatekeeper",
                    question_types=["reinforcement"],
                )
                if hypothesis:
                    logger.info(f"Gatekeeper researching: {hypothesis['hypothesis'][:80]}")
                    try:
                        result = self.researcher.investigate_hypothesis(hypothesis)
                        self.knowledge.complete_hypothesis(hypothesis["id"], result)
                    except Exception as re:
                        self.knowledge.complete_hypothesis(
                            hypothesis["id"], {"error": str(re)}, status="failed"
                        )

        except Exception as e:
            logger.error(f"Error in gatekeeper tick: {e}", exc_info=True)

    # ── Event Processing ───────────────────────────────────────

    async def _process_review_queue(self, event: Event):
        """
        When theses are forged or HITL requirements triggered,
        populate/update the review queue and check for auto-promotions.
        """
        payload = event.payload or {}
        gate = payload.get("gate", "L3_conviction")

        logger.info(f"Processing review queue for gate: {gate}")

        try:
            # Query pending reviews for this gate
            pending_reviews = self._query_pending_reviews(gate)
            logger.debug(f"Found {len(pending_reviews)} pending reviews for {gate}")

            # Rank by urgency
            ranked = self._rank_reviews_by_urgency(pending_reviews)

            # Check for auto-promotions
            auto_promoted = []
            for review in ranked:
                if self._should_auto_promote(review):
                    decision = self._auto_promote_review(review)
                    auto_promoted.append(decision)
                    logger.info(f"Auto-promoted review {review['id']} (score={review['total_score']})")

            if auto_promoted:
                await self.emit(
                    EventType.DECISIONS_MADE,
                    {
                        "count": len(auto_promoted),
                        "decisions": auto_promoted,
                        "source": "gatekeeper_auto_promote",
                        "gate": gate,
                    },
                )

            # Research: generate reinforcement hypotheses for non-auto-promoted reviews
            remaining = [r for r in ranked if not self._should_auto_promote(r)]
            if self.researcher and remaining:
                try:
                    self.researcher.generate_review_hypotheses(remaining[:5])
                except Exception as re:
                    logger.warning(f"Gatekeeper: review hypothesis generation failed: {re}")

        except Exception as e:
            logger.error(f"Error processing review queue: {e}", exc_info=True)
            raise

    # ── Database Queries ───────────────────────────────────────

    def _query_pending_reviews(self, gate: str) -> List[Dict[str, Any]]:
        """
        Fetch pending reviews for a given gate (decision IS NULL).
        Includes entity details and scores.
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            c = conn.cursor()

            c.execute("""
                SELECT id, gate, symbol, entity_id, entity_type,
                       scores_json, total_score, threshold, narrative,
                       dominant_narrative, market_pricing, invalidation,
                       position_size, risk_note, created_at
                FROM reviews
                WHERE gate = ? AND decision IS NULL
                ORDER BY created_at ASC
            """, (gate,))

            rows = c.fetchall()
            return [dict(row) for row in rows]

    def _query_completed_reviews(self) -> List[Dict[str, Any]]:
        """
        Fetch reviews with decisions that haven't been converted to DECISIONS_MADE yet.
        (Marked by a special field or checked by absence in decisions table)
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            c = conn.cursor()

            # Fetch reviews with decisions that don't yet have corresponding decision records
            c.execute("""
                SELECT id, gate, symbol, entity_id, entity_type,
                       scores_json, total_score, narrative,
                       dominant_narrative, market_pricing, invalidation,
                       decision, position_size, risk_note, created_at
                FROM reviews
                WHERE decision IS NOT NULL
                  AND id NOT IN (
                    SELECT entity_id FROM decisions WHERE entity_type = 'review'
                  )
                ORDER BY created_at ASC
            """)

            rows = c.fetchall()
            return [dict(row) for row in rows]

    def _mark_review_processed(self, review_id: int):
        """
        Create a placeholder decision record to mark review as processed.
        """
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            # Insert a record linking this review to decisions (prevent reprocessing)
            c.execute("""
                INSERT OR IGNORE INTO decisions (
                    thesis_id, gate, symbol, decision, trust_level, created_at
                )
                SELECT NULL, gate, symbol, decision, 'manual', created_at
                FROM reviews
                WHERE id = ?
            """, (review_id,))
            conn.commit()

    # ── Ranking & Scoring ──────────────────────────────────────

    def _rank_reviews_by_urgency(self, reviews: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Rank reviews by: lifecycle_stage urgency × divergence_velocity × age.
        Uses hot_symbols from context to boost reviews for trending tickers.
        Returns sorted list.
        """
        # Lifecycle stage urgency mapping
        lifecycle_urgency = {
            "emerging": 4,
            "validating": 3,
            "confirmed": 2,
            "saturated": 1,
        }

        # Get hot symbols from context for priority boost
        hot_symbol_scores = {}
        if self.ctx:
            pipeline = self.ctx.get_context()
            for h in pipeline.hot_symbols:
                hot_symbol_scores[h["symbol"]] = h["urgency_score"]

        def urgency_score(review):
            symbol = review.get("symbol", "")

            # Get lifecycle stage from thesis or entity
            lifecycle = review.get("lifecycle_stage", "validating")
            lifecycle_score = lifecycle_urgency.get(lifecycle, 2)

            # Divergence strength (infer from total_score or scores_json)
            divergence = review.get("total_score", 10)

            # Age penalty (older = higher priority)
            created_at = review.get("created_at", "")
            age_hours = 0
            if created_at:
                try:
                    created = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                    age_hours = (datetime.now(timezone.utc) - created).total_seconds() / 3600
                except:
                    age_hours = 0

            # Hot symbol boost: if this symbol is trending, it gets priority
            hot_boost = hot_symbol_scores.get(symbol, 0) * 2

            # Composite: lifecycle urgency (weight 3) + divergence + age bonus + hot boost
            return (lifecycle_score * 3) + divergence + (age_hours / 100) + hot_boost

        ranked = sorted(reviews, key=urgency_score, reverse=True)
        return ranked

    def _should_auto_promote(self, review: Dict[str, Any]) -> bool:
        """
        Auto-promote if: total_score >= threshold AND we have autonomous trust level.
        (Trust level inferred from theses' autonomous decision history)
        """
        total_score = review.get("total_score", 0)
        threshold = review.get("threshold", self.auto_promote_threshold)

        # Check if entity has autonomous trust records
        symbol = review.get("symbol")
        entity_id = review.get("entity_id")

        if total_score >= threshold:
            # Verify trust level by querying decisions for this entity
            trust_level = self._query_trust_level(symbol, entity_id)
            if trust_level == "autonomous":
                return True

        return False

    def _query_trust_level(self, symbol: str, entity_id: Optional[int]) -> str:
        """
        Infer trust level from recent decisions for this symbol/entity.
        Returns 'autonomous', 'supervised', or 'manual'.
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            c = conn.cursor()

            # Check recent decisions for this symbol
            c.execute("""
                SELECT trust_level
                FROM decisions
                WHERE symbol = ?
                ORDER BY created_at DESC
                LIMIT 5
            """, (symbol,))

            rows = c.fetchall()
            if not rows:
                return "manual"

            trust_levels = [row["trust_level"] for row in rows if row["trust_level"]]
            if not trust_levels:
                return "manual"

            # If majority are autonomous, return autonomous
            autonomous_count = sum(1 for tl in trust_levels if tl == "autonomous")
            if autonomous_count >= len(trust_levels) * 0.7:
                return "autonomous"

            return "supervised" if any(tl == "supervised" for tl in trust_levels) else "manual"

    def _auto_promote_review(self, review: Dict[str, Any]) -> Dict[str, Any]:
        """
        Auto-approve a review and return decision object.
        """
        decision_text = "auto_approve"
        confidence = min(review.get("total_score", 10) / 20.0, 1.0)  # Normalize to 0-1

        return {
            "review_id": review["id"],
            "thesis_id": review.get("entity_id"),
            "symbol": review["symbol"],
            "gate": review["gate"],
            "decision": decision_text,
            "confidence": confidence,
            "trust_level": "autonomous",
            "rationale": f"Auto-promoted: score={review['total_score']:.1f}, threshold={review['threshold']:.1f}",
        }

    def _convert_review_to_decision(self, review: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Convert a completed review to a decision record.
        """
        decision_text = review.get("decision")
        if not decision_text:
            return None

        return {
            "review_id": review["id"],
            "thesis_id": review.get("entity_id"),
            "symbol": review["symbol"],
            "gate": review["gate"],
            "decision": decision_text,
            "confidence": 0.8,  # Human-made decisions default to high confidence
            "trust_level": "manual",
            "rationale": review.get("narrative", ""),
        }
