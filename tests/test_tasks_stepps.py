"""Tests for STEPPS task handlers."""
import json
import tempfile
import asyncio
import pytest
from social_arb.db.schema import init_db, DEFAULT_DB_PATH
from social_arb.db import store
from social_arb.tasks.workers import handle_train_stepps


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
async def test_handle_train_stepps_no_data(temp_db):
    """Test STEPPS training with insufficient data."""
    result = await handle_train_stepps(params={}, db_path=temp_db)

    assert not result["success"]
    assert "Insufficient" in result.get("error", "")


@pytest.mark.asyncio
async def test_handle_train_stepps_with_data(temp_db):
    """Test STEPPS training with sufficient labeled examples."""
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

    result = await handle_train_stepps(params={}, db_path=temp_db)

    assert isinstance(result, dict)
    assert "success" in result
