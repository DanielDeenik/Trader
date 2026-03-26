"""Database helpers for the Streamlit app — shared across all pages."""

import json
from social_arb.db.adapter import get_connection, get_db_backend, get_placeholder
from social_arb.db.schema import init_db


def ensure_db():
    """Initialize DB schema (idempotent)."""
    init_db()


def query(sql, params=None):
    """Execute a read query, return list of dicts."""
    with get_connection() as conn:
        cur = conn.execute(sql, params or ())
        rows = cur.fetchall()
        return [dict(r) for r in rows]


def query_one(sql, params=None):
    """Execute a read query, return single dict."""
    with get_connection() as conn:
        cur = conn.execute(sql, params or ())
        row = cur.fetchone()
        return dict(row) if row else {}


def execute(sql, params=None):
    """Execute a write query."""
    with get_connection() as conn:
        conn.execute(sql, params or ())
        conn.commit()


def ph():
    """Get placeholder for current backend."""
    return get_placeholder()


def parse_json(val):
    """Safely parse JSON string."""
    if not val:
        return {}
    try:
        return json.loads(val) if isinstance(val, str) else val
    except (json.JSONDecodeError, TypeError):
        return {}


# ─── DOMAIN QUERIES ────────────────────────────────────────────────────────────

def get_signals(symbol=None, source=None, limit=500):
    """Get signals with optional filters."""
    p = ph()
    sql = "SELECT * FROM signals WHERE 1=1"
    args = []
    if symbol:
        sql += f" AND symbol = {p}"
        args.append(symbol)
    if source:
        sql += f" AND source = {p}"
        args.append(source)
    sql += f" ORDER BY timestamp DESC LIMIT {p}"
    args.append(limit)
    rows = query(sql, tuple(args))
    for r in rows:
        r["raw_json"] = parse_json(r.get("raw_json"))
    return rows


def get_signals_grouped():
    """Get signals grouped by symbol with counts."""
    return query("""
        SELECT symbol,
               COUNT(*) as total,
               SUM(CASE WHEN direction = 'bullish' THEN 1 ELSE 0 END) as bullish,
               SUM(CASE WHEN direction = 'bearish' THEN 1 ELSE 0 END) as bearish,
               SUM(CASE WHEN direction = 'neutral' THEN 1 ELSE 0 END) as neutral,
               COUNT(DISTINCT source) as source_count,
               GROUP_CONCAT(DISTINCT source) as sources,
               MAX(timestamp) as latest_signal
        FROM signals
        GROUP BY symbol
        ORDER BY total DESC
    """)


def get_mosaics(symbol=None):
    """Get mosaics with optional symbol filter."""
    if symbol:
        p = ph()
        rows = query(f"SELECT * FROM mosaics WHERE symbol = {p} ORDER BY created_at DESC", (symbol,))
    else:
        rows = query("SELECT * FROM mosaics ORDER BY coherence_score DESC")
    for r in rows:
        r["fragments_json"] = parse_json(r.get("fragments_json"))
    return rows


def get_theses(symbol=None, status=None):
    """Get theses with optional filters."""
    p = ph()
    sql = "SELECT * FROM theses WHERE 1=1"
    args = []
    if symbol:
        sql += f" AND symbol = {p}"
        args.append(symbol)
    if status:
        sql += f" AND status = {p}"
        args.append(status)
    sql += " ORDER BY created_at DESC"
    return query(sql, tuple(args))


def get_ohlcv(symbol, limit=365):
    """Get OHLCV data for a symbol."""
    p = ph()
    return query(
        f"SELECT * FROM ohlcv WHERE symbol = {p} ORDER BY timestamp ASC LIMIT {p}",
        (symbol, limit),
    )


def get_ohlcv_summary():
    """Get OHLCV summary per symbol."""
    return query("""
        SELECT symbol, COUNT(*) as bars,
               MIN(timestamp) as first_bar, MAX(timestamp) as last_bar,
               source
        FROM ohlcv GROUP BY symbol ORDER BY bars DESC
    """)


def get_positions(status=None):
    """Get positions with optional status filter."""
    if status:
        p = ph()
        return query(f"SELECT * FROM positions WHERE status = {p} ORDER BY created_at DESC", (status,))
    return query("SELECT * FROM positions ORDER BY created_at DESC")


def get_reviews(gate=None, symbol=None):
    """Get HITL reviews with optional filters."""
    p = ph()
    sql = "SELECT * FROM reviews WHERE 1=1"
    args = []
    if gate:
        sql += f" AND gate = {p}"
        args.append(gate)
    if symbol:
        sql += f" AND symbol = {p}"
        args.append(symbol)
    sql += " ORDER BY created_at DESC"
    return query(sql, tuple(args))


def save_review(gate, symbol, entity_id, entity_type, scores_json, total_score,
                threshold, narrative, dominant_narrative, market_pricing,
                invalidation, decision, position_size=None, risk_note=None):
    """Save a HITL review to the database."""
    p = ph()
    execute(
        f"""INSERT INTO reviews
            (gate, symbol, entity_id, entity_type, scores_json, total_score,
             threshold, narrative, dominant_narrative, market_pricing,
             invalidation, decision, position_size, risk_note)
            VALUES ({','.join([p]*14)})""",
        (gate, symbol, entity_id, entity_type,
         json.dumps(scores_json) if isinstance(scores_json, dict) else scores_json,
         total_score, threshold, narrative, dominant_narrative, market_pricing,
         invalidation, decision, position_size, risk_note),
    )


def get_scan_summary():
    """Get latest scan info."""
    rows = query("SELECT * FROM scans ORDER BY started_at DESC LIMIT 5")
    for r in rows:
        r["sources_json"] = parse_json(r.get("sources_json"))
        r["symbols_json"] = parse_json(r.get("symbols_json"))
        r["errors_json"] = parse_json(r.get("errors_json"))
    return rows


def count_table(table):
    """Get row count for a table."""
    return query_one(f"SELECT COUNT(*) as c FROM {table}").get("c", 0)
