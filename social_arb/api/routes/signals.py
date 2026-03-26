"""Signal queries and collection triggers."""

from fastapi import APIRouter
from social_arb.api.deps import get_db_path
from social_arb.api.schemas import SignalResponse
from social_arb.db.store import query_signals
from social_arb.db.schema import get_connection

router = APIRouter()


@router.get("/signals", response_model=list[SignalResponse])
def list_signals(
    symbol: str | None = None,
    source: str | None = None,
    data_class: str | None = None,
    limit: int = 500,
):
    """List signals with optional filters."""
    return query_signals(
        db_path=get_db_path(), symbol=symbol,
        source=source, data_class=data_class, limit=limit,
    )


@router.get("/signals/grouped")
def signals_grouped():
    """Signals grouped by symbol with counts and direction breakdown."""
    db_path = get_db_path()
    with get_connection(db_path) as conn:
        cursor = conn.execute("""
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
        return [dict(row) for row in cursor.fetchall()]
