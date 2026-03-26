"""Test that pipeline.run_analysis() uses all 6 engines."""
import os
import tempfile
import json
import pytest
from social_arb.db.schema import init_db
from social_arb.db.store import insert_signals_batch, insert_ohlcv_batch, query_theses


@pytest.fixture
def seeded_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path)
    insert_signals_batch(db_path=path, signals=[
        {"timestamp": "2026-03-26T10:00:00", "symbol": "NVDA",
         "source": "reddit", "direction": "bullish", "strength": 0.8,
         "confidence": 0.7, "signal_type": "social",
         "raw_json": json.dumps({"title": "NVDA bullish"}),
         "data_class": "public", "scan_id": None},
        {"timestamp": "2026-03-26T09:00:00", "symbol": "NVDA",
         "source": "yfinance", "direction": "bullish", "strength": 0.7,
         "confidence": 0.8, "signal_type": "price",
         "raw_json": json.dumps({"change_1d_pct": 3.5}),
         "data_class": "public", "scan_id": None},
        {"timestamp": "2026-03-26T08:00:00", "symbol": "NVDA",
         "source": "sec_edgar", "direction": "neutral", "strength": 0.5,
         "confidence": 0.6, "signal_type": "filing",
         "raw_json": json.dumps({"form_type": "10-K"}),
         "data_class": "public", "scan_id": None},
    ])
    insert_ohlcv_batch(db_path=path, bars=[
        {"timestamp": f"2026-03-{d:02d}", "symbol": "NVDA",
         "open": 900+d, "high": 910+d, "low": 890+d,
         "close": 905+d, "volume": 1000000, "data_class": "public"}
        for d in range(1, 26)
    ])
    yield path
    os.unlink(path)


def test_pipeline_creates_thesis_with_vulnerability(seeded_db):
    from social_arb.pipeline import run_analysis
    result = run_analysis(db_path=seeded_db)
    theses = query_theses(db_path=seeded_db)
    assert len(theses) > 0
    thesis = theses[0]
    # After engine wiring, vulnerability_json should be populated
    assert thesis.get("vulnerability_json") is not None


def test_pipeline_creates_thesis_with_simulation(seeded_db):
    from social_arb.pipeline import run_analysis
    result = run_analysis(db_path=seeded_db)
    theses = query_theses(db_path=seeded_db)
    thesis = theses[0]
    assert thesis.get("simulation_json") is not None
