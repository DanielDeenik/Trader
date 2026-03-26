"""Tests for hiring collector."""

import pytest
from social_arb.collectors.hiring_collector import HiringCollector


def test_hiring_collector_instantiate():
    collector = HiringCollector()
    assert collector.source_name == "hiring"


def test_hiring_collector_collect_databricks():
    collector = HiringCollector()
    result = collector.collect(symbols=["databricks"])
    assert result.source == "hiring"
    assert isinstance(result.signals, list)
    assert isinstance(result.errors, list)
    assert "databricks" in [s["symbol"].lower() for s in result.signals] or len(result.errors) > 0


def test_hiring_collector_custom_urls():
    custom_urls = {"testcorp": "https://example.com/jobs/"}
    collector = HiringCollector()
    result = collector.collect(symbols=["testcorp"], company_urls=custom_urls)
    assert isinstance(result.signals, list)
    assert isinstance(result.errors, list)


def test_hiring_collector_no_url_mapping():
    collector = HiringCollector()
    result = collector.collect(symbols=["UnknownCorp"])
    assert isinstance(result.errors, list)
