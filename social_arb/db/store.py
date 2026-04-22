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


def update_position(
    *,
    position_id: int,
    exit_price: float,
    exit_date: str,
    db_path: str = DEFAULT_DB_PATH,
) -> None:
    """Close a position by updating exit_price, exit_date, pnl, pnl_pct, and status."""
    with get_connection(db_path) as conn:
        # Get current position to calculate entry_price
        cursor = conn.execute(
            "SELECT entry_price FROM positions WHERE id = ?",
            (position_id,),
        )
        row = cursor.fetchone()
        if not row:
            raise ValueError(f"Position {position_id} not found")

        entry_price = row["entry_price"]
        pnl_pct = ((exit_price - entry_price) / entry_price * 100) if entry_price else 0
        pnl = exit_price - entry_price

        ph = get_placeholder()
        conn.execute(
            f"UPDATE positions SET exit_price = {ph}, exit_date = {ph}, pnl = {ph}, pnl_pct = {ph}, status = 'closed' WHERE id = {ph}",
            (exit_price, exit_date, pnl, pnl_pct, position_id),
        )
        conn.commit()


# TIER 1: INSTRUMENTS


def insert_instrument(
    *,
    symbol: str,
    name: str,
    type: str,
    sector: Optional[str] = None,
    vertical: Optional[str] = None,
    exchange: Optional[str] = None,
    market_cap_b: Optional[float] = None,
    data_class: str = "public",
    metadata_json: Optional[str] = None,
    db_path: str = DEFAULT_DB_PATH,
) -> int:
    """Insert an instrument. Returns lastrowid. Raises on duplicate symbol."""
    with get_connection(db_path) as conn:
        ph = _make_placeholders(9)
        cursor = conn.execute(
            f"""
            INSERT INTO instruments
            (symbol, name, type, sector, vertical, exchange, market_cap_b, data_class, metadata_json)
            VALUES ({ph})
            """,
            (symbol, name, type, sector, vertical, exchange, market_cap_b, data_class, metadata_json),
        )
        return cursor.lastrowid


def query_instruments(
    *,
    symbol: Optional[str] = None,
    type: Optional[str] = None,
    data_class: Optional[str] = None,
    search: Optional[str] = None,
    sector: Optional[str] = None,
    exchange: Optional[str] = None,
    limit: int = 0,
    offset: int = 0,
    db_path: str = DEFAULT_DB_PATH,
) -> List[Dict]:
    """Query instruments with optional filters, search, and pagination."""
    with get_connection(db_path) as conn:
        ph = get_placeholder()
        query = "SELECT * FROM instruments WHERE 1=1"
        params: list = []
        if symbol:
            query += f" AND symbol = {ph}"
            params.append(symbol)
        if type:
            query += f" AND type = {ph}"
            params.append(type)
        if data_class:
            query += f" AND data_class = {ph}"
            params.append(data_class)
        if sector:
            query += f" AND sector = {ph}"
            params.append(sector)
        if exchange:
            query += f" AND exchange = {ph}"
            params.append(exchange)
        if search:
            query += f" AND (symbol LIKE {ph} OR name LIKE {ph})"
            params.append(f"%{search}%")
            params.append(f"%{search}%")
        query += " ORDER BY symbol ASC"
        if limit > 0:
            query += f" LIMIT {ph} OFFSET {ph}"
            params.append(limit)
            params.append(offset)
        cursor = conn.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]


def count_instruments(
    *,
    symbol: Optional[str] = None,
    type: Optional[str] = None,
    data_class: Optional[str] = None,
    search: Optional[str] = None,
    sector: Optional[str] = None,
    exchange: Optional[str] = None,
    db_path: str = DEFAULT_DB_PATH,
) -> int:
    """Count instruments matching filters."""
    with get_connection(db_path) as conn:
        ph = get_placeholder()
        query = "SELECT COUNT(*) FROM instruments WHERE 1=1"
        params: list = []
        if symbol:
            query += f" AND symbol = {ph}"
            params.append(symbol)
        if type:
            query += f" AND type = {ph}"
            params.append(type)
        if data_class:
            query += f" AND data_class = {ph}"
            params.append(data_class)
        if sector:
            query += f" AND sector = {ph}"
            params.append(sector)
        if exchange:
            query += f" AND exchange = {ph}"
            params.append(exchange)
        if search:
            query += f" AND (symbol LIKE {ph} OR name LIKE {ph})"
            params.append(f"%{search}%")
            params.append(f"%{search}%")
        cursor = conn.execute(query, params)
        return cursor.fetchone()[0]


def get_instrument_facets(*, db_path: str = DEFAULT_DB_PATH) -> Dict:
    """Get distinct values for filter dropdowns."""
    with get_connection(db_path) as conn:
        sectors = [r[0] for r in conn.execute(
            "SELECT DISTINCT sector FROM instruments WHERE sector IS NOT NULL AND sector != '' ORDER BY sector"
        ).fetchall()]
        exchanges = [r[0] for r in conn.execute(
            "SELECT DISTINCT exchange FROM instruments WHERE exchange IS NOT NULL AND exchange != '' ORDER BY exchange"
        ).fetchall()]
        types = [r[0] for r in conn.execute(
            "SELECT DISTINCT type FROM instruments ORDER BY type"
        ).fetchall()]
        return {"sectors": sectors, "exchanges": exchanges, "types": types}


def update_instrument(
    *,
    instrument_id: int,
    sector: Optional[str] = None,
    vertical: Optional[str] = None,
    exchange: Optional[str] = None,
    market_cap_b: Optional[float] = None,
    metadata_json: Optional[str] = None,
    db_path: str = DEFAULT_DB_PATH,
) -> None:
    """Update mutable fields on an instrument."""
    with get_connection(db_path) as conn:
        ph = get_placeholder()
        updates = []
        params = []
        if sector is not None:
            updates.append(f"sector = {ph}")
            params.append(sector)
        if vertical is not None:
            updates.append(f"vertical = {ph}")
            params.append(vertical)
        if exchange is not None:
            updates.append(f"exchange = {ph}")
            params.append(exchange)
        if market_cap_b is not None:
            updates.append(f"market_cap_b = {ph}")
            params.append(market_cap_b)
        if metadata_json is not None:
            updates.append(f"metadata_json = {ph}")
            params.append(metadata_json)
        if not updates:
            return
        updates.append("updated_at = CURRENT_TIMESTAMP")
        params.append(instrument_id)
        conn.execute(
            f"UPDATE instruments SET {', '.join(updates)} WHERE id = {ph}",
            params,
        )


def delete_instrument(
    *,
    instrument_id: int,
    db_path: str = DEFAULT_DB_PATH,
) -> None:
    """Delete an instrument by ID."""
    with get_connection(db_path) as conn:
        ph = get_placeholder()
        conn.execute(f"DELETE FROM instruments WHERE id = {ph}", (instrument_id,))


def query_data_freshness(
    *,
    symbol: Optional[str] = None,
    db_path: str = DEFAULT_DB_PATH,
) -> List[Dict]:
    """Get latest signal timestamp per source per symbol for staleness tracking."""
    with get_connection(db_path) as conn:
        ph = get_placeholder()
        query = """
            SELECT symbol, source, MAX(timestamp) as last_signal,
                   COUNT(*) as signal_count
            FROM signals WHERE 1=1
        """
        params = []
        if symbol:
            query += f" AND symbol = {ph}"
            params.append(symbol)
        query += " GROUP BY symbol, source ORDER BY symbol, source"
        cursor = conn.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]


# TIER 3: REVIEWS (HITL)


def insert_review(
    *,
    gate: str,
    symbol: str,
    entity_id: int,
    entity_type: str,
    scores_json: str,
    total_score: float,
    threshold: float = 12.0,
    narrative: Optional[str] = None,
    dominant_narrative: Optional[str] = None,
    market_pricing: Optional[str] = None,
    invalidation: Optional[str] = None,
    decision: str,
    position_size: Optional[str] = None,
    risk_note: Optional[str] = None,
    db_path: str = DEFAULT_DB_PATH,
) -> int:
    """Insert a HITL review. Returns lastrowid."""
    with get_connection(db_path) as conn:
        ph = _make_placeholders(14)
        cursor = conn.execute(
            f"""
            INSERT INTO reviews
            (gate, symbol, entity_id, entity_type, scores_json, total_score,
             threshold, narrative, dominant_narrative, market_pricing,
             invalidation, decision, position_size, risk_note)
            VALUES ({ph})
            """,
            (gate, symbol, entity_id, entity_type, scores_json, total_score,
             threshold, narrative, dominant_narrative, market_pricing,
             invalidation, decision, position_size, risk_note),
        )
        return cursor.lastrowid


def query_reviews(
    *,
    gate: Optional[str] = None,
    symbol: Optional[str] = None,
    limit: int = 100,
    db_path: str = DEFAULT_DB_PATH,
) -> List[Dict]:
    """Query HITL reviews with optional filters."""
    with get_connection(db_path) as conn:
        ph = get_placeholder()
        query = "SELECT * FROM reviews WHERE 1=1"
        params = []
        if gate:
            query += f" AND gate = {ph}"
            params.append(gate)
        if symbol:
            query += f" AND symbol = {ph}"
            params.append(symbol)
        query += f" ORDER BY created_at DESC LIMIT {ph}"
        params.append(limit)
        cursor = conn.execute(query, params)
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


# TIER 5: TASKS (META)


def insert_task(
    *,
    task_type: str,
    params_json: str,
    max_attempts: int = 3,
    db_path: str = DEFAULT_DB_PATH,
) -> int:
    """Insert a new task with 'pending' status. Returns task id."""
    with get_connection(db_path) as conn:
        ph = _make_placeholders(4)
        cursor = conn.execute(
            f"""
            INSERT INTO tasks
            (task_type, status, params_json, max_attempts)
            VALUES ({ph})
            """,
            (task_type, "pending", params_json, max_attempts),
        )
        return cursor.lastrowid


def query_tasks(
    *,
    limit: int = 100,
    db_path: str = DEFAULT_DB_PATH,
) -> List[Dict]:
    """Query all tasks, most recent first. Returns list of dicts."""
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """
            SELECT * FROM tasks
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,),
        )
        return [dict(row) for row in cursor.fetchall()]


def query_tasks_by_status(
    *,
    status: str,
    limit: int = 100,
    db_path: str = DEFAULT_DB_PATH,
) -> List[Dict]:
    """Query tasks by status. Returns list of dicts ordered by created_at."""
    with get_connection(db_path) as conn:
        ph = get_placeholder()
        cursor = conn.execute(
            f"""
            SELECT * FROM tasks
            WHERE status = {ph}
            ORDER BY created_at ASC
            LIMIT ?
            """,
            (status, limit),
        )
        return [dict(row) for row in cursor.fetchall()]


def claim_task(
    *,
    db_path: str = DEFAULT_DB_PATH,
) -> Optional[Dict]:
    """
    Atomically claim the next pending task.
    Updates it to 'running' status and returns the task dict.
    Returns None if no pending tasks exist.
    """
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """
            SELECT id FROM tasks
            WHERE status = 'pending' AND (next_retry_at IS NULL OR next_retry_at <= datetime('now'))
            ORDER BY created_at ASC
            LIMIT 1
            """
        )
        row = cursor.fetchone()
        if not row:
            return None

        task_id = dict(row)["id"]
        cursor.execute(
            """
            UPDATE tasks
            SET status = 'running'
            WHERE id = ?
            """,
            (task_id,),
        )
        conn.commit()

        # Fetch and return the updated task
        cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        return dict(cursor.fetchone())


def update_task_started_at(
    *,
    task_id: int,
    started_at: str,
    db_path: str = DEFAULT_DB_PATH,
) -> None:
    """Update the started_at timestamp for a task."""
    with get_connection(db_path) as conn:
        ph = get_placeholder()
        conn.execute(
            f"""
            UPDATE tasks
            SET started_at = {ph}
            WHERE id = {ph}
            """,
            (started_at, task_id),
        )
        conn.commit()


def complete_task(
    *,
    task_id: int,
    result_json: str,
    db_path: str = DEFAULT_DB_PATH,
) -> None:
    """Mark task as completed with result."""
    with get_connection(db_path) as conn:
        now = datetime.utcnow().isoformat()
        ph = get_placeholder()
        conn.execute(
            f"""
            UPDATE tasks
            SET status = 'completed', result_json = {ph}, completed_at = {ph}
            WHERE id = {ph}
            """,
            (result_json, now, task_id),
        )
        conn.commit()


def fail_task(
    *,
    task_id: int,
    error: str,
    next_retry_at: Optional[str] = None,
    db_path: str = DEFAULT_DB_PATH,
) -> None:
    """Mark task as failed, increment attempts, set next_retry_at."""
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        # Get current attempts
        cursor.execute("SELECT attempts, max_attempts FROM tasks WHERE id = ?", (task_id,))
        row = cursor.fetchone()
        if not row:
            return

        row_dict = dict(row)
        current_attempts = (row_dict["attempts"] or 0) + 1
        max_attempts = row_dict["max_attempts"] or 3

        # If exhausted, mark as failed; otherwise keep as 'pending' for retry
        new_status = "failed" if current_attempts >= max_attempts else "pending"

        ph = get_placeholder()
        cursor.execute(
            f"""
            UPDATE tasks
            SET status = {ph}, error = {ph}, attempts = {ph}, next_retry_at = {ph}
            WHERE id = {ph}
            """,
            (new_status, error, current_attempts, next_retry_at, task_id),
        )
        conn.commit()


def query_source_health(
    *,
    hours: int = 24,
    db_path: str = DEFAULT_DB_PATH,
) -> List[Dict]:
    """
    Query per-source health based on recent signals.
    Returns list of dicts with: source, signal_count, avg_confidence, last_timestamp, status.
    """
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            f"""
            SELECT
                source,
                COUNT(*) as signal_count,
                ROUND(AVG(confidence), 2) as avg_confidence,
                MAX(timestamp) as last_timestamp,
                CASE
                    WHEN COUNT(*) > 0 AND ROUND(AVG(confidence), 2) > 0.7 THEN 'healthy'
                    WHEN COUNT(*) > 0 THEN 'degraded'
                    ELSE 'unknown'
                END as status
            FROM signals
            WHERE datetime(timestamp) > datetime('now', '-{hours} hours')
            GROUP BY source
            ORDER BY signal_count DESC
            """
        )
        return [dict(row) for row in cursor.fetchall()]


# ─── TIER 3: STEPPS SCORES & TRAINING ───────────────────────────────────────


def insert_stepps_score(
    *,
    signal_id: int,
    social_currency: float,
    triggers: float,
    emotion: float,
    public_visibility: float,
    practical_value: float,
    stories: float,
    composite: float,
    scored_by: str = "classifier",
    model_version: Optional[str] = None,
    db_path: str = DEFAULT_DB_PATH,
) -> int:
    """Insert a STEPPS score row. Returns lastrowid."""
    with get_connection(db_path) as conn:
        ph = _make_placeholders(11)
        cursor = conn.execute(
            f"""
            INSERT INTO stepps_scores
            (signal_id, social_currency, triggers, emotion, public_visibility, practical_value, stories, composite, scored_by, model_version, created_at)
            VALUES ({ph})
            """,
            (signal_id, social_currency, triggers, emotion, public_visibility, practical_value, stories, composite, scored_by, model_version, datetime.utcnow().isoformat() + "Z"),
        )
        return cursor.lastrowid


def query_stepps_scores(
    *,
    signal_id: Optional[int] = None,
    scored_by: Optional[str] = None,
    limit: int = 100,
    db_path: str = DEFAULT_DB_PATH,
) -> List[Dict]:
    """Query STEPPS scores with optional filters. Returns list of dicts."""
    with get_connection(db_path) as conn:
        ph = get_placeholder()
        query = "SELECT * FROM stepps_scores WHERE 1=1"
        params = []

        if signal_id is not None:
            query += f" AND signal_id = {ph}"
            params.append(signal_id)
        if scored_by:
            query += f" AND scored_by = {ph}"
            params.append(scored_by)

        query += f" ORDER BY created_at DESC LIMIT {ph}"
        params.append(limit)

        cursor = conn.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]


def query_stepps_scores_by_symbol(
    *,
    symbol: str,
    limit: int = 100,
    db_path: str = DEFAULT_DB_PATH,
) -> List[Dict]:
    """Query STEPPS scores for all signals of a symbol."""
    with get_connection(db_path) as conn:
        ph = get_placeholder()
        cursor = conn.execute(
            f"""
            SELECT ss.* FROM stepps_scores ss
            JOIN signals s ON ss.signal_id = s.id
            WHERE s.symbol = {ph}
            ORDER BY ss.composite DESC LIMIT {ph}
            """,
            (symbol, limit),
        )
        return [dict(row) for row in cursor.fetchall()]


def insert_stepps_training(
    *,
    signal_id: int,
    social_currency: float,
    triggers: float,
    emotion: float,
    public_visibility: float,
    practical_value: float,
    stories: float,
    source: str = "human_correction",
    db_path: str = DEFAULT_DB_PATH,
) -> int:
    """Insert STEPPS training data (ground truth from human correction). Returns lastrowid."""
    with get_connection(db_path) as conn:
        ph = _make_placeholders(9)
        cursor = conn.execute(
            f"""
            INSERT INTO stepps_training
            (signal_id, social_currency, triggers, emotion, public_visibility, practical_value, stories, source, created_at)
            VALUES ({ph})
            """,
            (signal_id, social_currency, triggers, emotion, public_visibility, practical_value, stories, source, datetime.utcnow().isoformat() + "Z"),
        )
        return cursor.lastrowid


def query_stepps_training(
    *,
    source: Optional[str] = None,
    limit: int = 10000,
    db_path: str = DEFAULT_DB_PATH,
) -> List[Dict]:
    """Query STEPPS training data (for model retraining). Returns list of dicts."""
    with get_connection(db_path) as conn:
        ph = get_placeholder()
        query = "SELECT * FROM stepps_training WHERE 1=1"
        params = []

        if source:
            query += f" AND source = {ph}"
            params.append(source)

        query += f" ORDER BY created_at DESC LIMIT {ph}"
        params.append(limit)

        cursor = conn.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]


# LATTICE: HITL Graph Visualization


def insert_lattice_node(
    *,
    symbol: str,
    node_id: str,
    node_type: str,
    label: str,
    data_json: Optional[str] = None,
    db_path: str = DEFAULT_DB_PATH,
) -> int:
    """Insert a lattice node. Returns lastrowid."""
    with get_connection(db_path) as conn:
        ph = _make_placeholders(5)
        cursor = conn.execute(
            f"""
            INSERT INTO lattice_nodes
            (symbol, node_id, node_type, label, data_json)
            VALUES ({ph})
            """,
            (symbol, node_id, node_type, label, data_json),
        )
        return cursor.lastrowid


def query_lattice_nodes(
    *,
    symbol: str,
    db_path: str = DEFAULT_DB_PATH,
) -> List[Dict]:
    """Query all lattice nodes for a symbol. Returns list of dicts."""
    with get_connection(db_path) as conn:
        ph = get_placeholder()
        cursor = conn.execute(
            f"SELECT * FROM lattice_nodes WHERE symbol = {ph} ORDER BY created_at ASC",
            (symbol,),
        )
        return [dict(row) for row in cursor.fetchall()]


def insert_lattice_edge(
    *,
    symbol: str,
    edge_id: str,
    source_node_id: str,
    target_node_id: str,
    label: Optional[str] = None,
    db_path: str = DEFAULT_DB_PATH,
) -> int:
    """Insert a lattice edge. Returns lastrowid."""
    with get_connection(db_path) as conn:
        ph = _make_placeholders(5)
        cursor = conn.execute(
            f"""
            INSERT INTO lattice_edges
            (symbol, edge_id, source_node_id, target_node_id, label)
            VALUES ({ph})
            """,
            (symbol, edge_id, source_node_id, target_node_id, label),
        )
        return cursor.lastrowid


def query_lattice_edges(
    *,
    symbol: str,
    db_path: str = DEFAULT_DB_PATH,
) -> List[Dict]:
    """Query all lattice edges for a symbol. Returns list of dicts."""
    with get_connection(db_path) as conn:
        ph = get_placeholder()
        cursor = conn.execute(
            f"SELECT * FROM lattice_edges WHERE symbol = {ph} ORDER BY created_at ASC",
            (symbol,),
        )
        return [dict(row) for row in cursor.fetchall()]


def count_stepps_training(
    *,
    db_path: str = DEFAULT_DB_PATH,
) -> int:
    """Count total STEPPS training records (for cold-start detection)."""
    with get_connection(db_path) as conn:
        cursor = conn.execute("SELECT COUNT(*) as cnt FROM stepps_training")
        return cursor.fetchone()["cnt"]
