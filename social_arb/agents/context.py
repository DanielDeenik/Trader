"""
ContextLayer — Real-time pipeline intelligence for adaptive agent behavior.

Every agent queries the ContextLayer before acting. Instead of static thresholds
and fixed timers, agents read data conditions and adapt:

  - Signal velocity rising → Sentinel collects faster, Assembler processes eagerly
  - Divergence spiking → Gatekeeper fast-tracks reviews, Strategist lowers thresholds
  - Pipeline backed up → Assembler batches larger, Sentinel backs off
  - Portfolio hot → Executor tightens limits, monitors more frequently

The ContextLayer computes pressure metrics from real DB state. It's not AI —
it's just smart SQL queries that give agents situational awareness.

Pressure Model:
  Each metric has a `pressure` value from 0.0 to 1.0:
    0.0 = calm, use default/relaxed parameters
    0.5 = normal, standard behavior
    1.0 = urgent, maximum adaptation

  Agents map pressure to their specific parameters using linear interpolation
  between their min/max config bounds.
"""

import logging
import sqlite3
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class PressureMetric:
    """A single pressure reading with context."""
    value: float           # 0.0 to 1.0
    raw: float             # The raw measurement before normalization
    label: str             # Human-readable description
    trend: str = "stable"  # "rising", "falling", "stable"


@dataclass
class PipelineContext:
    """
    Full pipeline context snapshot. Agents read this to adapt behavior.

    Computed fresh every time an agent asks (with short TTL caching).
    """
    # Signal flow
    signal_velocity: PressureMetric = field(default_factory=lambda: PressureMetric(0.5, 0, "signal velocity"))
    source_diversity: PressureMetric = field(default_factory=lambda: PressureMetric(0.5, 0, "source diversity"))

    # Divergence state
    divergence_pressure: PressureMetric = field(default_factory=lambda: PressureMetric(0.5, 0, "divergence pressure"))
    divergence_velocity: PressureMetric = field(default_factory=lambda: PressureMetric(0.5, 0, "divergence velocity"))

    # Lifecycle distribution
    emerging_count: int = 0
    validating_count: int = 0
    confirmed_count: int = 0
    saturated_count: int = 0
    lifecycle_freshness: PressureMetric = field(default_factory=lambda: PressureMetric(0.5, 0, "lifecycle freshness"))

    # Pipeline throughput
    pipeline_throughput: PressureMetric = field(default_factory=lambda: PressureMetric(0.5, 0, "pipeline throughput"))
    conversion_rate: float = 0.0  # signals→theses conversion

    # HITL queue
    hitl_backlog: PressureMetric = field(default_factory=lambda: PressureMetric(0.5, 0, "hitl backlog"))
    pending_review_count: int = 0

    # Portfolio state
    portfolio_heat: PressureMetric = field(default_factory=lambda: PressureMetric(0.5, 0, "portfolio heat"))
    open_position_count: int = 0
    total_allocation_pct: float = 0.0

    # Bottleneck detection
    bottleneck_agent: Optional[str] = None
    bottleneck_severity: float = 0.0

    # Top symbols by urgency (agents use this to prioritize)
    hot_symbols: List[Dict[str, Any]] = field(default_factory=list)

    # Timestamp
    computed_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize for API/dashboard."""
        def _pm(pm: PressureMetric) -> Dict:
            return {"value": round(pm.value, 3), "raw": round(pm.raw, 3), "label": pm.label, "trend": pm.trend}

        return {
            "signal_velocity": _pm(self.signal_velocity),
            "source_diversity": _pm(self.source_diversity),
            "divergence_pressure": _pm(self.divergence_pressure),
            "divergence_velocity": _pm(self.divergence_velocity),
            "lifecycle": {
                "emerging": self.emerging_count,
                "validating": self.validating_count,
                "confirmed": self.confirmed_count,
                "saturated": self.saturated_count,
                "freshness": _pm(self.lifecycle_freshness),
            },
            "pipeline_throughput": _pm(self.pipeline_throughput),
            "conversion_rate": round(self.conversion_rate, 4),
            "hitl_backlog": _pm(self.hitl_backlog),
            "pending_review_count": self.pending_review_count,
            "portfolio": {
                "heat": _pm(self.portfolio_heat),
                "open_positions": self.open_position_count,
                "total_allocation_pct": round(self.total_allocation_pct, 2),
            },
            "bottleneck": {
                "agent": self.bottleneck_agent,
                "severity": round(self.bottleneck_severity, 3),
            },
            "hot_symbols": self.hot_symbols[:10],
            "computed_at": self.computed_at.isoformat() if self.computed_at else None,
        }


class ContextLayer:
    """
    Shared service that computes real-time pipeline context from DB state.

    All agents receive a reference to this at construction. When they need
    to adapt behavior, they call `get_context()` which returns a cached
    PipelineContext snapshot (refreshed every `ttl_seconds`).

    No AI, no LLM calls — just SQL queries that measure data conditions.
    """

    def __init__(self, db_path: str, ttl_seconds: float = 10.0):
        self.db_path = db_path
        self.ttl_seconds = ttl_seconds
        self._cache: Optional[PipelineContext] = None
        self._cache_time: float = 0.0

        # Configurable normalization bounds
        # These define what "calm" and "urgent" look like for each metric
        self._bounds = {
            # signal_velocity: signals per hour. 0-10 = calm, 100+ = urgent
            "signal_velocity": (10.0, 100.0),
            # source_diversity: unique sources active in last 4h. 1 = calm, 6+ = full
            "source_diversity": (1.0, 6.0),
            # divergence: count of symbols with divergence > 0.15. 0 = calm, 10+ = urgent
            "divergence_count": (0.0, 10.0),
            # hitl backlog: pending reviews. 0 = calm, 15+ = urgent
            "hitl_backlog": (0.0, 15.0),
            # portfolio heat: total allocation %. 0 = calm, 50+ = urgent
            "portfolio_heat": (0.0, 50.0),
            # pipeline throughput: theses generated per 24h. 0 = stalled, 10+ = healthy
            "throughput": (0.0, 10.0),
        }

    def get_context(self) -> PipelineContext:
        """
        Get the current pipeline context. Returns cached version if fresh enough.
        """
        now = time.monotonic()
        if self._cache and (now - self._cache_time) < self.ttl_seconds:
            return self._cache

        ctx = self._compute_context()
        self._cache = ctx
        self._cache_time = now
        return ctx

    def invalidate(self):
        """Force next get_context() to recompute."""
        self._cache = None

    def _compute_context(self) -> PipelineContext:
        """
        Run all context queries against the DB and build a PipelineContext.
        """
        ctx = PipelineContext(computed_at=datetime.now(timezone.utc))

        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row

                self._compute_signal_velocity(conn, ctx)
                self._compute_divergence_pressure(conn, ctx)
                self._compute_lifecycle_distribution(conn, ctx)
                self._compute_pipeline_throughput(conn, ctx)
                self._compute_hitl_backlog(conn, ctx)
                self._compute_portfolio_heat(conn, ctx)
                self._compute_hot_symbols(conn, ctx)
                self._detect_bottleneck(conn, ctx)

        except Exception as e:
            logger.error(f"ContextLayer: error computing context: {e}", exc_info=True)

        return ctx

    # ── Signal Flow ───────────────────────────────────────────

    def _compute_signal_velocity(self, conn: sqlite3.Connection, ctx: PipelineContext):
        """
        Measure signal ingestion rate: signals per hour over last 4 hours,
        compared to the previous 4-hour window. Determines trend direction.
        """
        now = datetime.now(timezone.utc)
        recent_cutoff = (now - timedelta(hours=4)).isoformat()
        prev_cutoff = (now - timedelta(hours=8)).isoformat()

        # Recent window (last 4h)
        row = conn.execute(
            "SELECT COUNT(*) as cnt FROM signals WHERE timestamp > ?",
            (recent_cutoff,),
        ).fetchone()
        recent_count = row["cnt"] if row else 0
        recent_rate = recent_count / 4.0  # per hour

        # Previous window (4-8h ago)
        row = conn.execute(
            "SELECT COUNT(*) as cnt FROM signals WHERE timestamp > ? AND timestamp <= ?",
            (prev_cutoff, recent_cutoff),
        ).fetchone()
        prev_count = row["cnt"] if row else 0
        prev_rate = prev_count / 4.0

        # Trend detection
        if prev_rate > 0:
            change_ratio = recent_rate / prev_rate
            if change_ratio > 1.3:
                trend = "rising"
            elif change_ratio < 0.7:
                trend = "falling"
            else:
                trend = "stable"
        else:
            trend = "rising" if recent_rate > 0 else "stable"

        lo, hi = self._bounds["signal_velocity"]
        pressure = self._normalize(recent_rate, lo, hi)

        ctx.signal_velocity = PressureMetric(
            value=pressure, raw=recent_rate,
            label=f"{recent_rate:.0f} signals/hr", trend=trend,
        )

        # Source diversity: unique sources in last 4h
        row = conn.execute(
            "SELECT COUNT(DISTINCT source) as cnt FROM signals WHERE timestamp > ?",
            (recent_cutoff,),
        ).fetchone()
        source_count = row["cnt"] if row else 0
        lo, hi = self._bounds["source_diversity"]
        ctx.source_diversity = PressureMetric(
            value=self._normalize(source_count, lo, hi),
            raw=source_count,
            label=f"{source_count} active sources",
            trend="stable",
        )

    # ── Divergence Pressure ───────────────────────────────────

    def _compute_divergence_pressure(self, conn: sqlite3.Connection, ctx: PipelineContext):
        """
        Count symbols with divergence > threshold and measure if divergence
        is accelerating (comparing recent mosaics vs older ones).
        """
        # Symbols with high divergence in recent mosaics
        row = conn.execute("""
            SELECT COUNT(DISTINCT symbol) as cnt
            FROM mosaics
            WHERE (divergence_strength > 15 OR (divergence_strength > 0.15 AND divergence_strength <= 1.0))
        """).fetchone()
        high_div_count = row["cnt"] if row else 0

        lo, hi = self._bounds["divergence_count"]
        ctx.divergence_pressure = PressureMetric(
            value=self._normalize(high_div_count, lo, hi),
            raw=high_div_count,
            label=f"{high_div_count} high-divergence symbols",
            trend="stable",
        )

        # Divergence velocity: compare average divergence of mosaics created
        # in last 24h vs previous 24h
        now = datetime.now(timezone.utc)
        recent = (now - timedelta(hours=24)).isoformat()
        prev = (now - timedelta(hours=48)).isoformat()

        row_recent = conn.execute(
            "SELECT AVG(divergence_strength) as avg_div FROM mosaics WHERE created_at > ?",
            (recent,),
        ).fetchone()
        row_prev = conn.execute(
            "SELECT AVG(divergence_strength) as avg_div FROM mosaics WHERE created_at > ? AND created_at <= ?",
            (prev, recent),
        ).fetchone()

        avg_recent = (row_recent["avg_div"] or 0)
        avg_prev = (row_prev["avg_div"] or 0)

        # Normalize to 0-1 range if stored as percentage
        if avg_recent > 1.0:
            avg_recent /= 100.0
        if avg_prev > 1.0:
            avg_prev /= 100.0

        if avg_prev > 0:
            velocity = (avg_recent - avg_prev) / avg_prev
            trend = "rising" if velocity > 0.1 else ("falling" if velocity < -0.1 else "stable")
        else:
            velocity = 0.0
            trend = "stable"

        # Pressure: 0 when divergence is stable/falling, up to 1.0 when accelerating fast
        vel_pressure = max(0.0, min(1.0, velocity * 2))

        ctx.divergence_velocity = PressureMetric(
            value=vel_pressure, raw=velocity,
            label=f"divergence {'accelerating' if velocity > 0 else 'decelerating'}",
            trend=trend,
        )

    # ── Lifecycle Distribution ────────────────────────────────

    def _compute_lifecycle_distribution(self, conn: sqlite3.Connection, ctx: PipelineContext):
        """
        Count theses by lifecycle stage. High emerging-to-total ratio = fresh pipeline.
        """
        rows = conn.execute("""
            SELECT lifecycle_stage, COUNT(*) as cnt
            FROM theses
            WHERE status NOT IN ('rejected', 'invalidated')
            GROUP BY lifecycle_stage
        """).fetchall()

        stage_counts = {row["lifecycle_stage"]: row["cnt"] for row in rows}
        ctx.emerging_count = stage_counts.get("emerging", 0)
        ctx.validating_count = stage_counts.get("validating", 0)
        ctx.confirmed_count = stage_counts.get("confirmed", 0)
        ctx.saturated_count = stage_counts.get("saturated", 0)

        total = ctx.emerging_count + ctx.validating_count + ctx.confirmed_count + ctx.saturated_count
        if total > 0:
            freshness = (ctx.emerging_count + ctx.validating_count * 0.5) / total
        else:
            freshness = 0.5

        ctx.lifecycle_freshness = PressureMetric(
            value=freshness, raw=total,
            label=f"{ctx.emerging_count} emerging, {total} total theses",
            trend="stable",
        )

    # ── Pipeline Throughput ───────────────────────────────────

    def _compute_pipeline_throughput(self, conn: sqlite3.Connection, ctx: PipelineContext):
        """
        Measure conversion efficiency: signals → mosaics → theses in last 24h.
        Low throughput = pipeline is stalled somewhere.
        """
        day_ago = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()

        signals_24h = conn.execute(
            "SELECT COUNT(*) as cnt FROM signals WHERE timestamp > ?", (day_ago,),
        ).fetchone()["cnt"]

        mosaics_24h = conn.execute(
            "SELECT COUNT(*) as cnt FROM mosaics WHERE created_at > ?", (day_ago,),
        ).fetchone()["cnt"]

        theses_24h = conn.execute(
            "SELECT COUNT(*) as cnt FROM theses WHERE created_at > ?", (day_ago,),
        ).fetchone()["cnt"]

        # Conversion rate: theses / signals (what fraction of signal volume becomes actionable)
        ctx.conversion_rate = theses_24h / max(signals_24h, 1)

        lo, hi = self._bounds["throughput"]
        ctx.pipeline_throughput = PressureMetric(
            value=self._normalize(theses_24h, lo, hi),
            raw=theses_24h,
            label=f"{signals_24h}→{mosaics_24h}→{theses_24h} (24h)",
            trend="stable",
        )

    # ── HITL Backlog ──────────────────────────────────────────

    def _compute_hitl_backlog(self, conn: sqlite3.Connection, ctx: PipelineContext):
        """
        Pending reviews waiting for human decision. High backlog = gatekeeper
        should be more aggressive with auto-promotion.
        """
        row = conn.execute(
            "SELECT COUNT(*) as cnt FROM reviews WHERE decision IS NULL"
        ).fetchone()
        pending = row["cnt"] if row else 0
        ctx.pending_review_count = pending

        lo, hi = self._bounds["hitl_backlog"]
        ctx.hitl_backlog = PressureMetric(
            value=self._normalize(pending, lo, hi),
            raw=pending,
            label=f"{pending} pending reviews",
            trend="stable",
        )

    # ── Portfolio Heat ────────────────────────────────────────

    def _compute_portfolio_heat(self, conn: sqlite3.Connection, ctx: PipelineContext):
        """
        Total allocation across open positions. High heat = tighten limits.
        """
        row = conn.execute("""
            SELECT COUNT(*) as cnt, COALESCE(SUM(allocation_pct), 0) as total_alloc
            FROM positions WHERE status = 'open'
        """).fetchone()

        ctx.open_position_count = row["cnt"] if row else 0
        ctx.total_allocation_pct = row["total_alloc"] if row else 0

        lo, hi = self._bounds["portfolio_heat"]
        ctx.portfolio_heat = PressureMetric(
            value=self._normalize(ctx.total_allocation_pct, lo, hi),
            raw=ctx.total_allocation_pct,
            label=f"{ctx.open_position_count} positions, {ctx.total_allocation_pct:.1f}% allocated",
            trend="stable",
        )

    # ── Hot Symbols ───────────────────────────────────────────

    def _compute_hot_symbols(self, conn: sqlite3.Connection, ctx: PipelineContext):
        """
        Identify the most urgent symbols: high signal velocity + high divergence
        + early lifecycle stage. Agents use this to prioritize what they process.
        """
        now = datetime.now(timezone.utc)
        recent = (now - timedelta(hours=24)).isoformat()

        rows = conn.execute("""
            SELECT
                s.symbol,
                COUNT(s.id) as signal_count_24h,
                COUNT(DISTINCT s.source) as source_count,
                m.divergence_strength,
                m.coherence_score,
                t.lifecycle_stage,
                t.kelly_fraction
            FROM signals s
            LEFT JOIN (
                SELECT symbol, divergence_strength, coherence_score,
                       ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY created_at DESC) as rn
                FROM mosaics
            ) m ON m.symbol = s.symbol AND m.rn = 1
            LEFT JOIN (
                SELECT symbol, lifecycle_stage, kelly_fraction,
                       ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY created_at DESC) as rn
                FROM theses
            ) t ON t.symbol = s.symbol AND t.rn = 1
            WHERE s.timestamp > ?
            GROUP BY s.symbol
            HAVING signal_count_24h >= 2
            ORDER BY signal_count_24h DESC
            LIMIT 20
        """, (recent,)).fetchall()

        lifecycle_urgency = {"emerging": 4, "validating": 3, "confirmed": 2, "saturated": 1}

        hot = []
        for row in rows:
            r = dict(row)
            div = r.get("divergence_strength") or 0
            if div > 1.0:
                div /= 100.0
            lifecycle = r.get("lifecycle_stage") or "validating"
            urgency = lifecycle_urgency.get(lifecycle, 2)

            # Composite urgency score: signal_volume × divergence × lifecycle_urgency
            score = (r["signal_count_24h"] / 10.0) * max(div, 0.1) * urgency

            hot.append({
                "symbol": r["symbol"],
                "signal_count_24h": r["signal_count_24h"],
                "source_count": r["source_count"],
                "divergence": round(div, 4),
                "lifecycle_stage": lifecycle,
                "urgency_score": round(score, 3),
            })

        hot.sort(key=lambda x: x["urgency_score"], reverse=True)
        ctx.hot_symbols = hot[:10]

    # ── Bottleneck Detection ──────────────────────────────────

    def _detect_bottleneck(self, conn: sqlite3.Connection, ctx: PipelineContext):
        """
        Find where the pipeline is choking. Compare layer input vs output rates.
        If sentinel produces 200 signals/day but assembler only creates 10 mosaics,
        the assembler is the bottleneck.
        """
        day_ago = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()

        signals = conn.execute(
            "SELECT COUNT(*) as cnt FROM signals WHERE timestamp > ?", (day_ago,),
        ).fetchone()["cnt"]

        mosaics = conn.execute(
            "SELECT COUNT(*) as cnt FROM mosaics WHERE created_at > ?", (day_ago,),
        ).fetchone()["cnt"]

        theses = conn.execute(
            "SELECT COUNT(*) as cnt FROM theses WHERE created_at > ?", (day_ago,),
        ).fetchone()["cnt"]

        reviews_pending = ctx.pending_review_count

        # Compute drop ratios between layers
        # A healthy pipeline has gradual funneling; a bottleneck shows a sudden cliff
        bottleneck = None
        max_drop = 0.0

        if signals > 0:
            # Sentinel → Assembler drop
            assembler_efficiency = mosaics / max(signals, 1)
            if assembler_efficiency < 0.01 and signals > 20:
                drop = 1.0 - assembler_efficiency
                if drop > max_drop:
                    max_drop = drop
                    bottleneck = "assembler"

        if mosaics > 0:
            # Assembler → Strategist drop
            strategist_efficiency = theses / max(mosaics, 1)
            if strategist_efficiency < 0.05 and mosaics > 5:
                drop = 1.0 - strategist_efficiency
                if drop > max_drop:
                    max_drop = drop
                    bottleneck = "strategist"

        if theses > 0 and reviews_pending > 10:
            # Strategist → Gatekeeper backlog
            gatekeeper_load = reviews_pending / max(theses, 1)
            if gatekeeper_load > 0.5:
                drop = min(1.0, gatekeeper_load)
                if drop > max_drop:
                    max_drop = drop
                    bottleneck = "gatekeeper"

        ctx.bottleneck_agent = bottleneck
        ctx.bottleneck_severity = max_drop

    # ── Utility ───────────────────────────────────────────────

    @staticmethod
    def _normalize(value: float, lo: float, hi: float) -> float:
        """Normalize value to 0.0-1.0 pressure scale."""
        if hi <= lo:
            return 0.5
        return max(0.0, min(1.0, (value - lo) / (hi - lo)))


# ── Agent Helper: Adaptive Parameter Interpolation ────────────

def adapt(pressure: float, calm_value: float, urgent_value: float) -> float:
    """
    Interpolate a parameter between calm and urgent values based on pressure.

    Usage in agents:
        tick_interval = adapt(ctx.signal_velocity.value, calm=120, urgent=15)
        min_signals = adapt(ctx.pipeline_throughput.value, calm=5, urgent=2)

    When pressure=0 → returns calm_value
    When pressure=1 → returns urgent_value
    """
    return calm_value + pressure * (urgent_value - calm_value)
