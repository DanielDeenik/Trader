"""Tests for sentiment enricher orchestrator."""

import json
import pytest
from unittest.mock import patch, MagicMock
from social_arb.nlp.sentiment_enricher import SentimentEnricher


@pytest.fixture
def enricher():
    return SentimentEnricher(use_finbert=False)  # VADER-only for fast tests


def test_enricher_instantiate(enricher):
    assert enricher is not None


def test_extract_text_from_signal_news(enricher):
    signal = {
        "source": "news",
        "raw_json": json.dumps({"title": "BREAKING: Tech company reports record earnings"}),
    }
    text = enricher.extract_text(signal)
    assert "record earnings" in text.lower()


def test_extract_text_from_signal_reddit(enricher):
    signal = {
        "source": "reddit",
        "raw": {"title": "PLTR to the moon!", "subreddit": "wallstreetbets"},
    }
    text = enricher.extract_text(signal)
    assert "pltr" in text.lower() or "moon" in text.lower()


def test_extract_text_from_signal_sec(enricher):
    signal = {
        "source": "sec_edgar",
        "raw": {"description": "Annual report filed", "form_type": "10-K"},
    }
    text = enricher.extract_text(signal)
    assert "annual report" in text.lower()


def test_enrich_single_signal(enricher):
    signal = {
        "source": "news",
        "direction": "neutral",
        "strength": 0.5,
        "confidence": 0.5,
        "raw_json": json.dumps({"title": "Amazing growth, revenue soaring to new heights"}),
    }
    enriched = enricher.enrich_signal(signal)
    assert enriched["direction"] in ("bullish", "bearish", "neutral")
    assert "sentiment" in json.loads(enriched["raw_json"]) if isinstance(enriched["raw_json"], str) else "sentiment" in enriched["raw_json"]


def test_enrich_batch(enricher):
    signals = [
        {
            "source": "news",
            "direction": "neutral",
            "strength": 0.5,
            "confidence": 0.5,
            "raw_json": json.dumps({"title": "Great earnings beat"}),
        },
        {
            "source": "reddit",
            "direction": "bullish",
            "strength": 0.3,
            "confidence": 0.4,
            "raw": {"title": "Terrible losses reported"},
        },
    ]
    enriched = enricher.enrich_batch(signals)
    assert len(enriched) == 2


def test_enricher_preserves_non_text_signals(enricher):
    signal = {
        "source": "yfinance",
        "direction": "bullish",
        "strength": 0.8,
        "confidence": 0.9,
        "raw_json": json.dumps({"price": 150.0, "volume": 1000000}),
    }
    enriched = enricher.enrich_signal(signal)
    # Non-text source: should be returned unchanged
    assert enriched["direction"] == "bullish"
    assert enriched["strength"] == 0.8


def test_should_use_finbert(enricher):
    # enricher has use_finbert=False, so always returns False
    assert enricher.should_deep_score({"strength": 0.9}) is False

    # Mock FinBERT as available and create enricher with it enabled
    with patch("social_arb.nlp.finbert_scorer.FINBERT_AVAILABLE", True):
        with patch("social_arb.nlp.finbert_scorer.FinBertScorer") as mock_finbert_class:
            mock_finbert_instance = MagicMock()
            mock_finbert_class.return_value = mock_finbert_instance

            enricher_fb = SentimentEnricher(use_finbert=True, finbert_threshold=0.7)
            # High VADER strength should trigger finbert
            assert enricher_fb.should_deep_score({"strength": 0.8}) is True
            assert enricher_fb.should_deep_score({"strength": 0.3}) is False
