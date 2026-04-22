"""Structured logging setup for Social Arb."""

import logging
import os
import sys


def setup_logging(
    level: str = None,
    json_format: bool = None,
) -> None:
    if level is None:
        level = os.getenv("LOG_LEVEL", "INFO")
    if json_format is None:
        json_format = os.getenv("LOG_FORMAT", "plain").lower() == "json"

    numeric_level = getattr(logging, level.upper(), logging.INFO)

    root = logging.getLogger()
    root.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(numeric_level)

    if json_format:
        try:
            from pythonjsonlogger import jsonlogger
            formatter = jsonlogger.JsonFormatter(
                fmt="%(asctime)s %(name)s %(levelname)s %(message)s",
                datefmt="%Y-%m-%dT%H:%M:%S",
            )
        except ImportError:
            formatter = logging.Formatter(
                fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                datefmt="%Y-%m-%dT%H:%M:%S",
            )
    else:
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )

    handler.setFormatter(formatter)
    root.addHandler(handler)
    root.setLevel(numeric_level)

    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
