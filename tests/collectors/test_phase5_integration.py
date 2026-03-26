"""Integration tests for Phase 5 private company collectors."""

import pytest
from social_arb.collectors.news_collector import NewsCollector
from social_arb.collectors.hiring_collector import HiringCollector
from social_arb.collectors.patent_collector import PatentCollector
from social_arb.collectors.appstore_collector import AppStoreCollector
from social_arb.collectors.web_presence_collector import WebPresenceCollector
from social_arb.collectors.base import CollectorResult


@pytest.fixture
def private_symbols():
    return ["Databricks", "Stripe", "Anduril"]


def test_all_collectors_exist(private_symbols):
    collectors = [
        NewsCollector(),
        HiringCollector(),
        PatentCollector(),
        AppStoreCollector(),
        WebPresenceCollector(),
    ]
    assert len(collectors) == 5
    assert all(c is not None for c in collectors)


def test_collector_result_structure():
    collector = NewsCollector()
    result = collector.collect(symbols=["Databricks"])
    assert isinstance(result, CollectorResult)
    assert hasattr(result, "source")
    assert hasattr(result, "signals")
    assert hasattr(result, "errors")
    assert hasattr(result, "symbols_scanned")
    assert isinstance(result.signals, list)
    assert isinstance(result.errors, list)
    assert isinstance(result.symbols_scanned, list)


def test_signal_schema(private_symbols):
    collector = NewsCollector()
    result = collector.collect(symbols=private_symbols)
    for signal in result.signals:
        assert "symbol" in signal
        assert "source" in signal
        assert "signal_type" in signal
        assert "direction" in signal
        assert "strength" in signal
        assert "confidence" in signal
        assert "raw_json" in signal
        assert 0 <= signal["strength"] <= 1.0
        assert 0 <= signal["confidence"] <= 1.0
        assert signal["direction"] in ["bullish", "neutral", "bearish"]


def test_error_handling():
    collectors = [
        NewsCollector(),
        HiringCollector(),
        PatentCollector(),
        AppStoreCollector(),
        WebPresenceCollector(),
    ]
    for collector in collectors:
        result = collector.collect(symbols=["NonExistentCompanyXYZ"])
        assert isinstance(result, CollectorResult)
        assert isinstance(result.errors, list)


def test_source_names():
    mappings = {
        NewsCollector(): "news",
        HiringCollector(): "hiring",
        PatentCollector(): "patents",
        AppStoreCollector(): "appstore",
        WebPresenceCollector(): "web_presence",
    }
    for collector, expected_name in mappings.items():
        assert collector.source_name == expected_name


def test_no_api_keys_required():
    import os
    saved_env = {}
    api_keys = ["API_KEY", "REDIS_URL", "DATABASE_URL"]
    for key in api_keys:
        if key in os.environ:
            saved_env[key] = os.environ.pop(key)
    try:
        collectors = [
            NewsCollector(),
            HiringCollector(),
            PatentCollector(),
            AppStoreCollector(),
            WebPresenceCollector(),
        ]
        assert len(collectors) == 5
    finally:
        for key, val in saved_env.items():
            os.environ[key] = val
