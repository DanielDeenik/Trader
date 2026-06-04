"""
Trends API Routes — Serves the Gummy Search-style trend dashboard.

All data comes from real DB queries via trend_scorer engine.
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, Query

from ...api.deps import get_db_path
from ...engine.trend_scorer import (
    get_trending_tickers,
    get_divergence_alerts,
    get_similar_trends,
    get_ticker_deep_dive,
    get_overview_stats,
)

router = APIRouter(prefix="/trends", tags=["trends"])


@router.get("/tickers")
async def trending_tickers(
    hours: int = Query(168, gt=0),
    limit: int = Query(50, ge=1, le=500),
    domain: Optional[str] = None,
):
    """Trending tickers ranked by trend score."""
    db_path = get_db_path()
    return get_trending_tickers(db_path, hours=hours, limit=limit, domain_filter=domain)


@router.get("/alerts")
async def divergence_alerts(
    min_divergence: float = Query(0.15, ge=0.0, le=1.0),
    limit: int = Query(10, ge=1, le=500),
):
    """Tickers with highest social-vs-market divergence."""
    db_path = get_db_path()
    return get_divergence_alerts(db_path, min_divergence=min_divergence, limit=limit)


@router.get("/themes")
async def theme_clusters(limit: int = Query(20, ge=1, le=500)):
    """Similar trend clusters — tickers grouped by shared narrative/sector."""
    db_path = get_db_path()
    return get_similar_trends(db_path, limit=limit)


@router.get("/ticker/{symbol}")
async def ticker_deep_dive(symbol: str):
    """Full deep dive for a single ticker."""
    db_path = get_db_path()
    result = get_ticker_deep_dive(db_path, symbol=symbol.upper())
    if not result or not result.get("signals", {}).get("total"):
        raise HTTPException(404, f"No data found for {symbol.upper()}")
    return result


@router.get("/stats")
async def overview_stats():
    """Dashboard top-level stats."""
    db_path = get_db_path()
    return get_overview_stats(db_path)
