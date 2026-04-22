"""Tests for instrument CRUD operations."""
import os
import tempfile
import pytest
from social_arb.db.schema import init_db
from social_arb.db.store import (
    insert_instrument, query_instruments, update_instrument,
    delete_instrument, query_data_freshness,
    insert_review, query_reviews,
)


@pytest.fixture
def db_path():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path)
    yield path
    os.unlink(path)


def test_insert_instrument(db_path):
    row_id = insert_instrument(
        db_path=db_path,
        symbol="NVDA",
        name="NVIDIA Corporation",
        type="stock",
        sector="Technology",
        exchange="NASDAQ",
        data_class="public",
    )
    assert row_id > 0


def test_query_instruments_empty(db_path):
    result = query_instruments(db_path=db_path)
    assert result == []


def test_query_instruments_after_insert(db_path):
    insert_instrument(
        db_path=db_path, symbol="NVDA", name="NVIDIA",
        type="stock", data_class="public",
    )
    insert_instrument(
        db_path=db_path, symbol="BTC", name="Bitcoin",
        type="crypto", data_class="public",
    )
    result = query_instruments(db_path=db_path)
    assert len(result) == 2
    symbols = [r["symbol"] for r in result]
    assert "NVDA" in symbols
    assert "BTC" in symbols


def test_query_instruments_by_type(db_path):
    insert_instrument(
        db_path=db_path, symbol="NVDA", name="NVIDIA",
        type="stock", data_class="public",
    )
    insert_instrument(
        db_path=db_path, symbol="BTC", name="Bitcoin",
        type="crypto", data_class="public",
    )
    stocks = query_instruments(db_path=db_path, type="stock")
    assert len(stocks) == 1
    assert stocks[0]["symbol"] == "NVDA"


def test_update_instrument(db_path):
    row_id = insert_instrument(
        db_path=db_path, symbol="NVDA", name="NVIDIA",
        type="stock", data_class="public",
    )
    update_instrument(
        db_path=db_path, instrument_id=row_id,
        sector="Semiconductors", market_cap_b=3200.0,
    )
    result = query_instruments(db_path=db_path, symbol="NVDA")
    assert result[0]["sector"] == "Semiconductors"
    assert result[0]["market_cap_b"] == 3200.0


def test_delete_instrument(db_path):
    row_id = insert_instrument(
        db_path=db_path, symbol="NVDA", name="NVIDIA",
        type="stock", data_class="public",
    )
    delete_instrument(db_path=db_path, instrument_id=row_id)
    result = query_instruments(db_path=db_path)
    assert len(result) == 0


def test_insert_duplicate_symbol_raises(db_path):
    insert_instrument(
        db_path=db_path, symbol="NVDA", name="NVIDIA",
        type="stock", data_class="public",
    )
    with pytest.raises(Exception):
        insert_instrument(
            db_path=db_path, symbol="NVDA", name="NVIDIA Dup",
            type="stock", data_class="public",
        )


def test_query_data_freshness(db_path):
    """Freshness query should return last signal timestamp per source per symbol."""
    from social_arb.db.store import insert_signals_batch
    insert_instrument(
        db_path=db_path, symbol="NVDA", name="NVIDIA",
        type="stock", data_class="public",
    )
    insert_signals_batch(
        db_path=db_path,
        signals=[{
            "timestamp": "2026-03-26T10:00:00",
            "symbol": "NVDA", "source": "yfinance",
            "direction": "bullish", "strength": 0.7,
            "confidence": 0.8, "signal_type": "price",
            "raw_json": "{}", "data_class": "public",
            "scan_id": None,
        }],
    )
    freshness = query_data_freshness(db_path=db_path, symbol="NVDA")
    assert len(freshness) >= 1
    assert freshness[0]["source"] == "yfinance"


def test_insert_review(db_path):
    row_id = insert_review(
        db_path=db_path,
        gate="entry",
        symbol="NVDA",
        entity_id=1,
        entity_type="thesis",
        scores_json='{"signal_coherence": 8.5}',
        total_score=8.5,
        threshold=12.0,
        decision="promote",
    )
    assert row_id > 0


def test_query_reviews_empty(db_path):
    result = query_reviews(db_path=db_path)
    assert result == []


def test_query_reviews_after_insert(db_path):
    insert_review(
        db_path=db_path,
        gate="entry",
        symbol="NVDA",
        entity_id=1,
        entity_type="thesis",
        scores_json='{"signal_coherence": 8.5}',
        total_score=8.5,
        decision="promote",
    )
    insert_review(
        db_path=db_path,
        gate="exit",
        symbol="BTC",
        entity_id=2,
        entity_type="position",
        scores_json='{"momentum": 6.0}',
        total_score=6.0,
        decision="hold",
    )
    result = query_reviews(db_path=db_path)
    assert len(result) == 2


def test_query_reviews_by_gate(db_path):
    insert_review(
        db_path=db_path,
        gate="entry",
        symbol="NVDA",
        entity_id=1,
        entity_type="thesis",
        scores_json='{"signal_coherence": 8.5}',
        total_score=8.5,
        decision="promote",
    )
    insert_review(
        db_path=db_path,
        gate="exit",
        symbol="BTC",
        entity_id=2,
        entity_type="position",
        scores_json='{"momentum": 6.0}',
        total_score=6.0,
        decision="hold",
    )
    entry_reviews = query_reviews(db_path=db_path, gate="entry")
    assert len(entry_reviews) == 1
    assert entry_reviews[0]["gate"] == "entry"
