"""Tests for sentiment enrichment in pipeline."""

import json
import pytest
from social_arb.nlp.sentiment_enricher import SentimentEnricher


def test_enricher_in_pipeline_context():
    """Simulate pipeline enrichment of collected signals."""
    enricher = SentimentEnricher(use_finbert=False)

    # Simulate signals as they come from collectors
    signals = [
        {
            "symbol": "DATABRICKS",
            "source": "news",
            "signal_type": "news_mention",
            "direction": "neutral",
            "strength": 0.6,
            "confidence": 0.7,
            "raw_json": json.dumps({
                "title": "Databricks raises $500M at $43B valuation, massive growth",
                "feed": "techcrunch",
            }),
        },
        {
            "symbol": "PLTR",
            "source": "reddit",
            "signal_type": "social_mention",
            "direction": "bullish",
            "strength": 0.3,
            "confidence": 0.4,
            "raw": {
                "title": "PLTR is going to crash hard, terrible earnings",
                "subreddit": "wallstreetbets",
            },
        },
        {
            "symbol": "NVDA",
            "source": "yfinance",
            "signal_type": "price",
            "direction": "bullish",
            "strength": 0.8,
            "confidence": 0.9,
            "raw_json": json.dumps({"price": 950.0}),
        },
    ]

    enriched = enricher.enrich_batch(signals)

    # News signal should have sentiment
    assert enriched[0]["direction"] in ("bullish", "neutral", "bearish")
    raw0 = json.loads(enriched[0]["raw_json"])
    assert "sentiment" in raw0

    # Reddit signal should have sentiment
    assert enriched[1]["direction"] in ("bullish", "neutral", "bearish")

    # yfinance signal should be unchanged (non-text source)
    assert enriched[2]["direction"] == "bullish"
    assert enriched[2]["strength"] == 0.8


def test_handle_enrich_sentiment():
    """Test the task handler function."""
    from social_arb.tasks.workers import HANDLER_MAP
    assert "enrich_sentiment" in HANDLER_MAP
