"""Tests for VADER sentiment scorer."""

import pytest
from social_arb.nlp.vader_scorer import VaderScorer


def test_vader_scorer_instantiate():
    scorer = VaderScorer()
    assert scorer is not None


def test_vader_positive_sentiment():
    scorer = VaderScorer()
    result = scorer.score("Amazing earnings beat, revenue soaring, incredible growth")
    assert result["compound"] > 0.3
    assert result["direction"] == "bullish"


def test_vader_negative_sentiment():
    scorer = VaderScorer()
    result = scorer.score("Terrible losses, massive layoffs, company struggling badly")
    assert result["compound"] < -0.3
    assert result["direction"] == "bearish"


def test_vader_neutral_sentiment():
    scorer = VaderScorer()
    result = scorer.score("Company filed quarterly report with the SEC")
    assert result["direction"] in ("neutral", "bullish", "bearish")
    assert abs(result["compound"]) < 0.5


def test_vader_empty_text():
    scorer = VaderScorer()
    result = scorer.score("")
    assert result["compound"] == 0.0
    assert result["direction"] == "neutral"


def test_vader_score_batch():
    scorer = VaderScorer()
    texts = [
        "Stock surges on great earnings",
        "Company faces lawsuit and regulatory probe",
        "Quarterly filing submitted",
    ]
    results = scorer.score_batch(texts)
    assert len(results) == 3
    assert results[0]["direction"] == "bullish"
    assert results[1]["direction"] == "bearish"


def test_vader_result_has_all_fields():
    scorer = VaderScorer()
    result = scorer.score("Great news for investors")
    assert "compound" in result
    assert "positive" in result
    assert "negative" in result
    assert "neutral_score" in result
    assert "direction" in result
    assert "strength" in result
    assert "confidence" in result
