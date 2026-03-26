"""Tests for logging configuration."""

import logging
import pytest
from social_arb.logging_config import setup_logging


def test_setup_logging_returns_logger():
    setup_logging(level="DEBUG", json_format=False)
    logger = logging.getLogger("social_arb")
    assert logger.level == logging.DEBUG or logging.getLogger().level == logging.DEBUG


def test_setup_logging_json_format():
    setup_logging(level="INFO", json_format=True)
    root = logging.getLogger()
    assert len(root.handlers) > 0


def test_setup_logging_plain_format():
    setup_logging(level="WARNING", json_format=False)
    root = logging.getLogger()
    assert len(root.handlers) > 0
