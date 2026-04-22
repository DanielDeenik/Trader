"""Tests for app store collector."""

import pytest
from social_arb.collectors.appstore_collector import AppStoreCollector


def test_appstore_collector_instantiate():
    collector = AppStoreCollector()
    assert collector.source_name == "appstore"


def test_appstore_collector_with_apps():
    custom_apps = {"anthropic": ["Claude"]}
    collector = AppStoreCollector()
    result = collector.collect(symbols=["anthropic"], app_mapping=custom_apps)
    assert result.source == "appstore"
    assert isinstance(result.signals, list)


def test_appstore_collector_no_apps():
    collector = AppStoreCollector()
    result = collector.collect(symbols=["Databricks"])
    assert isinstance(result.signals, list)
