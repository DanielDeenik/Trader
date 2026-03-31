"""Health check endpoint — DB status, table counts, source freshness."""

from fastapi import APIRouter
from social_arb.api.deps import get_db_path
from social_arb.api.schemas import HealthResponse, SourceHealth
from social_arb.db.adapter import get_db_backend
from social_arb.db.schema import get_connection
from social_arb.db.store import query_data_freshness
from datetime import datetime, timedelta

router = APIRouter()

TABLES = ["signals", "mosaics", "theses", "decisions", "reviews",
          "positions", "ohlcv", "scans", "instruments", "audit_trail"]

STALE_HOURS = 24


@router.get("/health", response_model=HealthResponse)
def health_check():
    """System health: DB status, table row counts, source freshness."""
    db_path = get_db_path()
    backend = get_db_backend()

    # Table counts
    table_counts = {}
    try:
        with get_connection(db_path) as conn:
            for table in TABLES:
                row = conn.execute(f"SELECT COUNT(*) as c FROM {table}").fetchone()
                table_counts[table] = dict(row).get("c", 0)
    except Exception:
        return HealthResponse(
            status="unhealthy", db_backend=backend,
            table_counts={}, source_health=[],
        )

    # Source freshness
    freshness = query_data_freshness(db_path=db_path)
    now = datetime.utcnow()
    source_health = []
    for row in freshness:
        row_dict = dict(row)
        last = row_dict.get("last_signal", "")
        try:
            last_dt = datetime.fromisoformat(last.replace("Z", ""))
            age = now - last_dt
            status = "fresh" if age < timedelta(hours=STALE_HOURS) else "stale"
        except (ValueError, AttributeError):
            status = "stale"
        source_health.append(SourceHealth(
            source=row_dict["source"],
            status=status,
            last_signal=last,
            signal_count=row_dict.get("signal_count", 0),
        ))

    # Overall status
    total_rows = sum(table_counts.values())
    stale_sources = sum(1 for s in source_health if s.status == "stale")
    if total_rows == 0:
        status = "unhealthy"
    elif stale_sources > len(source_health) / 2 if source_health else False:
        status = "degraded"
    else:
        status = "healthy"

    return HealthResponse(
        status=status, db_backend=backend,
        table_counts=table_counts, source_health=source_health,
    )
