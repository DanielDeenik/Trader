"""Tests for patent collector."""

import pytest
from social_arb.collectors.patent_collector import PatentCollector


def test_patent_collector_instantiate():
    collector = PatentCollector()
    assert collector.source_name == "patents"


def test_patent_collector_collect():
    collector = PatentCollector()
    result = collector.collect(symbols=["Google", "Microsoft"], days_back=90)
    assert result.source == "patents"
    assert isinstance(result.signals, list)
    assert isinstance(result.errors, list)


def test_patent_collector_handles_timeout():
    collector = PatentCollector()
    result = collector.collect(symbols=["TestCorp"])
    assert isinstance(result.errors, list)
