"""
Executor Agent — L4→L5 Position Lifecycle Management

This agent implements the execution layer of Camillo's cognitive architecture:
translating approved theses into open positions, monitoring position validity,
and managing position exit signals based on lifecycle stage changes.

The agent:
1. Subscribes to DECISIONS_MADE (position entry trigger)
2. On 'execute' or 'promote' decisions: creates position records
3. Periodic tick (120s): checks open positions for invalidation & lifecycle regression
4. Publishes POSITIONS_UPDATED when positions change

Flow:
  DECISIONS_MADE (trigger with decision='execute' or 'promote')
    → Check if position already exists for symbol
    → If not, create position record (status='open') with:
         - thesis_id, symbol, domain, direction, allocation_pct, conviction
         - entry_price (from current OHLCV), entry_date
    → Publish POSITIONS_UPDATED

  Periodic tick (120s):
    → Query open positions
    → For each position:
         1. Check if thesis is invalidated (status='invalidated')
            → Close position (status='closed', exit_price, pnl)
            → Publish POSITIONS_UPDATED
         2. Check lifecycle_stage regression (confirmed → saturated)
            → Exit signal
            → Close position with exit signal rationale
            → Publish POSITIONS_UPDATED
    → Check if open position count >= max_positions
         → Warn or enforce allocation limits

Config:
  max_positions (int): Maximum concurrent open positions (default 10)
  max_allocation_pct (float): Max allocation per position (default 5.0)
"""

import json
import logging
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .base import BaseAgent
from .context import adapt
from .events import Event, EventType

logger = logging.getLogger(__name__)


class ExecutorAgent(BaseAgent):
    """
    L4→L5: Open/close positions based on decisions, monitor for invalidation
    and lifecycle regression, manage position lifecycle.

    Subscribes to DECISIONS_MADE for entry signals.
    Periodic tick: checks open positions for exit conditions.
    Publishes POSITIONS_UPDATED when positions change.
    """

    def __init__(self, name: str, event_bus, db_path: str, config: Optional[Dict[str, Any]] = None):
        super().__init__(
            name=name or "executor",
            layer="L4→L5",
            event_bus=event_bus,
            db_path=db_path,
            config=config or {},
        )
        self.max_positions = self.config.get("max_positions", 10)
        self.max_allocation_pct = self.config.get("max_allocation_pct", 5.0)
        self._tick_interval = 120.0  # Fixed 120s per spec

    def subscriptions(self) -> List[EventType]:
        """Listen for approved decisions to execute positions."""
        return [EventType.DECISIONS_MADE]

    async def handle_event(self, event: Event):
        """
        React to DECISIONS_MADE: open positions for 'execute' or 'promote'.
        """
        payload = event.payload or {}
        decisions = payload.get("decisions", [])

        if not decisions:
            return

        logger.info(f"Processing {len(decisions)} decisions for position entry")

        opened = []
        for decision in decisions:
            decision_text = decision.get("decision")
            if decision_text in ("execute", "promote", "auto_approve"):
                position = await self._open_position_from_decision(decision)
                if position:
                    opened.append(position)

        if opened:
            logger.info(f"Opened {len(opened)} positions")
            await self.emit(
                EventType.POSITIONS_UPDATED,
                {
                    "action": "open",
                    "count": len(opened),
                    "positions": opened,
                    "source_event_id": event.event_id,
                },
            )

    def adapt_params(self):
        """
        Adapt position management based on portfolio and pipeline conditions.

        Portfolio heat high → tighten max allocation, increase monitoring
        Many positions showing lifecycle regression → faster tick cycle
        Divergence falling across portfolio → defensive posture
        """
        if not self.ctx:
            return None

        pipeline = self.ctx.get_context()

        # Tighten max allocation when portfolio is hot
        heat = pipeline.portfolio_heat.value
        self.max_allocation_pct = adapt(heat, calm_value=5.0, urgent_value=2.0)

        # Monitor more frequently when portfolio has many open positions
        # or when divergence is volatile
        monitoring_urgency = max(heat, pipeline.divergence_velocity.value)
        self._tick_interval = adapt(monitoring_urgency, calm_value=180.0, urgent_value=60.0)

        adapted = {
            "max_allocation_pct": round(self.max_allocation_pct, 2),
            "tick_interval": round(self._tick_interval, 1),
            "portfolio_heat": round(heat, 3),
            "open_positions": pipeline.open_position_count,
            "total_allocation": round(pipeline.total_allocation_pct, 2),
        }
        self.metrics.last_adapted_params = adapted
        logger.info(
            f"Executor adapted: max_alloc={self.max_allocation_pct:.1f}%, "
            f"tick={self._tick_interval:.0f}s, heat={heat:.2f}"
        )
        return adapted

    async def tick(self):
        """
        Periodic check (dynamically adapted): Monitor open positions for
        invalidation and lifecycle regression (exit signals).
        """
        logger.debug("Executor tick: monitoring open positions")

        try:
            open_positions = self._query_open_positions()
            if not open_positions:
                return

            logger.debug(f"Checking {len(open_positions)} open positions")

            closed = []
            for position in open_positions:
                exit_reason = self._check_exit_conditions(position)
                if exit_reason:
                    closed_pos = await self._close_position(position, exit_reason)
                    closed.append(closed_pos)

            if closed:
                logger.info(f"Closed {len(closed)} positions due to exit signals")
                await self.emit(
                    EventType.POSITIONS_UPDATED,
                    {
                        "action": "close",
                        "count": len(closed),
                        "positions": closed,
                        "source": "executor_tick",
                    },
                )

            # Check allocation limits
            self._check_allocation_limits(open_positions)

        except Exception as e:
            logger.error(f"Error in executor tick: {e}", exc_info=True)

    # ── Position Management ────────────────────────────────────

    async def _open_position_from_decision(self, decision: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Create position record from approved decision.
        Checks for duplicate positions and enforces allocation limits.
        """
        symbol = decision.get("symbol")
        thesis_id = decision.get("thesis_id")

        if not symbol or not thesis_id:
            logger.warning(f"Decision missing symbol or thesis_id: {decision}")
            return None

        # Check if position already exists
        if self._position_exists(symbol):
            logger.warning(f"Position already exists for {symbol}, skipping")
            return None

        # Check if we're at max positions
        open_count = self._count_open_positions()
        if open_count >= self.max_positions:
            logger.warning(f"Max positions ({self.max_positions}) reached, cannot open new position")
            return None

        # Fetch thesis details
        thesis = self._query_thesis(thesis_id)
        if not thesis:
            logger.error(f"Thesis {thesis_id} not found")
            return None

        # Get current price for entry
        entry_price = self._get_current_price(symbol)
        if not entry_price:
            logger.warning(f"Could not get current price for {symbol}")
            entry_price = None

        # Calculate allocation (capped at max_allocation_pct)
        allocation_pct = min(thesis.get("kelly_fraction", 2.0) * 100, self.max_allocation_pct)

        # Map conviction to text
        conviction_score = decision.get("confidence", 0.5)
        if conviction_score >= 0.8:
            conviction = "high"
        elif conviction_score >= 0.5:
            conviction = "medium"
        else:
            conviction = "low"

        # Create position record
        position = {
            "thesis_id": thesis_id,
            "symbol": symbol,
            "domain": thesis.get("domain", "public"),
            "direction": "long",
            "allocation_pct": allocation_pct,
            "conviction": conviction,
            "entry_price": entry_price,
            "entry_date": datetime.now(timezone.utc).isoformat(),
            "status": "open",
        }

        try:
            position_id = self._create_position_record(position)
            position["id"] = position_id
            logger.info(f"Created position {position_id}: {symbol} ({conviction}, {allocation_pct:.1f}%)")
            return position
        except Exception as e:
            logger.error(f"Error creating position: {e}")
            return None

    async def _close_position(
        self, position: Dict[str, Any], exit_reason: str
    ) -> Dict[str, Any]:
        """
        Close an open position with exit price and PnL calculation.
        """
        position_id = position["id"]
        symbol = position["symbol"]
        entry_price = position.get("entry_price")

        # Get current price for exit
        exit_price = self._get_current_price(symbol)
        if not exit_price:
            logger.warning(f"Could not get exit price for {symbol}, using entry price")
            exit_price = entry_price or 0

        # Calculate PnL
        pnl = None
        pnl_pct = None
        if entry_price and entry_price > 0:
            pnl = exit_price - entry_price
            pnl_pct = (pnl / entry_price) * 100

        exit_date = datetime.now(timezone.utc).isoformat()

        try:
            self._update_position_closed(
                position_id, exit_price, exit_date, pnl, pnl_pct, exit_reason
            )
            logger.info(
                f"Closed position {position_id} ({symbol}): {exit_reason}, "
                f"PnL={pnl_pct:.2f}%"
            )

            return {
                "id": position_id,
                "symbol": symbol,
                "exit_reason": exit_reason,
                "exit_price": exit_price,
                "exit_date": exit_date,
                "pnl": pnl,
                "pnl_pct": pnl_pct,
                "status": "closed",
            }
        except Exception as e:
            logger.error(f"Error closing position {position_id}: {e}")
            raise

    # ── Exit Condition Checks ──────────────────────────────────

    def _check_exit_conditions(self, position: Dict[str, Any]) -> Optional[str]:
        """
        Check if an open position should be closed.
        Returns exit reason if conditions met, else None.
        """
        thesis_id = position.get("thesis_id")

        # Condition 1: Thesis invalidated
        thesis = self._query_thesis(thesis_id)
        if thesis and thesis.get("status") == "invalidated":
            return "thesis_invalidated"

        # Condition 2: Lifecycle regression (confirmed → saturated)
        if thesis:
            lifecycle = thesis.get("lifecycle_stage", "validating")
            if lifecycle == "saturated":
                return "lifecycle_saturated"

        return None

    def _check_allocation_limits(self, open_positions: List[Dict[str, Any]]):
        """
        Check if total allocation exceeds limits and log warnings.
        """
        total_alloc = sum(p.get("allocation_pct", 0) for p in open_positions)
        if total_alloc > 100:
            logger.warning(
                f"Total allocation ({total_alloc:.1f}%) exceeds 100% "
                f"across {len(open_positions)} positions"
            )

    # ── Database Queries ───────────────────────────────────────

    def _query_open_positions(self) -> List[Dict[str, Any]]:
        """Fetch all open positions."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            c = conn.cursor()

            c.execute("""
                SELECT id, thesis_id, symbol, domain, direction, allocation_pct,
                       conviction, entry_price, entry_date, status
                FROM positions
                WHERE status = 'open'
                ORDER BY entry_date DESC
            """)

            rows = c.fetchall()
            return [dict(row) for row in rows]

    def _position_exists(self, symbol: str) -> bool:
        """Check if an open position already exists for symbol."""
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute("""
                SELECT 1 FROM positions
                WHERE symbol = ? AND status = 'open'
                LIMIT 1
            """, (symbol,))
            return c.fetchone() is not None

    def _count_open_positions(self) -> int:
        """Count open positions."""
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute("SELECT COUNT(*) as cnt FROM positions WHERE status = 'open'")
            return c.fetchone()[0]

    def _query_thesis(self, thesis_id: int) -> Optional[Dict[str, Any]]:
        """Fetch thesis details."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            c = conn.cursor()

            c.execute("""
                SELECT id, symbol, domain, kelly_fraction, roi_bear, roi_base, roi_bull,
                       status, lifecycle_stage
                FROM theses
                WHERE id = ?
            """, (thesis_id,))

            row = c.fetchone()
            return dict(row) if row else None

    def _get_current_price(self, symbol: str) -> Optional[float]:
        """
        Get current price from OHLCV table (latest close).
        """
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()

            c.execute("""
                SELECT close FROM ohlcv
                WHERE symbol = ?
                ORDER BY timestamp DESC
                LIMIT 1
            """, (symbol,))

            row = c.fetchone()
            return row[0] if row else None

    def _create_position_record(self, position: Dict[str, Any]) -> int:
        """Insert position record and return ID."""
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()

            c.execute("""
                INSERT INTO positions (
                    thesis_id, symbol, domain, direction, allocation_pct,
                    conviction, entry_price, entry_date, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                position["thesis_id"],
                position["symbol"],
                position["domain"],
                position.get("direction", "long"),
                position["allocation_pct"],
                position["conviction"],
                position.get("entry_price"),
                position["entry_date"],
                position["status"],
            ))

            conn.commit()
            return c.lastrowid

    def _update_position_closed(
        self,
        position_id: int,
        exit_price: float,
        exit_date: str,
        pnl: Optional[float],
        pnl_pct: Optional[float],
        exit_reason: str,
    ):
        """Update position to closed status with exit details."""
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()

            c.execute("""
                UPDATE positions
                SET status = 'closed',
                    exit_price = ?,
                    exit_date = ?,
                    pnl = ?,
                    pnl_pct = ?
                WHERE id = ?
            """, (exit_price, exit_date, pnl, pnl_pct, position_id))

            # Log to audit trail
            c.execute("""
                INSERT INTO audit_trail (layer, action, symbol, actor, details_json)
                SELECT 'L4→L5', 'position_closed', symbol, 'system',
                       ?
                FROM positions
                WHERE id = ?
            """, (
                json.dumps({"exit_reason": exit_reason, "pnl_pct": pnl_pct}),
                position_id,
            ))

            conn.commit()
