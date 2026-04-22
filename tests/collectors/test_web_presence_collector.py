"""Tests for web presence collector."""

import pytest
from social_arb.collectors.web_presence_collector import WebPresenceCollector


def test_web_presence_collector_instantiate():
    collector = WebPresenceCollector()
    assert collector.source_name == "web_presence"


def test_web_presence_collector_collect():
    collector = WebPresenceCollector()
    result = collector.collect(symbols=["databricks"])
    assert result.source == "web_presence"
    assert isinstance(result.signals, list)
    assert isinstance(result.errors, list)


def test_web_presence_collector_custom_urls():
    custom_urls = {"testcorp": "https://www.example.com"}
    collector = WebPresenceCollector()
    result = collector.collect(symbols=["testcorp"], domain_urls=custom_urls)
    assert isinstance(result.signals, list)


def test_web_presence_collector_no_url_mapping():
    collector = WebPresenceCollector()
    result = collector.collect(symbols=["UnknownCorp"])
    assert isinstance(result.errors, list)
