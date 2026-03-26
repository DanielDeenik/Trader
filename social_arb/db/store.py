"""
Social Arb — Data Store Layer

Provides insert/query functions for all 12 tables.
All functions use keyword-only args with * and db_path defaults to DEFAULT_DB_PATH.
All insert functions return lastrowid.
All query functions return List[Dict] using dict(row) from sqlite3.Row or psycopg2.RealDictCursor.

Uses .adapter module to support both SQLite and PostgreSQL backends.
"""

import json
from typing import List, Dict, Optional
from datetime import datetime
from .schema import get_connection, DEFAULT_DB_PATH
from .adapter import get_placeholder


# TIER 2: RAW SIGNALS


def _make_placeholders(count: int) -> str:
    """Generate SQL placeholders for current backend."""
    ph = get_placeholder()
    return ", ".join([ph] * count)


def insert_signal(
    *,
    timestamp: str,
    symbol: str,
    source: str,
    direction: str,
    strength: float,
    confidence: float,
    signal_type: str,
    raw_json: str,
    data_class: str,
    scan_id: Optional[int] = None,
    db_path: str = DEFAULT_DB_PATH,
) -> int:
    """Insert a single signal row. Returns lastrowid."""
    with get_connection(db_path) as conn:
        ph = _make_placeholders(10)
        cursor = conn.execute(
            f"""
            INSERT INTO signals
            (timestamp, symbol, source, signal_type, direction, strength, confidence, raw_json, data_class, scan_id)
            VALUES ({ph})
            """,
            (timestamp, symbol, source, signal_type, direction, strength, confidence, raw_json, data_class, scan_id),
        )
        return cursor.lastrowid


def insert_signals_batch(
    *,
    signals: List[Dict],
    db_path: str = DEFAULT_DB_PATH,
) -> int:
    """
    Insert multiple signals in a transaction.
    signals: List of dicts with keys: timestamp, symbol, source, direction, strength, confidence, signal_type, raw_json, data_class, scan_id
    Returns count of inserted rows.
    """
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        ph = _make_placeholders(10)
        count = 0
        for sig in signals:
            cursor.execute(
                f"""
                INSERT INTO signals
                (timestamp, symbol, source, signal_type, direction, strength, confidence, raw_json, data_class, scan_id)
                VALUES ({ph})
                """,
                (
                    sig.get("timestamp"),
                    sig.get("symbol"),
                    sig.get("source"),
                    sig.get("signal_type", "general"),
                    sig.get("direction"),
                    sig.get("strength"),
                    sig.get("confidence"),
                    sig.get("raw_json"),
                    sig.get("data_class", "public"),
                    sig.get("scan_id"),
                ),
            )
            count += 1
        return count


def query_signals(
    *,
    symbol: Optional[str] = None,
    source: Optional[str] = None,
    data_class: Optional[str] = None,
    limit: int = 100,
    db_path: str = DEFAULT_DB_PATH,
) -> List[Dict]:
    """Query signals with optional filters. Returns list of dicts."""
    with get_connection(db_path) as conn:
        ph = get_placeholder()
        query = "SELECT * FROM signals WHERE 1=1"
        params = []

        if symbol:
            query += f" AND symbol = {ph}"
            params.append(symbol)
        if source:
            query += f" AND source = {ph}"
            params.append(source)
        if data_class:
            query += f" AND data_class = {ph}"
            params.append(data_class)

        query += f" ORDER BY timestamp DESC LIMIT {ph}"
        params.append(limit)

        cursor = conn.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]


# TIER 2: OHLCV


def insert_ohlcv_batch(
    *,
    bars: List[Dict],
    source: str = "yfinance",
    db_path: str = DEFAULT_DB_PATH,
) -> int:
    """
    Insert multiple OHLCV bars in a transaction.
    bars: List of dicts with keys: timestamp, symbol, open, high, low, close, volume, data_class
    Returns count of inserted rows (excluding duplicates).
    """
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        ph = _make_placeholders(9)
        count = 0
        for bar in bars:
            try:
                cursor.execute(
                    f"""
                    INSERT INTO ohlcv
                    (timestamp, symbol, open, high, low, close, volume, source, data_class)
                    VALUES ({ph})
                    """,
                    (
                        bar.get("timestamp"),
                        bar.get("symbol"),
                        bar.get("open"),
                        bar.get("high"),
                        bar.get("low"),
                        bar.get("close"),
                        bar.get("volume"),
                        source,
                        bar.get("data_class", "public"),
                    ),
                )
                count += 1
            except Exception:
                # Skip duplicate UNIQUE(timestamp, symbol, source) constraint violations
                pass
        return count


def query_ohlcv(
    *,
    symbol: str,
    limit: int = 100,
    db_path: str = DEFAULT_DB_PATH,
) -> List[Dict]:
    """Query OHLCV bars for a symbol. Returns list of dicts."""
    with get_connection(db_path) as conn:
        ph = get_placeholder()
        cursor = conn.execute(
            f"SELECT * FROM ohlcv WHERE symbol = {ph} ORDER BY timestamp DESC LIMIT {ph}",
            (symbol, limit),
        )
        return [dict(row) for row in cursor.fetchall()]


# TIER 3: MOSAICS


def insert_mosaic(
    *,
    symbol: str,
    domain: str,
    coherence_score: float,
    divergence_strength: float,
    fragments_json: str,
    narrative: str,
    action: str,
    data_class: str,
    scan_id: Optional[int] = None,
    db_path: str = DEFAULT_DB_PATH,
) -> int:
    """Insert a mosaic row. Returns lastrowid."""
    with get_connection(db_path) as conn:
        ph = _make_placeholders(9)
        cursor = conn.execute(
            f"""
            INSERT INTO mosaics
            (symbol, domain, coherence_score, divergence_strength, fragments_json, narrative, action, data_class, scan_id)
            VALUES ({ph})
            """,
            (symbol, domain, coherence_score, divergence_strength, fragments_json, narrative, action, data_class, scan_id),
        )
        return cursor.lastrowid


def query_mosaics(
    *,
    symbol: Optional[str] = None,
    action: Optional[str] = None,
    limit: int = 100,
    db_path: str = DEFAULT_DB_PATH,
) -> List[Dict]:
    """Query mosaics with optional filters. Returns list of dicts."""
    with get_connection(db_path) as conn:
        ph = get_placeholder()
        query = "SELECT * FROM mosaics WHERE 1=1"
        params = []

        if symbol:
            query += f" AND symbol = {ph}"
            params.append(symbol)
        if action:
            query += f" AND action = {ph}"
            params.append(action)

        query += f" ORDER BY created_at DESC LIMIT {ph}"
        params.append(limit)

        cursor = conn.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]


# TIER 3: THESES


def insert_thesis(
    *,
    mosaic_id: Optional[int],
    symbol: str,
    domain: str,
    roi_bear: float,
    roi_base: float,
    roi_bull: float,
    kelly_fraction: float,
    lifecycle_stage: str,
    status: str,
    vulnerability_json: str,
    simulation_json: str,
    thesis_type: str = "public",
    db_path: str = DEFAULT_DB_PATH,
) -> int:
    """Insert a thesis row. Returns lastrowid."""
    with get_connection(db_path) as conn:
        ph = _make_placeholders(12)
        cursor = conn.execute(
            f"""
            INSERT INTO theses
            (mosaic_id, symbol, domain, roi_bear, roi_base, roi_bull, kelly_fraction, lifecycle_stage, status, vulnerability_json, simulation_json, thesis_type)
            VALUES ({ph})
            """,
            (mosaic_id, symbol, domain, roi_bear, roi_base, roi_bull, kelly_fraction, lifecycle_stage, status, vulnerability_json, simulation_json, thesis_type),
        )
        return cursor.lastrowid


def query_theses(
    *,
    status: Optional[str] = None,
    symbol: Optional[str] = None,
    limit: int = 100,
    db_path: str = DEFAULT_DB_PATH,
) -> List[Dict]:
    """Query theses with optional filters. Returns list of dicts."""
    with get_connection(db_path) as conn:
        ph = get_placeholder()
        query = "SELECT * FROM theses WHERE 1=1"
        params = []

        if status:
            query += f" AND status = {ph}"
            params.append(status)
        if symbol:
            query += f" AND symbol = {ph}"
            params.append(symbol)

        query += f" ORDER BY created_at DESC LIMIT {ph}"
        params.append(limit)

        cursor = conn.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]


# TIER 4: DECISIONS (HITL Sacred)


def insert_decision(
    *,
    thesis_id: int,
    gate: str,
    symbol: str,
    decision: str,
    confidence: float,
    human_override: bool,
    rationale: str,
    trust_level: str,
    db_path: str = DEFAULT_DB_PATH,
) -> int:
    """
    Insert a decision row AND write to audit_trail (HITL sacred audit).
    Returns lastrowid of decision.
    """
    with get_connection(db_path) as conn:
        ph = get_placeholder()
        # Insert decision
        ph8 = _make_placeholders(8)
        cursor = conn.execute(
            f"""
            INSERT INTO decisions
            (thesis_id, gate, symbol, decision, confidence, human_override, rationale, trust_level)
            VALUES ({ph8})
            """,
            (thesis_id, gate, symbol, decision, confidence, human_override, rationale, trust_level),
        )
        decision_id = cursor.lastrowid

        # Write to audit_trail
        actor = "human" if human_override else "system"
        details = json.dumps(
            {
                "decision_id": decision_id,
                "decision": decision,
                "confidence": confidence,
                "trust_level": trust_level,
            }
        )
        ph5 = _make_placeholders(5)
        conn.execute(
            f"""
            INSERT INTO audit_trail
            (layer, action, symbol, actor, details_json)
            VALUES ({ph5})
            """,
            ("HITL", "decision", symbol, actor, details),
        )

        return decision_id


def query_decisions(
    *,
    symbol: Optional[str] = None,
    limit: int = 100,
    db_path: str = DEFAULT_DB_PATH,
) -> List[Dict]:
    """Query decisions with optional symbol filter. Returns list of dicts."""
    with get_connection(db_path) as conn:
        ph = get_placeholder()
        query = "SELECT * FROM decisions WHERE 1=1"
        params = []

        if symbol:
            query += f" AND symbol = {ph}"
            params.append(symbol)

        query += f" ORDER BY created_at DESC LIMIT {ph}"
        params.append(limit)

        cursor = conn.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]


# TIER 4: POSITIONS


def insert_position(
    *,
    thesis_id: int,
    symbol: str,
    domain: str,
    direction: str,
    allocation_pct: float,
    conviction: str,
    entry_price: float,
    entry_date: str,
    data_class: str,
    db_path: str = DEFAULT_DB_PATH,
) -> int:
    """Insert a position row. Returns lastrowid."""
    with get_connection(db_path) as conn:
        ph = _make_placeholders(9)
        cursor = conn.execute(
            f"""
            INSERT INTO positions
            (thesis_id, symbol, domain, direction, allocation_pct, conviction, entry_price, entry_date, data_class)
            VALUES ({ph})
            """,
            (thesis_id, symbol, domain, direction, allocation_pct, conviction, entry_price, entry_date, data_class),
        )
        return cursor.lastrowid


def query_positions(
    *,
    status: str = "open",
    limit: int = 100,
    db_path: str = DEFAULT_DB_PATH,
) -> List[Dict]:
    """Query positions by status. Returns list of dicts."""
    with get_connection(db_path) as conn:
        ph = get_placeholder()
        cursor = conn.execute(
            f"SELECT * FROM positions WHERE status = {ph} ORDER BY created_at DESC LIMIT {ph}",
            (status, limit),
        )
        return [dict(row) for row in cursor.fetchall()]


# TIER 5: SCANS (Meta)


def start_scan(
    *,
    scan_type: str,
    sources: List[str],
    symbols: List[str],
    db_path: str = DEFAULT_DB_PATH,
) -> int:
    """Start a new scan, return scan_id."""
    with get_connection(db_path) as conn:
        sources_json = json.dumps(sources)
        symbols_json = json.dumps(symbols)
        ph = _make_placeholders(3)
        cursor = conn.execute(
            f"""
            INSERT INTO scans
            (scan_type, sources_json, symbols_json, status)
            VALUES ({ph}, 'running')
            """,
            (scan_type, sources_json, symbols_json),
        )
        return cursor.lastrowid


def complete_scan(
    *,
    scan_id: int,
    signal_count: int,
    errors: List[str],
    db_path: str = DEFAULT_DB_PATH,
) -> None:
    """Mark a scan as completed."""
    with get_connection(db_path) as conn:
        errors_json = json.dumps(errors) if errors else None
        ph = get_placeholder()
        conn.execute(
            f"""
            UPDATE scans
            SET status = 'completed', signal_count = {ph}, errors_json = {ph}, completed_at = CURRENT_TIMESTAMP
            WHERE id = {ph}
            """,
            (signal_count, errors_json, scan_id),
        )
