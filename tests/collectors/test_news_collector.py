"""Tests for news collector."""

import pytest
from social_arb.collectors.news_collector import NewsCollector


def test_news_collector_instantiate():
    collector = NewsCollector()
    assert collector.source_name == "news"


def test_news_collector_collect_databricks():
    collector = NewsCollector()
    result = collector.collect(symbols=["Databricks", "Stripe"], feeds=["techcrunch"])
    assert result.source == "news"
    assert isinstance(result.signals, list)
    assert isinstance(result.errors, list)
    if result.signals:
        sig = result.signals[0]
        assert "symbol" in sig
        assert "source" in sig
        assert sig["source"] == "news"


def test_news_collector_timeout_handling():
    collector = NewsCollector()
    result = collector.collect(symbols=["TestCorp"])
    assert isinstance(result.errors, list)
