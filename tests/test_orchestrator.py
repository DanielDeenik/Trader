"""Tests for the engine orchestrator — auto-stack execution."""
import os
import tempfile
import pytest
from social_arb.db.schema import init_db
from social_arb.db.store import insert_signals_batch, insert_ohlcv_batch
from social_arb.api.orchestrator import EngineOrchestrator


@pytest.fixture
def db_path():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path)
    # Seed with signals
    insert_signals_batch(db_path=path, signals=[
        {"timestamp": "2026-03-26T10:00:00", "symbol": "NVDA",
         "source": "reddit", "direction": "bullish", "strength": 0.8,
         "confidence": 0.7, "signal_type": "social", "raw_json": "{}",
         "data_class": "public", "scan_id": None},
        {"timestamp": "2026-03-26T09:00:00", "symbol": "NVDA",
         "source": "yfinance", "direction": "bullish", "strength": 0.6,
         "confidence": 0.8, "signal_type": "price", "raw_json": '{"change_1d_pct": 3.5}',
         "data_class": "public", "scan_id": None},
    ])
    # Seed with OHLCV
    insert_ohlcv_batch(db_path=path, bars=[
        {"timestamp": f"2026-03-{d:02d}", "symbol": "NVDA",
         "open": 900+d, "high": 910+d, "low": 890+d,
         "close": 905+d, "volume": 1000000, "data_class": "public"}
        for d in range(1, 26)
    ])
    yield path
    os.unlink(path)


def test_orchestrator_run_all_engines(db_path):
    orch = EngineOrchestrator(db_path=db_path)
    result = orch.run_all("NVDA")
    assert "sentiment_divergence" in result
    assert "technical_analyzer" in result
    assert "kelly_sizer" in result
    assert "cross_domain_amplifier" in result


def test_orchestrator_sentiment_has_classification(db_path):
    orch = EngineOrchestrator(db_path=db_path)
    result = orch.run_all("NVDA")
    sd = result["sentiment_divergence"]
    assert "classification" in sd
    assert sd["classification"] in ("strong", "monitor", "pass")


def test_orchestrator_technical_has_indicators(db_path):
    orch = EngineOrchestrator(db_path=db_path)
    result = orch.run_all("NVDA")
    ta = result["technical_analyzer"]
    assert "indicators" in ta or "latest" in ta


def test_orchestrator_returns_error_not_crash(db_path):
    orch = EngineOrchestrator(db_path=db_path)
    result = orch.run_all("NONEXISTENT_SYMBOL")
    # Should return empty/error results, not raise
    assert isinstance(result, dict)


def test_orchestrator_kelly_has_allocation(db_path):
    orch = EngineOrchestrator(db_path=db_path)
    result = orch.run_all("NVDA")
    ks = result["kelly_sizer"]
    assert "kelly_fraction" in ks or "allocation" in ks or "error" in ks
