"""Tests for task worker handlers."""
import asyncio
import json
import tempfile
import pytest
from unittest.mock import Mock, patch, MagicMock

from social_arb.db.schema import init_db
from social_arb.db import store
from social_arb.collectors.base import CollectorResult


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    init_db(db_path)
    yield db_path
    import os
    os.unlink(db_path)


@pytest.mark.asyncio
async def test_handle_collect_with_mocked_collector(temp_db):
    """Test collect handler with mocked collector."""
    from social_arb.tasks.workers import handle_collect

    # Insert a tracked instrument
    store.insert_instrument(
        symbol="AAPL", name="Apple Inc", type="stock", db_path=temp_db,
    )

    # Create mock collector result
    mock_result = CollectorResult(
        source="yfinance",
        signals=[
            {
                "timestamp": "2026-03-26T10:00:00Z",
                "symbol": "AAPL",
                "source": "yfinance",
                "direction": "bullish",
                "strength": 0.8,
                "confidence": 0.9,
                "signal_type": "price",
                "raw_json": "{}",
                "data_class": "public",
            }
        ],
        errors=[],
        symbols_scanned=["AAPL"],
    )

    mock_collector = Mock()
    mock_collector.collect.return_value = mock_result

    with patch('social_arb.tasks.workers.COLLECTORS', {'yfinance': mock_collector}):
        result = await handle_collect(
            params={"sources": ["yfinance"], "symbols": ["AAPL"], "domain": "public"},
            db_path=temp_db,
        )

    assert result["signal_count"] == 1
    assert len(result["errors"]) == 0
    assert result["source_results"]["yfinance"]["count"] == 1


@pytest.mark.asyncio
async def test_handle_collect_unknown_source(temp_db):
    """Test collect with unknown source."""
    from social_arb.tasks.workers import handle_collect

    result = await handle_collect(
        params={"sources": ["unknown_source"], "symbols": ["AAPL"]},
        db_path=temp_db,
    )

    assert result["signal_count"] == 0
    assert len(result["errors"]) > 0
    assert "unknown_source" in result["source_results"]


@pytest.mark.asyncio
async def test_handle_collect_no_symbols(temp_db):
    """Test collect with no symbols and no tracked instruments."""
    from social_arb.tasks.workers import handle_collect

    result = await handle_collect(
        params={"sources": ["yfinance"], "symbols": None},
        db_path=temp_db,
    )

    assert result["signal_count"] == 0
    assert len(result["errors"]) > 0


@pytest.mark.asyncio
async def test_handle_analyze_with_signals(temp_db):
    """Test analyze handler."""
    from social_arb.tasks.workers import handle_analyze

    # Insert some signals
    store.insert_signal(
        timestamp="2026-03-26T10:00:00Z",
        symbol="AAPL", source="yfinance",
        direction="bullish", strength=0.8, confidence=0.9,
        signal_type="price", raw_json="{}", data_class="public",
        db_path=temp_db,
    )

    with patch('social_arb.tasks.workers.run_analysis', return_value={"status": "ok"}):
        result = await handle_analyze(
            params={"symbols": ["AAPL"]},
            db_path=temp_db,
        )

    assert result["analyzed_count"] == 1
    assert len(result["errors"]) == 0


@pytest.mark.asyncio
async def test_handle_backfill_with_data(temp_db):
    """Test backfill handler."""
    from social_arb.tasks.workers import handle_backfill

    mock_result = CollectorResult(
        source="yfinance",
        signals=[
            {
                "timestamp": "2026-01-01T00:00:00Z",
                "symbol": "AAPL",
                "source": "yfinance",
                "direction": "neutral",
                "strength": 0.5,
                "confidence": 0.8,
                "signal_type": "price",
                "raw_json": "{}",
                "data_class": "public",
            }
        ],
        errors=[],
        symbols_scanned=["AAPL"],
    )

    mock_collector = Mock()
    mock_collector.collect.return_value = mock_result

    with patch('social_arb.tasks.workers.COLLECTORS', {'yfinance': mock_collector}):
        result = await handle_backfill(
            params={
                "source": "yfinance",
                "symbol": "AAPL",
                "start_date": "2026-01-01",
                "end_date": "2026-03-26",
            },
            db_path=temp_db,
        )

    assert result["bar_count"] == 1
    assert result["error"] is None


@pytest.mark.asyncio
async def test_handle_backfill_missing_params(temp_db):
    """Test backfill with missing parameters."""
    from social_arb.tasks.workers import handle_backfill

    result = await handle_backfill(
        params={"source": "yfinance"},  # missing symbol, dates
        db_path=temp_db,
    )

    assert result["bar_count"] == 0
    assert result["error"] is not None
