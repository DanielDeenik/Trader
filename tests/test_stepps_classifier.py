"""Tests for STEPPS classifier."""
import json
import tempfile
import pytest
from social_arb.db.schema import init_db, DEFAULT_DB_PATH
from social_arb.db import store
from social_arb.engine.stepps_classifier import SteppsClassifier


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
def sample_signal_dict(temp_db):
    """Create a sample signal."""
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
    return {
        "id": signal_id,
        "strength": 0.75,
        "confidence": 0.8,
        "direction": "bullish",
        "source": "reddit",
        "signal_type": "general",
    }


def test_score_with_zero_training(temp_db, sample_signal_dict):
    """Test scoring with no training data (LLM or fallback)."""
    classifier = SteppsClassifier(db_path=temp_db)
    result = classifier.score(sample_signal_dict)

    assert result.signal_id == sample_signal_dict["id"]
    assert 0 <= result.composite <= 1
    assert result.scored_by in ("llm", "classifier")


def test_feature_engineering(temp_db, sample_signal_dict):
    """Test feature engineering converts signals to numeric features."""
    classifier = SteppsClassifier(db_path=temp_db)
    features = classifier._engineer_features(sample_signal_dict)

    assert len(features) == 5  # strength, confidence, direction, source, type
    assert all(isinstance(f, (int, float)) for f in features)


def test_classifier_to_dict(temp_db, sample_signal_dict):
    """Test SteppsResult.to_dict()."""
    classifier = SteppsClassifier(db_path=temp_db)
    result = classifier.score(sample_signal_dict)

    result_dict = result.to_dict()
    assert "signal_id" in result_dict
    assert "composite" in result_dict
    assert "scored_by" in result_dict


def test_train_insufficient_data(temp_db):
    """Test training with insufficient data."""
    classifier = SteppsClassifier(db_path=temp_db)
    result = classifier.train(db_path=temp_db)

    assert not result["success"]
    assert "Insufficient" in result.get("error", "")


def test_train_with_data(temp_db):
    """Test training with sufficient labeled examples."""
    classifier = SteppsClassifier(db_path=temp_db)

    # Create 15 training examples
    for i in range(15):
        signal_id = store.insert_signal(
            timestamp=f"2026-03-26T{i:02d}:00:00Z",
            symbol="AAPL",
            source="reddit",
            direction="bullish",
            strength=0.5 + (i * 0.02),
            confidence=0.7,
            signal_type="general",
            raw_json=json.dumps({"text": "test"}),
            data_class="public",
            db_path=temp_db,
        )

        store.insert_stepps_training(
            signal_id=signal_id,
            social_currency=0.6 + (i * 0.01),
            triggers=0.5,
            emotion=0.7,
            public_visibility=0.4,
            practical_value=0.5,
            stories=0.8,
            source="human_correction",
            db_path=temp_db,
        )

    result = classifier.train(db_path=temp_db)
    # Should succeed with 15 examples
    assert result["success"] or result["training_count"] > 0
