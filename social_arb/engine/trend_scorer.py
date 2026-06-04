"""
Trend Scorer Engine — Computes trending tickers, theme clusters, and ticker deep dives.

All data comes from the DB. No hardcoding. Queries:
  - signals (recent activity, direction, source diversity)
  - mosaics (coherence, divergence, narrative)
  - theses (kelly, ROI, lifecycle)
  - ohlcv (price sparklines)
  - stepps_scores (virality dimensions)
  - reviews (HITL queue status)
  - instruments (name, type, sector)

Trend Score formula:
  trend_score = w1*signal_velocity + w2*source_diversity + w3*divergence + w4*coherence + w5*recency
  Weights: velocity=0.30, source_diversity=0.15, divergence=0.25, coherence=0.20, recency=0.10
"""

import json
import logging
import sqlite3
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from social_arb.db.adapter import get_connection, get_placeholder

logger = logging.getLogger(__name__)

# Trend score weights
W_VELOCITY = 0.30
W_SOURCE_DIVERSITY = 0.15
W_DIVERGENCE = 0.25
W_COHERENCE = 0.20
W_RECENCY = 0.10

# Known source count for normalization
KNOWN_SOURCES = [
    "yfinance", "reddit", "sec_edgar", "google_trends", "github",
    "coingecko", "defillama", "news", "appstore", "patent",
    "hiring", "web_presence", "research", "manual",
]


def _normalize_domain(instrument_type: str, mosaic_domain: str) -> str:
    """Map DB domain strings to frontend domain: public | private | crypto."""
    itype = (instrument_type or "").lower()
    mdomain = (mosaic_domain or "").lower()

    if itype == "crypto" or mdomain in ("crypto", "defi", "ai_crypto"):
        return "crypto"
    if itype == "private" or "private" in mdomain:
        return "private"
    # Everything else (stock, etf, public_markets, sector-based domains)
    return "public"


def _dict_row(cursor, row):
    """Convert sqlite3 row to dict."""
    cols = [d[0] for d in cursor.description]
    return dict(zip(cols, row))


def _get_conn(db_path: str):
    """Get a connection with dict row factory."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = _dict_row
    return conn


def _safe_float(val, default=0.0):
    try:
        return float(val) if val is not None else default
    except (ValueError, TypeError):
        return default


def get_trending_tickers(
    db_path: str,
    hours: int = 168,
    limit: int = 50,
    domain_filter: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Compute trending tickers ranked by trend score.

    Pulls from: signals, mosaics, theses, instruments, ohlcv.
    Returns list of ticker dicts with trend_score, signals, divergence, etc.
    """
    hours = max(int(hours), 1)  # guard against div-by-zero in recency calc
    conn = _get_conn(db_path)
    ph = get_placeholder()
    cutoff = (datetime.utcnow() - timedelta(hours=hours)).isoformat()

    try:
        # 1. Signal aggregation per symbol (recent window)
        signal_query = f"""
            SELECT
                s.symbol,
                COUNT(*) as signal_count,
                COUNT(DISTINCT s.source) as source_count,
                GROUP_CONCAT(DISTINCT s.source) as sources,
                SUM(CASE WHEN s.direction = 'bullish' THEN 1 ELSE 0 END) as bullish,
                SUM(CASE WHEN s.direction = 'bearish' THEN 1 ELSE 0 END) as bearish,
                SUM(CASE WHEN s.direction = 'neutral' THEN 1 ELSE 0 END) as neutral,
                AVG(s.strength) as avg_strength,
                AVG(s.confidence) as avg_confidence,
                MAX(s.timestamp) as latest_signal
            FROM signals s
            WHERE s.timestamp >= {ph}
            GROUP BY s.symbol
            HAVING COUNT(*) >= 2
            ORDER BY COUNT(*) DESC
        """
        rows = conn.execute(signal_query, (cutoff,)).fetchall()

        if not rows:
            return []

        symbols = [r["symbol"] for r in rows]
        signal_map = {r["symbol"]: r for r in rows}

        # 2. Latest mosaic per symbol
        mosaic_map = {}
        for sym in symbols:
            m = conn.execute(
                f"""SELECT symbol, domain, coherence_score, divergence_strength,
                           narrative, action, fragments_json, created_at
                    FROM mosaics WHERE symbol = {ph}
                    ORDER BY created_at DESC LIMIT 1""",
                (sym,),
            ).fetchone()
            if m:
                mosaic_map[sym] = m

        # 3. Latest thesis per symbol
        thesis_map = {}
        for sym in symbols:
            t = conn.execute(
                f"""SELECT symbol, domain, roi_bear, roi_base, roi_bull,
                           kelly_fraction, lifecycle_stage, status, created_at
                    FROM theses WHERE symbol = {ph}
                    ORDER BY created_at DESC LIMIT 1""",
                (sym,),
            ).fetchone()
            if t:
                thesis_map[sym] = t

        # 4. Instrument metadata
        instr_map = {}
        for sym in symbols:
            i = conn.execute(
                f"SELECT symbol, name, type, sector, vertical, data_class FROM instruments WHERE symbol = {ph}",
                (sym,),
            ).fetchone()
            if i:
                instr_map[sym] = i

        # 5. Price sparkline (last 12 data points from ohlcv)
        sparkline_map = {}
        for sym in symbols:
            prices = conn.execute(
                f"""SELECT close FROM ohlcv WHERE symbol = {ph}
                    ORDER BY timestamp DESC LIMIT 12""",
                (sym,),
            ).fetchall()
            if prices:
                sparkline_map[sym] = [p["close"] for p in reversed(prices)]

        # 6. Signal timeline (daily counts for last 7 days grouped by source)
        now = datetime.utcnow()
        timeline_map = {}
        for sym in symbols:
            timeline_rows = conn.execute(
                f"""SELECT DATE(timestamp) as day, source, COUNT(*) as cnt
                    FROM signals
                    WHERE symbol = {ph} AND timestamp >= {ph}
                    GROUP BY DATE(timestamp), source
                    ORDER BY day""",
                (sym, (now - timedelta(days=7)).isoformat()),
            ).fetchall()
            if timeline_rows:
                days = defaultdict(lambda: defaultdict(int))
                for tr in timeline_rows:
                    days[tr["day"]][tr["source"]] = tr["cnt"]
                timeline_map[sym] = [
                    {"date": day, **dict(sources)}
                    for day, sources in sorted(days.items())
                ]

        # 7. Compute trend scores
        # Find max signal count for normalization
        max_signals = max(r["signal_count"] for r in rows) if rows else 1

        results = []
        for sig in rows:
            sym = sig["symbol"]
            mosaic = mosaic_map.get(sym, {})
            thesis = thesis_map.get(sym, {})
            instr = instr_map.get(sym, {})

            # Velocity: normalized signal count (0-1)
            velocity = min(sig["signal_count"] / max(max_signals, 1), 1.0)

            # Source diversity: source_count / known sources (0-1)
            source_div = min(sig["source_count"] / max(len(KNOWN_SOURCES), 1), 1.0)

            # Divergence: from mosaic (normalize to 0-1; DB may store 0-100)
            raw_div = _safe_float(mosaic.get("divergence_strength"), 0.0)
            divergence = raw_div / 100.0 if raw_div > 1.0 else raw_div

            # Coherence: from mosaic (normalize to 0-1; DB may store 0-100)
            raw_coh = _safe_float(mosaic.get("coherence_score"), 0.0)
            coherence = raw_coh / 100.0 if raw_coh > 1.0 else raw_coh

            # Recency: how recent is the latest signal (0-1, 1 = within last hour)
            recency = 0.0
            latest = sig.get("latest_signal")
            if latest:
                try:
                    latest_dt = datetime.fromisoformat(str(latest).replace("Z", "+00:00").replace("+00:00", ""))
                    age_hours = max((now - latest_dt).total_seconds() / 3600, 0)
                    recency = max(1.0 - (age_hours / hours), 0.0)
                except (ValueError, TypeError):
                    pass

            trend_score = round(
                (W_VELOCITY * velocity
                 + W_SOURCE_DIVERSITY * source_div
                 + W_DIVERGENCE * divergence
                 + W_COHERENCE * coherence
                 + W_RECENCY * recency) * 100,
                1,
            )

            # Direction: majority vote
            b = sig["bullish"] or 0
            br = sig["bearish"] or 0
            n = sig["neutral"] or 0
            total = b + br + n
            if total > 0:
                if b / total > 0.5:
                    direction = "bullish"
                elif br / total > 0.5:
                    direction = "bearish"
                else:
                    direction = "neutral"
            else:
                direction = "neutral"

            # Domain: normalize from instrument type + mosaic domain
            domain = _normalize_domain(instr.get("type", ""), mosaic.get("domain", ""))

            sources_str = sig.get("sources", "")
            sources_list = [s.strip() for s in sources_str.split(",") if s.strip()] if sources_str else []

            results.append({
                "symbol": sym,
                "name": instr.get("name", sym),
                "domain": domain,
                "trend_score": trend_score,
                "signal_count": sig["signal_count"],
                "source_count": sig["source_count"],
                "sources": sources_list,
                "direction": direction,
                "bullish": b,
                "bearish": br,
                "neutral": n,
                "avg_strength": round(_safe_float(sig["avg_strength"]), 3),
                "avg_confidence": round(_safe_float(sig["avg_confidence"]), 3),
                "divergence": round(divergence, 3),
                "coherence": round(coherence, 3),
                "narrative": mosaic.get("narrative", ""),
                "mosaic_action": mosaic.get("action", ""),
                "lifecycle": thesis.get("lifecycle_stage", ""),
                "kelly": round(_safe_float(thesis.get("kelly_fraction")), 4),
                "roi_bear": _safe_float(thesis.get("roi_bear")),
                "roi_base": _safe_float(thesis.get("roi_base")),
                "roi_bull": _safe_float(thesis.get("roi_bull")),
                "thesis_status": thesis.get("status", ""),
                "latest_signal": sig.get("latest_signal", ""),
                "sparkline": sparkline_map.get(sym, []),
                "sector": instr.get("sector", ""),
                "vertical": instr.get("vertical", ""),
            })

        # Apply domain filter
        if domain_filter and domain_filter != "all":
            results = [r for r in results if r["domain"] == domain_filter]

        # Sort by trend score
        results.sort(key=lambda x: x["trend_score"], reverse=True)
        return results[:limit]

    finally:
        conn.close()


def get_divergence_alerts(db_path: str, min_divergence: float = 0.15, limit: int = 10) -> List[Dict[str, Any]]:
    """Get tickers with highest divergence (social vs market gap)."""
    tickers = get_trending_tickers(db_path, hours=168, limit=200)
    alerts = [t for t in tickers if t["divergence"] >= min_divergence]
    alerts.sort(key=lambda x: x["divergence"], reverse=True)
    return alerts[:limit]


def get_similar_trends(db_path: str, limit: int = 20) -> List[Dict[str, Any]]:
    """
    Cluster tickers by shared narrative/sector signals.

    Strategy: Group by sector+vertical from instruments, then by shared signal sources.
    For each cluster, compute aggregate metrics.
    """
    conn = _get_conn(db_path)
    now = datetime.utcnow()
    cutoff = (now - timedelta(hours=168)).isoformat()

    try:
        # Get all tickers with recent mosaics that have a narrative
        rows = conn.execute(
            f"""SELECT m.symbol, m.domain, m.coherence_score, m.divergence_strength,
                       m.narrative, m.action, m.created_at,
                       i.name, i.type, i.sector, i.vertical
                FROM mosaics m
                LEFT JOIN instruments i ON m.symbol = i.symbol
                WHERE m.created_at >= {get_placeholder()}
                  AND m.narrative IS NOT NULL AND m.narrative != ''
                ORDER BY m.created_at DESC""",
            (cutoff,),
        ).fetchall()

        if not rows:
            return []

        # Deduplicate: latest mosaic per symbol
        seen = set()
        unique = []
        for r in rows:
            if r["symbol"] not in seen:
                seen.add(r["symbol"])
                unique.append(r)

        # Group by sector+vertical (primary clustering), fallback to domain
        clusters = defaultdict(list)
        for r in unique:
            sector = r.get("sector") or ""
            vertical = r.get("vertical") or ""
            domain = r.get("domain") or "public"

            if sector:
                key = f"{sector}|{vertical}" if vertical else sector
            else:
                key = f"domain:{domain}"

            clusters[key].append(r)

        # Build theme objects from clusters with 2+ tickers
        themes = []
        for key, members in clusters.items():
            if len(members) < 2:
                continue

            symbols = [m["symbol"] for m in members]
            def _norm(val):
                v = _safe_float(val)
                return v / 100.0 if v > 1.0 else v
            avg_coherence = sum(_norm(m.get("coherence_score")) for m in members) / len(members)
            avg_divergence = sum(_norm(m.get("divergence_strength")) for m in members) / len(members)

            # Get signal counts per source for this cluster
            ph = get_placeholder()
            placeholders = ",".join([ph] * len(symbols))
            source_rows = conn.execute(
                f"""SELECT source, COUNT(*) as cnt
                    FROM signals
                    WHERE symbol IN ({placeholders}) AND timestamp >= {ph}
                    GROUP BY source""",
                (*symbols, cutoff),
            ).fetchall()
            source_counts = {r["source"]: r["cnt"] for r in source_rows}
            total_signals = sum(source_counts.values())

            # Timeline: weekly trend score
            timeline_rows = conn.execute(
                f"""SELECT DATE(timestamp) as day, COUNT(*) as cnt
                    FROM signals
                    WHERE symbol IN ({placeholders}) AND timestamp >= {ph}
                    GROUP BY DATE(timestamp)
                    ORDER BY day""",
                (*symbols, (now - timedelta(days=30)).isoformat()),
            ).fetchall()
            timeline = [{"date": r["day"], "signals": r["cnt"]} for r in timeline_rows]

            # Pick best narrative from highest-coherence member
            best = max(members, key=lambda m: _safe_float(m.get("coherence_score")))
            narrative = best.get("narrative", "")

            # Theme name from sector/vertical or domain
            if "|" in key:
                parts = key.split("|")
                theme_name = f"{parts[0]} — {parts[1]}" if parts[1] else parts[0]
            elif key.startswith("domain:"):
                theme_name = f"{key.replace('domain:', '').title()} Markets"
            else:
                theme_name = key

            # Lifecycle: from theses of member symbols
            lifecycle_rows = conn.execute(
                f"""SELECT lifecycle_stage, COUNT(*) as cnt
                    FROM theses
                    WHERE symbol IN ({placeholders})
                    GROUP BY lifecycle_stage
                    ORDER BY cnt DESC LIMIT 1""",
                tuple(symbols),
            ).fetchall()
            lifecycle = lifecycle_rows[0]["lifecycle_stage"] if lifecycle_rows else ""

            # Trend score for cluster
            velocity = min(total_signals / 100, 1.0)
            source_div = min(len(source_counts) / len(KNOWN_SOURCES), 1.0)
            theme_score = round(
                (W_VELOCITY * velocity
                 + W_SOURCE_DIVERSITY * source_div
                 + W_DIVERGENCE * avg_divergence
                 + W_COHERENCE * avg_coherence
                 + W_RECENCY * 0.5) * 100,
                1,
            )

            themes.append({
                "theme": theme_name,
                "trend_score": theme_score,
                "tickers": symbols,
                "ticker_count": len(symbols),
                "signal_count": total_signals,
                "narrative": narrative,
                "lifecycle": lifecycle,
                "sources": source_counts,
                "divergence_avg": round(avg_divergence, 3),
                "coherence_avg": round(avg_coherence, 3),
                "timeline": timeline,
            })

        themes.sort(key=lambda x: x["trend_score"], reverse=True)
        return themes[:limit]

    finally:
        conn.close()


def get_ticker_deep_dive(db_path: str, symbol: str) -> Dict[str, Any]:
    """
    Full deep dive for a single ticker: signals, mosaic, thesis, STEPPS, timeline, HITL status.
    """
    conn = _get_conn(db_path)
    ph = get_placeholder()
    now = datetime.utcnow()

    try:
        # Instrument metadata
        instr = conn.execute(
            f"SELECT * FROM instruments WHERE symbol = {ph}", (symbol,)
        ).fetchone() or {}

        # Signal stats (all time + recent)
        all_signals = conn.execute(
            f"""SELECT COUNT(*) as total,
                       COUNT(DISTINCT source) as source_count,
                       GROUP_CONCAT(DISTINCT source) as sources,
                       SUM(CASE WHEN direction='bullish' THEN 1 ELSE 0 END) as bullish,
                       SUM(CASE WHEN direction='bearish' THEN 1 ELSE 0 END) as bearish,
                       SUM(CASE WHEN direction='neutral' THEN 1 ELSE 0 END) as neutral,
                       AVG(strength) as avg_strength,
                       AVG(confidence) as avg_confidence,
                       MAX(timestamp) as latest
                FROM signals WHERE symbol = {ph}""",
            (symbol,),
        ).fetchone() or {}

        recent_signals = conn.execute(
            f"""SELECT COUNT(*) as total
                FROM signals WHERE symbol = {ph} AND timestamp >= {ph}""",
            (symbol, (now - timedelta(hours=24)).isoformat()),
        ).fetchone() or {}

        # Signal timeline by source (daily for last 30 days)
        timeline_rows = conn.execute(
            f"""SELECT DATE(timestamp) as day, source, COUNT(*) as cnt
                FROM signals
                WHERE symbol = {ph} AND timestamp >= {ph}
                GROUP BY DATE(timestamp), source
                ORDER BY day""",
            (symbol, (now - timedelta(days=30)).isoformat()),
        ).fetchall()

        timeline = defaultdict(lambda: defaultdict(int))
        all_tl_sources = set()
        for tr in timeline_rows:
            timeline[tr["day"]][tr["source"]] = tr["cnt"]
            all_tl_sources.add(tr["source"])
        signal_timeline = [
            {"date": day, **{src: counts.get(src, 0) for src in sorted(all_tl_sources)}}
            for day, counts in sorted(timeline.items())
        ]

        # Recent individual signals (last 20)
        recent_feed = conn.execute(
            f"""SELECT id, timestamp, source, signal_type, direction, strength, confidence, raw_json
                FROM signals WHERE symbol = {ph}
                ORDER BY timestamp DESC LIMIT 20""",
            (symbol,),
        ).fetchall()

        signal_feed = []
        for sig in recent_feed:
            raw = {}
            if sig.get("raw_json"):
                try:
                    raw = json.loads(sig["raw_json"])
                except (json.JSONDecodeError, TypeError):
                    pass
            # Build a human-readable summary from raw_json
            summary = raw.get("title", raw.get("summary", raw.get("text", "")))
            if not summary:
                summary = f"{sig['signal_type']} signal from {sig['source']}"

            signal_feed.append({
                "id": sig["id"],
                "timestamp": sig["timestamp"],
                "source": sig["source"],
                "signal_type": sig["signal_type"],
                "direction": sig["direction"],
                "strength": _safe_float(sig["strength"]),
                "confidence": _safe_float(sig["confidence"]),
                "summary": str(summary)[:200],
            })

        # Latest mosaic
        mosaic = conn.execute(
            f"""SELECT * FROM mosaics WHERE symbol = {ph}
                ORDER BY created_at DESC LIMIT 1""",
            (symbol,),
        ).fetchone() or {}

        # Latest thesis
        thesis = conn.execute(
            f"""SELECT * FROM theses WHERE symbol = {ph}
                ORDER BY created_at DESC LIMIT 1""",
            (symbol,),
        ).fetchone() or {}

        # STEPPS scores (latest per signal, aggregate)
        stepps_rows = conn.execute(
            f"""SELECT ss.social_currency, ss.triggers, ss.emotion,
                       ss.public_visibility, ss.practical_value, ss.stories, ss.composite
                FROM stepps_scores ss
                JOIN signals s ON ss.signal_id = s.id
                WHERE s.symbol = {ph}
                ORDER BY ss.created_at DESC LIMIT 20""",
            (symbol,),
        ).fetchall()

        stepps = None
        if stepps_rows:
            n = len(stepps_rows)
            stepps = {
                "social_currency": round(sum(_safe_float(r["social_currency"]) for r in stepps_rows) / n, 3),
                "triggers": round(sum(_safe_float(r["triggers"]) for r in stepps_rows) / n, 3),
                "emotion": round(sum(_safe_float(r["emotion"]) for r in stepps_rows) / n, 3),
                "public_visibility": round(sum(_safe_float(r["public_visibility"]) for r in stepps_rows) / n, 3),
                "practical_value": round(sum(_safe_float(r["practical_value"]) for r in stepps_rows) / n, 3),
                "stories": round(sum(_safe_float(r["stories"]) for r in stepps_rows) / n, 3),
                "composite": round(sum(_safe_float(r["composite"]) for r in stepps_rows) / n, 3),
                "sample_size": n,
            }

        # Price sparkline
        prices = conn.execute(
            f"""SELECT close FROM ohlcv WHERE symbol = {ph}
                ORDER BY timestamp DESC LIMIT 30""",
            (symbol,),
        ).fetchall()
        sparkline = [p["close"] for p in reversed(prices)] if prices else []

        # HITL review status
        latest_review = conn.execute(
            f"""SELECT gate, decision, total_score, threshold, created_at
                FROM reviews WHERE symbol = {ph}
                ORDER BY created_at DESC LIMIT 1""",
            (symbol,),
        ).fetchone()

        pending_reviews = conn.execute(
            f"""SELECT COUNT(*) as cnt FROM reviews
                WHERE symbol = {ph} AND decision IN ('watch', 'defer')""",
            (symbol,),
        ).fetchone()

        # Position status
        open_position = conn.execute(
            f"""SELECT * FROM positions WHERE symbol = {ph} AND status = 'open'
                ORDER BY created_at DESC LIMIT 1""",
            (symbol,),
        ).fetchone()

        # Build domain
        domain = _normalize_domain(instr.get("type", ""), mosaic.get("domain", ""))

        sources_str = all_signals.get("sources", "")
        sources_list = [s.strip() for s in sources_str.split(",") if s.strip()] if sources_str else []

        # Trend score
        total = all_signals.get("total", 0) or 0
        velocity = min(total / 100, 1.0)
        source_div = min((all_signals.get("source_count", 0) or 0) / len(KNOWN_SOURCES), 1.0)
        raw_div = _safe_float(mosaic.get("divergence_strength"))
        divergence = raw_div / 100.0 if raw_div > 1.0 else raw_div
        raw_coh = _safe_float(mosaic.get("coherence_score"))
        coherence = raw_coh / 100.0 if raw_coh > 1.0 else raw_coh
        trend_score = round(
            (W_VELOCITY * velocity + W_SOURCE_DIVERSITY * source_div
             + W_DIVERGENCE * divergence + W_COHERENCE * coherence
             + W_RECENCY * 0.5) * 100, 1
        )

        b = all_signals.get("bullish", 0) or 0
        br = all_signals.get("bearish", 0) or 0
        sig_total = b + br + (all_signals.get("neutral", 0) or 0)
        if sig_total > 0:
            direction = "bullish" if b / sig_total > 0.5 else ("bearish" if br / sig_total > 0.5 else "neutral")
        else:
            direction = "neutral"

        return {
            "symbol": symbol,
            "name": instr.get("name", symbol),
            "domain": domain,
            "sector": instr.get("sector", ""),
            "vertical": instr.get("vertical", ""),
            "trend_score": trend_score,
            "direction": direction,
            "signals": {
                "total": total,
                "recent_24h": recent_signals.get("total", 0) or 0,
                "source_count": all_signals.get("source_count", 0) or 0,
                "sources": sources_list,
                "bullish": b,
                "bearish": br,
                "neutral": all_signals.get("neutral", 0) or 0,
                "avg_strength": round(_safe_float(all_signals.get("avg_strength")), 3),
                "avg_confidence": round(_safe_float(all_signals.get("avg_confidence")), 3),
                "latest": all_signals.get("latest", ""),
            },
            "signal_timeline": signal_timeline,
            "signal_feed": signal_feed,
            "mosaic": {
                "coherence": round(coherence, 3),
                "divergence": round(divergence, 3),
                "narrative": mosaic.get("narrative", ""),
                "action": mosaic.get("action", ""),
                "fragments": _parse_json(mosaic.get("fragments_json")),
            },
            "thesis": {
                "roi_bear": _safe_float(thesis.get("roi_bear")),
                "roi_base": _safe_float(thesis.get("roi_base")),
                "roi_bull": _safe_float(thesis.get("roi_bull")),
                "kelly": round(_safe_float(thesis.get("kelly_fraction")), 4),
                "lifecycle": thesis.get("lifecycle_stage", ""),
                "status": thesis.get("status", ""),
                "vulnerability": _parse_json(thesis.get("vulnerability_json")),
                "simulation": _parse_json(thesis.get("simulation_json")),
            },
            "stepps": stepps,
            "sparkline": sparkline,
            "hitl": {
                "latest_review": {
                    "gate": latest_review["gate"] if latest_review else None,
                    "decision": latest_review["decision"] if latest_review else None,
                    "score": _safe_float(latest_review.get("total_score")) if latest_review else None,
                    "threshold": _safe_float(latest_review.get("threshold")) if latest_review else None,
                    "date": latest_review["created_at"] if latest_review else None,
                },
                "pending_count": (pending_reviews.get("cnt", 0) or 0) if pending_reviews else 0,
            },
            "position": {
                "status": open_position["status"] if open_position else None,
                "direction": open_position["direction"] if open_position else None,
                "allocation_pct": _safe_float(open_position.get("allocation_pct")) if open_position else None,
                "entry_price": _safe_float(open_position.get("entry_price")) if open_position else None,
                "pnl_pct": _safe_float(open_position.get("pnl_pct")) if open_position else None,
            } if open_position else None,
        }

    finally:
        conn.close()


def get_overview_stats(db_path: str) -> Dict[str, Any]:
    """Dashboard top-level stats."""
    conn = _get_conn(db_path)
    now = datetime.utcnow()
    ph = get_placeholder()

    try:
        today_cutoff = (now - timedelta(hours=24)).isoformat()
        week_cutoff = (now - timedelta(hours=168)).isoformat()

        total_signals = conn.execute("SELECT COUNT(*) as cnt FROM signals").fetchone()
        today_signals = conn.execute(
            f"SELECT COUNT(*) as cnt FROM signals WHERE timestamp >= {ph}", (today_cutoff,)
        ).fetchone()
        week_symbols = conn.execute(
            f"SELECT COUNT(DISTINCT symbol) as cnt FROM signals WHERE timestamp >= {ph}", (week_cutoff,)
        ).fetchone()
        active_mosaics = conn.execute(
            f"SELECT COUNT(DISTINCT symbol) as cnt FROM mosaics WHERE created_at >= {ph}", (week_cutoff,)
        ).fetchone()
        theme_count = len(get_similar_trends(db_path, limit=100))
        pending_reviews = conn.execute(
            "SELECT COUNT(*) as cnt FROM reviews WHERE decision IN ('watch', 'defer')"
        ).fetchone()
        open_positions = conn.execute(
            "SELECT COUNT(*) as cnt FROM positions WHERE status = 'open'"
        ).fetchone()

        return {
            "total_signals": (total_signals or {}).get("cnt", 0) or 0,
            "signals_24h": (today_signals or {}).get("cnt", 0) or 0,
            "trending_symbols": (week_symbols or {}).get("cnt", 0) or 0,
            "active_mosaics": (active_mosaics or {}).get("cnt", 0) or 0,
            "theme_clusters": theme_count,
            "pending_reviews": (pending_reviews or {}).get("cnt", 0) or 0,
            "open_positions": (open_positions or {}).get("cnt", 0) or 0,
        }

    finally:
        conn.close()


def _parse_json(val):
    if not val:
        return None
    try:
        return json.loads(val)
    except (json.JSONDecodeError, TypeError):
        return None
