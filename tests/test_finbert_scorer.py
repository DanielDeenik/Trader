"""Tests for FinBERT sentiment scorer."""

import pytest
from social_arb.nlp.finbert_scorer import FinBertScorer, FINBERT_AVAILABLE


@pytest.fixture
def scorer():
    """Create scorer — skip if transformers not available."""
    if not FINBERT_AVAILABLE:
        pytest.skip("transformers/torch not installed")
    return FinBertScorer()


def test_finbert_available_flag():
    """Test that FINBERT_AVAILABLE is a boolean."""
    assert isinstance(FINBERT_AVAILABLE, bool)


def test_finbert_instantiate_without_model():
    """Test scorer can be created even without model loaded."""
    scorer = FinBertScorer(lazy_load=True)
    assert scorer is not None
    assert scorer.model_loaded is False


def test_finbert_score_positive(scorer):
    result = scorer.score("Revenue increased significantly, beating all analyst expectations")
    assert result["direction"] in ("bullish", "neutral", "bearish")
    assert "compound" in result
    assert "confidence" in result


def test_finbert_score_negative(scorer):
    result = scorer.score("Company reported massive losses and is facing bankruptcy")
    assert result["direction"] in ("bullish", "neutral", "bearish")
    assert "compound" in result


def test_finbert_empty_text():
    scorer = FinBertScorer(lazy_load=True)
    result = scorer.score("")
    assert result["compound"] == 0.0
    assert result["direction"] == "neutral"


def test_finbert_score_batch(scorer):
    results = scorer.score_batch([
        "Strong earnings growth reported",
        "Regulatory investigation announced",
    ])
    assert len(results) == 2
    for r in results:
        assert "direction" in r
        assert "compound" in r


def test_finbert_fallback_without_model():
    """Test that scoring without model returns neutral fallback."""
    scorer = FinBertScorer(lazy_load=True)
    # Don't load model — should return fallback
    result = scorer.score("Test text")
    assert result["direction"] == "neutral"
    assert result["confidence"] == 0.0
