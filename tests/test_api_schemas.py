"""Tests for API Pydantic schemas — validation and serialization."""
import pytest
from social_arb.api.schemas import (
    InstrumentCreate, InstrumentResponse, InstrumentUpdate,
    SignalResponse, ReviewCreate, ReviewResponse,
    HealthResponse, SourceHealth,
    EngineResultResponse,
)


def test_instrument_create_valid():
    inst = InstrumentCreate(symbol="NVDA", name="NVIDIA", type="stock")
    assert inst.symbol == "NVDA"
    assert inst.data_class == "public"


def test_instrument_create_invalid_type():
    with pytest.raises(Exception):
        InstrumentCreate(symbol="X", name="X", type="banana")


def test_review_create_valid():
    review = ReviewCreate(
        gate="L1_triage", symbol="NVDA",
        entity_id=1, entity_type="signal_cluster",
        scores={"signal_quality": 4, "source_diversity": 3,
                "divergence_magnitude": 5, "timeliness": 4},
        decision="promote",
        dominant_narrative="Strong Reddit buzz",
    )
    assert review.total_score == 16
    assert review.threshold == 12.0


def test_review_create_l3_threshold():
    review = ReviewCreate(
        gate="L3_conviction", symbol="NVDA",
        entity_id=1, entity_type="thesis",
        scores={"conviction_level": 4, "risk_reward": 4,
                "timing_confidence": 3, "position_sizing": 4,
                "kill_criteria_clarity": 4},
        decision="execute",
    )
    assert review.threshold == 15.0


def test_health_response():
    health = HealthResponse(
        status="healthy",
        db_backend="sqlite",
        table_counts={"signals": 100, "mosaics": 10},
        source_health=[
            SourceHealth(source="yfinance", status="fresh",
                         last_signal="2026-03-26T10:00", signal_count=50),
        ],
    )
    assert health.status == "healthy"
    assert health.source_health[0].status == "fresh"
