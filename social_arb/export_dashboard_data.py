"""Export all DB data to a single JSON file for the dashboard.

Zero hardcoded values — everything comes from the SQLite database.
"""

import json
import sqlite3
from pathlib import Path
from datetime import datetime

from social_arb.db.schema import DEFAULT_DB_PATH


def dict_factory(cursor, row):
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}


def export_all(db_path: str = DEFAULT_DB_PATH, output_path: str = None) -> str:
    """Export signals, mosaics, theses, decisions, positions, scans to JSON."""
    if output_path is None:
        output_path = str(Path(db_path).parent.parent / "dashboard_data.json")

    conn = sqlite3.connect(db_path)
    conn.row_factory = dict_factory

    data = {
        "exported_at": datetime.utcnow().isoformat(),
        "signals": [],
        "mosaics": [],
        "theses": [],
        "decisions": [],
        "positions": [],
        "scans": [],
        "summary": {},
    }

    # Signals — all of them with raw data
    cur = conn.execute("""
        SELECT id, scan_id, timestamp, symbol, source, signal_type,
               direction, strength, confidence, data_class, raw_json
        FROM signals ORDER BY timestamp DESC
    """)
    data["signals"] = cur.fetchall()

    # Parse raw_json strings into objects
    for sig in data["signals"]:
        if sig.get("raw_json"):
            try:
                sig["raw"] = json.loads(sig["raw_json"])
            except (json.JSONDecodeError, TypeError):
                sig["raw"] = {}
        else:
            sig["raw"] = {}

    # Mosaics
    cur = conn.execute("""
        SELECT id, symbol, domain, coherence_score, divergence_strength,
               fragments_json, narrative, action, data_class, created_at
        FROM mosaics ORDER BY coherence_score DESC
    """)
    data["mosaics"] = cur.fetchall()

    for m in data["mosaics"]:
        if m.get("fragments_json"):
            try:
                m["fragments"] = json.loads(m["fragments_json"])
            except (json.JSONDecodeError, TypeError):
                m["fragments"] = []
        else:
            m["fragments"] = []

    # Theses
    cur = conn.execute("""
        SELECT id, mosaic_id, symbol, domain, roi_bear, roi_base, roi_bull,
               kelly_fraction, lifecycle_stage, status, vulnerability_json,
               simulation_json, created_at
        FROM theses ORDER BY created_at DESC
    """)
    data["theses"] = cur.fetchall()

    # Decisions
    cur = conn.execute("""
        SELECT id, thesis_id, gate, symbol, decision, confidence,
               rationale, trust_level, created_at
        FROM decisions ORDER BY created_at DESC
    """)
    data["decisions"] = cur.fetchall()

    # Positions
    cur = conn.execute("""
        SELECT id, thesis_id, symbol, domain, direction, allocation_pct,
               conviction, entry_price, entry_date, exit_price, exit_date,
               pnl, pnl_pct, status, data_class, created_at
        FROM positions ORDER BY entry_date DESC
    """)
    data["positions"] = cur.fetchall()

    # Scans
    cur = conn.execute("""
        SELECT id, scan_type, sources_json, symbols_json, signal_count,
               errors_json, status, started_at, completed_at
        FROM scans ORDER BY started_at DESC LIMIT 20
    """)
    data["scans"] = cur.fetchall()

    # Summary stats — all computed from data
    signal_count = len(data["signals"])
    sources = list(set(s["source"] for s in data["signals"]))
    symbols = list(set(s["symbol"] for s in data["signals"]))

    # Domain breakdown
    public_signals = [s for s in data["signals"] if s.get("data_class") == "public"]
    private_signals = [s for s in data["signals"] if s.get("data_class") == "private"]

    # Source breakdown
    source_counts = {}
    for s in data["signals"]:
        source_counts[s["source"]] = source_counts.get(s["source"], 0) + 1

    # Symbol strength ranking
    symbol_stats = {}
    for s in data["signals"]:
        sym = s["symbol"]
        if sym not in symbol_stats:
            symbol_stats[sym] = {"bullish": 0, "bearish": 0, "neutral": 0, "total": 0, "sources": set(), "avg_strength": 0, "strengths": []}
        symbol_stats[sym]["total"] += 1
        symbol_stats[sym][s.get("direction", "neutral")] += 1
        symbol_stats[sym]["sources"].add(s["source"])
        if s.get("strength"):
            symbol_stats[sym]["strengths"].append(s["strength"])

    for sym, st in symbol_stats.items():
        st["sources"] = list(st["sources"])
        st["avg_strength"] = sum(st["strengths"]) / len(st["strengths"]) if st["strengths"] else 0
        del st["strengths"]

    # Thesis status breakdown
    thesis_statuses = {}
    for t in data["theses"]:
        status = t.get("status", "unknown")
        thesis_statuses[status] = thesis_statuses.get(status, 0) + 1

    data["summary"] = {
        "total_signals": signal_count,
        "total_mosaics": len(data["mosaics"]),
        "total_theses": len(data["theses"]),
        "total_decisions": len(data["decisions"]),
        "total_positions": len(data["positions"]),
        "public_signals": len(public_signals),
        "private_signals": len(private_signals),
        "unique_sources": sources,
        "unique_symbols": symbols,
        "source_counts": source_counts,
        "symbol_stats": symbol_stats,
        "thesis_statuses": thesis_statuses,
        "last_scan": data["scans"][0] if data["scans"] else None,
    }

    conn.close()

    with open(output_path, "w") as f:
        json.dump(data, f, indent=2, default=str)

    print(f"Exported {signal_count} signals, {len(data['mosaics'])} mosaics, {len(data['theses'])} theses → {output_path}")
    return output_path


if __name__ == "__main__":
    export_all()
