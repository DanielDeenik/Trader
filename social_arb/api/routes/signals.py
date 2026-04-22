"""Signal queries and collection triggers."""

from fastapi import APIRouter
from pydantic import BaseModel
from datetime import datetime
from social_arb.api.deps import get_db_path
from social_arb.api.schemas import SignalResponse
from social_arb.db.store import query_signals, insert_signal
from social_arb.db.schema import get_connection

router = APIRouter()


class SignalCreate(BaseModel):
    """Request to create a signal manually."""
    symbol: str
    source: str  # manual, research, news, or other
    signal_type: str
    direction: str  # bullish, bearish, neutral
    strength: float  # 0-1
    confidence: float  # 0-1
    notes: str  # stored as raw_json


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


@router.post("/signals", response_model=dict, status_code=201)
def create_signal(body: SignalCreate):
    """Create a new signal manually."""
    signal_id = insert_signal(
        timestamp=datetime.utcnow().isoformat(),
        symbol=body.symbol,
        source=body.source,
        signal_type=body.signal_type,
        direction=body.direction,
        strength=body.strength,
        confidence=body.confidence,
        raw_json=body.notes,
        data_class="manual",
        db_path=get_db_path(),
    )
    return {"id": signal_id, "symbol": body.symbol, "source": body.source}


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
