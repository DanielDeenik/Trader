"""Camillo-style thesis writer — transforms mosaic cards into investment narratives.

Chris Camillo's approach: assemble disparate information fragments from
non-traditional sources into a coherent investment thesis before the
mainstream market prices it in.

All data comes from the database. Zero hardcoded values.
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from social_arb.db.schema import DEFAULT_DB_PATH


def dict_factory(cursor, row):
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}


def _extract_key_metrics(signals: List[Dict]) -> Dict:
    """Pull key metrics from raw signal data."""
    metrics = {}
    for s in signals:
        raw = s.get("raw") or {}
        if isinstance(raw, str):
            try: raw = json.loads(raw)
            except: raw = {}

        source = s.get("source", "")

        if source == "yfinance":
            if raw.get("close"):
                metrics["price"] = raw["close"]
            if raw.get("change_pct") is not None:
                metrics.setdefault("daily_changes", []).append(raw["change_pct"])
            if raw.get("volume"):
                metrics.setdefault("volumes", []).append(raw["volume"])
            if raw.get("market_cap"):
                metrics["market_cap"] = raw["market_cap"]
            if raw.get("pe_ratio"):
                metrics["pe_ratio"] = raw["pe_ratio"]

        elif source == "reddit":
            metrics.setdefault("reddit_mentions", []).append({
                "subreddit": raw.get("subreddit", "unknown"),
                "score": raw.get("score", 0),
                "comments": raw.get("num_comments", 0),
                "sentiment": s.get("strength", 0),
            })

        elif source == "sec_edgar":
            metrics.setdefault("sec_filings", []).append({
                "type": raw.get("filing_type", s.get("signal_type", "unknown")),
                "date": raw.get("filed_date", s.get("timestamp", "")),
            })

        elif source == "coingecko":
            if raw.get("price"):
                metrics["price"] = raw["price"]
            if raw.get("market_cap"):
                metrics["market_cap"] = raw["market_cap"]
            if raw.get("total_volume"):
                metrics["volume_24h"] = raw["total_volume"]
            if raw.get("price_change_7d_pct") is not None:
                metrics["price_change_7d"] = raw["price_change_7d_pct"]

        elif source == "defillama":
            if raw.get("tvl"):
                metrics["tvl"] = raw["tvl"]
            if raw.get("tvl_change_7d") is not None:
                metrics["tvl_change_7d"] = raw["tvl_change_7d"]
            if raw.get("category"):
                metrics["defi_category"] = raw["category"]
            if raw.get("chains"):
                metrics["chains"] = raw["chains"]

    # Compute averages
    if "daily_changes" in metrics:
        changes = metrics["daily_changes"]
        metrics["avg_daily_change"] = sum(changes) / len(changes)
        metrics["max_daily_change"] = max(changes)
        metrics["min_daily_change"] = min(changes)
    if "volumes" in metrics:
        metrics["avg_volume"] = sum(metrics["volumes"]) / len(metrics["volumes"])

    return metrics


def _format_price(val):
    if val is None: return "N/A"
    if val >= 1_000_000_000: return f"${val/1e9:.1f}B"
    if val >= 1_000_000: return f"${val/1e6:.1f}M"
    if val >= 1000: return f"${val:,.0f}"
    return f"${val:.2f}"


def write_thesis(symbol: str, db_path: str = DEFAULT_DB_PATH) -> Optional[str]:
    """Generate a Camillo-style investment thesis narrative for a symbol.

    Returns the thesis text, or None if insufficient data.
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = dict_factory

    # Get thesis
    thesis = conn.execute(
        "SELECT * FROM theses WHERE symbol = ? ORDER BY created_at DESC LIMIT 1", (symbol,)
    ).fetchone()
    if not thesis:
        return None

    # Get mosaic
    mosaic = conn.execute(
        "SELECT * FROM mosaics WHERE symbol = ? ORDER BY created_at DESC LIMIT 1", (symbol,)
    ).fetchone()

    # Get all signals
    signals_raw = conn.execute(
        "SELECT * FROM signals WHERE symbol = ? ORDER BY timestamp DESC", (symbol,)
    ).fetchall()

    # Parse raw_json
    signals = []
    for s in signals_raw:
        sig = dict(s)
        if sig.get("raw_json"):
            try: sig["raw"] = json.loads(sig["raw_json"])
            except: sig["raw"] = {}
        else:
            sig["raw"] = {}
        signals.append(sig)

    conn.close()

    if not signals:
        return None

    metrics = _extract_key_metrics(signals)
    fragments = []
    if mosaic and mosaic.get("fragments_json"):
        try: fragments = json.loads(mosaic["fragments_json"])
        except: fragments = []

    # Compute signal stats
    sources = list(set(s["source"] for s in signals))
    bullish = sum(1 for s in signals if s.get("direction") == "bullish")
    bearish = sum(1 for s in signals if s.get("direction") == "bearish")
    neutral = sum(1 for s in signals if s.get("direction") == "neutral")
    total = len(signals)
    dominant = "bullish" if bullish > bearish else "bearish" if bearish > bullish else "mixed"

    # ROI from thesis (computed from data, not hardcoded)
    roi_bear = thesis.get("roi_bear", 0)
    roi_base = thesis.get("roi_base", 0)
    roi_bull = thesis.get("roi_bull", 0)
    kelly = thesis.get("kelly_fraction", 0)
    lifecycle = thesis.get("lifecycle_stage", "unknown")
    domain = thesis.get("domain", "unknown")
    coherence = mosaic.get("coherence_score", 0) if mosaic else 0
    divergence = mosaic.get("divergence_strength", 0) if mosaic else 0

    # Build the thesis narrative
    lines = []
    lines.append(f"{'='*60}")
    lines.append(f"SOCIAL ARB — INVESTMENT THESIS")
    lines.append(f"{'='*60}")
    lines.append(f"Symbol:     {symbol}")
    lines.append(f"Domain:     {domain}")
    lines.append(f"Lifecycle:  {lifecycle.upper()}")
    lines.append(f"Generated:  {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    lines.append(f"{'='*60}")
    lines.append("")

    # MOSAIC SUMMARY
    lines.append("MOSAIC SUMMARY")
    lines.append("-" * 40)
    lines.append(f"Signals:    {total} from {len(sources)} sources ({', '.join(sources)})")
    lines.append(f"Direction:  {dominant} ({bullish} bullish / {bearish} bearish / {neutral} neutral)")
    lines.append(f"Coherence:  {coherence:.0f}/100")
    lines.append(f"Divergence: {divergence:.1f}")
    lines.append("")

    # KEY METRICS
    lines.append("KEY METRICS (from collected data)")
    lines.append("-" * 40)
    if "price" in metrics:
        lines.append(f"Price:          {_format_price(metrics['price'])}")
    if "market_cap" in metrics:
        lines.append(f"Market Cap:     {_format_price(metrics['market_cap'])}")
    if "pe_ratio" in metrics:
        lines.append(f"P/E Ratio:      {metrics['pe_ratio']:.1f}")
    if "tvl" in metrics:
        lines.append(f"TVL:            {_format_price(metrics['tvl'])}")
    if "tvl_change_7d" in metrics:
        lines.append(f"TVL 7d Change:  {metrics['tvl_change_7d']:+.1f}%")
    if "price_change_7d" in metrics:
        lines.append(f"Price 7d Chg:   {metrics['price_change_7d']:+.1f}%")
    if "avg_daily_change" in metrics:
        lines.append(f"Avg Daily Move: {metrics['avg_daily_change']:+.2f}%")
    if "avg_volume" in metrics:
        lines.append(f"Avg Volume:     {metrics['avg_volume']:,.0f}")
    if "defi_category" in metrics:
        lines.append(f"DeFi Category:  {metrics['defi_category']}")
    if "chains" in metrics:
        lines.append(f"Chains:         {', '.join(metrics['chains'][:5])}")
    lines.append("")

    # INFORMATION FRAGMENTS (Camillo's mosaic pieces)
    lines.append("INFORMATION FRAGMENTS")
    lines.append("-" * 40)
    if "reddit_mentions" in metrics:
        mentions = metrics["reddit_mentions"]
        total_score = sum(m["score"] for m in mentions)
        total_comments = sum(m["comments"] for m in mentions)
        subs = list(set(m["subreddit"] for m in mentions))
        avg_sentiment = sum(m["sentiment"] for m in mentions) / len(mentions) if mentions else 0
        lines.append(f"Reddit:     {len(mentions)} mentions across {', '.join(subs)}")
        lines.append(f"            Total engagement: {total_score} upvotes, {total_comments} comments")
        lines.append(f"            Avg sentiment strength: {avg_sentiment:.2f}")

    if "sec_filings" in metrics:
        filings = metrics["sec_filings"]
        filing_types = {}
        for f in filings:
            ft = f["type"]
            filing_types[ft] = filing_types.get(ft, 0) + 1
        lines.append(f"SEC Filings: {len(filings)} recent filings")
        for ft, cnt in sorted(filing_types.items(), key=lambda x: -x[1]):
            lines.append(f"            {ft}: {cnt}")

    if "daily_changes" in metrics:
        changes = metrics["daily_changes"]
        pos_days = sum(1 for c in changes if c > 0)
        neg_days = sum(1 for c in changes if c < 0)
        lines.append(f"Price Action: {pos_days} up days, {neg_days} down days (last {len(changes)} sessions)")
        lines.append(f"            Range: {metrics['min_daily_change']:+.2f}% to {metrics['max_daily_change']:+.2f}%")

    lines.append("")

    # CAMILLO-STYLE THESIS
    lines.append("THESIS NARRATIVE")
    lines.append("-" * 40)

    # Build narrative based on signal convergence
    if domain == "crypto":
        if "tvl" in metrics:
            lines.append(f"{symbol} currently has {_format_price(metrics.get('tvl', 0))} in Total Value Locked,")
            if metrics.get("tvl_change_7d", 0) > 0:
                lines.append(f"growing {metrics['tvl_change_7d']:+.1f}% over the past 7 days. Capital is flowing IN.")
            else:
                lines.append(f"contracting {metrics.get('tvl_change_7d', 0):.1f}% over the past 7 days.")

        if "reddit_mentions" in metrics and len(metrics["reddit_mentions"]) > 0:
            lines.append(f"Social signal shows {len(metrics['reddit_mentions'])} mentions across crypto Reddit communities")
            if dominant == "bullish":
                lines.append("with predominantly bullish sentiment — retail attention is building.")
            else:
                lines.append(f"with {dominant} sentiment.")

        if divergence > 20:
            lines.append(f"\nCRITICAL: Divergence score of {divergence:.1f} indicates social attention")
            lines.append("is outpacing market expectations. This is the Camillo signal —")
            lines.append("information asymmetry between retail social chatter and institutional pricing.")

    elif domain == "public_markets":
        if "price" in metrics:
            lines.append(f"{symbol} trading at {_format_price(metrics['price'])}")
            if "market_cap" in metrics:
                lines.append(f"({_format_price(metrics['market_cap'])} market cap)")
            if "pe_ratio" in metrics:
                lines.append(f"at a P/E of {metrics['pe_ratio']:.1f}.")
            else:
                lines.append(".")

        if "sec_filings" in metrics:
            filing_count = len(metrics["sec_filings"])
            lines.append(f"\n{filing_count} recent SEC filings detected — institutional activity is elevated.")
            insider_forms = sum(1 for f in metrics["sec_filings"] if "4" in f["type"])
            if insider_forms > 3:
                lines.append(f"  {insider_forms} Form 4 insider transactions flagged.")

        if "reddit_mentions" in metrics and len(metrics["reddit_mentions"]) > 0:
            lines.append(f"\nReddit signal: {len(metrics['reddit_mentions'])} social mentions with")
            avg_sent = sum(m["sentiment"] for m in metrics["reddit_mentions"]) / len(metrics["reddit_mentions"])
            sentiment_label = "strongly bullish" if avg_sent > 0.7 else "bullish" if avg_sent > 0.3 else "mixed"
            lines.append(f"{sentiment_label} average sentiment ({avg_sent:.2f}).")

        if divergence > 30:
            lines.append(f"\nDIVERGENCE ALERT: Score {divergence:.1f} — social signals diverging from")
            lines.append("institutional/market signals. Per Camillo's framework, this divergence")
            lines.append("represents an information arbitrage opportunity before market convergence.")

    elif domain == "private_markets":
        lines.append(f"{symbol} is a private company tracked via alternative data sources.")
        if "reddit_mentions" in metrics:
            lines.append(f"Social signal: {len(metrics['reddit_mentions'])} Reddit mentions detected.")

    lines.append("")

    # ROI SCENARIOS
    lines.append("ROI SCENARIOS (computed from signal data)")
    lines.append("-" * 40)
    lines.append(f"Bear Case:  {roi_bear:+.1%}")
    lines.append(f"Base Case:  {roi_base:+.1%}")
    lines.append(f"Bull Case:  {roi_bull:+.1%}")
    lines.append(f"Kelly f*:   {kelly:.2f} ({kelly*100:.0f}% of portfolio)")
    lines.append("")

    # LIFECYCLE POSITION
    lines.append("GOLD RUSH LIFECYCLE")
    lines.append("-" * 40)
    stages = ["EMERGING", "VALIDATING", "CONFIRMED", "SATURATED"]
    current_idx = {"emerging": 0, "validating": 1, "confirmed": 2, "saturated": 3}.get(lifecycle, 0)
    stage_line = ""
    for i, stage in enumerate(stages):
        if i == current_idx:
            stage_line += f" [{stage}] "
        else:
            stage_line += f"  {stage}  "
        if i < len(stages) - 1:
            stage_line += "→"
    lines.append(stage_line)
    lines.append("")

    # HITL DECISION
    lines.append("HITL DECISION REQUIRED")
    lines.append("-" * 40)
    lines.append(f"Status: {thesis.get('status', 'unknown').upper()}")
    lines.append(f"Confidence: {coherence/100:.0%}")
    lines.append("Action: Approve / Reject / Defer")
    lines.append("")
    lines.append(f"{'='*60}")

    return "\n".join(lines)


def write_all_theses(db_path: str = DEFAULT_DB_PATH) -> str:
    """Generate thesis narratives for all symbols with theses."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = dict_factory
    theses = conn.execute("SELECT DISTINCT symbol FROM theses ORDER BY symbol").fetchall()
    conn.close()

    all_text = []
    all_text.append(f"SOCIAL ARB — THESIS PORTFOLIO")
    all_text.append(f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    all_text.append(f"{'='*60}\n")

    for t in theses:
        text = write_thesis(t["symbol"], db_path)
        if text:
            all_text.append(text)
            all_text.append("\n")

    return "\n".join(all_text)


if __name__ == "__main__":
    output = write_all_theses()
    print(output)

    # Also save to file
    out_path = Path(__file__).parent.parent / "theses_report.txt"
    out_path.write_text(output)
    print(f"\nSaved to {out_path}")
