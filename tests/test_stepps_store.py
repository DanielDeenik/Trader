"""Tests for STEPPS store functions."""
import json
import tempfile
import pytest
from social_arb.db.schema import init_db, DEFAULT_DB_PATH
from social_arb.db import store


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
def sample_signal(temp_db):
    """Insert a sample signal to reference."""
    signal_id = store.insert_signal(
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
    return signal_id


def test_insert_stepps_score(temp_db, sample_signal):
    """Test inserting a STEPPS score."""
    score_id = store.insert_stepps_score(
        signal_id=sample_signal,
        social_currency=0.8,
        triggers=0.7,
        emotion=0.9,
        public_visibility=0.6,
        practical_value=0.5,
        stories=0.85,
        composite=0.73,
        scored_by="classifier",
        model_version="rf_v1_2026-03-26",
        db_path=temp_db,
    )
    assert score_id > 0


def test_query_stepps_scores_by_signal(temp_db, sample_signal):
    """Test querying STEPPS scores for a signal."""
    store.insert_stepps_score(
        signal_id=sample_signal,
        social_currency=0.8,
        triggers=0.7,
        emotion=0.9,
        public_visibility=0.6,
        practical_value=0.5,
        stories=0.85,
        composite=0.73,
        scored_by="classifier",
        model_version="rf_v1_2026-03-26",
        db_path=temp_db,
    )
    scores = store.query_stepps_scores(
        signal_id=sample_signal,
        db_path=temp_db,
    )
    assert len(scores) == 1
    assert scores[0]["composite"] == 0.73


def test_insert_stepps_training(temp_db, sample_signal):
    """Test inserting STEPPS training data (human correction)."""
    train_id = store.insert_stepps_training(
        signal_id=sample_signal,
        social_currency=0.85,
        triggers=0.75,
        emotion=0.95,
        public_visibility=0.65,
        practical_value=0.55,
        stories=0.9,
        source="human_correction",
        db_path=temp_db,
    )
    assert train_id > 0


def test_query_stepps_training_for_retraining(temp_db, sample_signal):
    """Test querying all training data for model retraining."""
    store.insert_stepps_training(
        signal_id=sample_signal,
        social_currency=0.85,
        triggers=0.75,
        emotion=0.95,
        public_visibility=0.65,
        practical_value=0.55,
        stories=0.9,
        source="human_correction",
        db_path=temp_db,
    )
    training_data = store.query_stepps_training(db_path=temp_db)
    assert len(training_data) >= 1
    assert training_data[0]["signal_id"] == sample_signal


def test_query_stepps_scores_by_symbol(temp_db, sample_signal):
    """Test querying STEPPS scores for all signals of a symbol."""
    store.insert_stepps_score(
        signal_id=sample_signal,
        social_currency=0.8,
        triggers=0.7,
        emotion=0.9,
        public_visibility=0.6,
        practical_value=0.5,
        stories=0.85,
        composite=0.73,
        scored_by="classifier",
        model_version="rf_v1_2026-03-26",
        db_path=temp_db,
    )
    scores = store.query_stepps_scores_by_symbol(
        symbol="AAPL",
        db_path=temp_db,
    )
    assert len(scores) >= 1
    assert scores[0]["composite"] == 0.73
