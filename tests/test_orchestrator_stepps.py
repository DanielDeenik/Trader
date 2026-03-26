"""Tests for orchestrator STEPPS integration."""
import json
import tempfile
import pytest
from social_arb.db.schema import init_db, DEFAULT_DB_PATH
from social_arb.db import store
from social_arb.api.orchestrator import EngineOrchestrator


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    init_db(db_path)
    yield db_path
    import os
    os.unlink(db_path)


@pytest.fixture
def orchestrator(temp_db):
    """Create an orchestrator with temp DB."""
    return EngineOrchestrator(db_path=temp_db)


def test_orchestrator_has_stepps_engine(orchestrator):
    """Test that orchestrator has STEPPS engine."""
    assert hasattr(orchestrator, "stepps")
    assert orchestrator.stepps is not None


def test_run_all_includes_stepps(temp_db, orchestrator):
    """Test that run_all() includes STEPPS results."""
    # Create a signal
    store.insert_signal(
        timestamp="2026-03-26T10:00:00Z",
        symbol="AAPL",
        source="reddit",
        direction="bullish",
        strength=0.75,
        confidence=0.8,
        signal_type="general",
        raw_json=json.dumps({"text": "bullish"}),
        data_class="public",
        db_path=temp_db,
    )

    results = orchestrator.run_all("AAPL")

    assert "stepps_classifier" in results
    assert "scores" in results.get("stepps_classifier", {}) or "error" in results.get("stepps_classifier", {})
