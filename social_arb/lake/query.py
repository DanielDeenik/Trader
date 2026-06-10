"""
Analytical tier — DuckDB query engine over the Parquet lake.

A lake_connection() yields an in-memory DuckDB connection with one VIEW per
operational table, each backed by a Parquet file in ``lake_dir``. Analytical
SQL then references the tables by name (``signals``, ``mosaics``, ...) exactly
as if they were local tables — but reads run against columnar Parquet, on
local disk or in a GCS bucket (gs://).

lake_dir resolution: the LAKE_DIR env var. When unset, the lakehouse path is
disabled and callers fall back to the operational store.
"""

import os
import logging
import threading
from contextlib import contextmanager
from typing import Optional

import duckdb

# Tables exposed as DuckDB views (must match what sync writes).
from .sync import LAKE_TABLES, _lit

logger = logging.getLogger(__name__)

# A single DuckDB connection is created per lake_dir and reused across requests:
# building the engine + views is the expensive part (~1.5s cold), while
# read_parquet is lazy so the cached views always see freshly-synced files.
# A lock serializes access (DuckDB connections are not concurrency-safe).
_cache_lock = threading.Lock()
_cached_dir: Optional[str] = None
_cached_con: Optional[duckdb.DuckDBPyConnection] = None


def refresh_lake() -> None:
    """Drop the cached connection (call after a re-sync that adds tables)."""
    global _cached_dir, _cached_con
    with _cache_lock:
        if _cached_con is not None:
            _cached_con.close()
        _cached_dir, _cached_con = None, None


def lake_dir_from_env() -> Optional[str]:
    """Lake directory/bucket from LAKE_DIR env, or None if unset/blank."""
    val = (os.getenv("LAKE_DIR") or "").strip().rstrip("/")
    return val or None


def is_lake_enabled() -> bool:
    """True when LAKE_DIR is configured (analytical tier active)."""
    return lake_dir_from_env() is not None


def _configure_remote(con: duckdb.DuckDBPyConnection, lake_dir: str) -> None:
    """Set up httpfs + GCS credentials when the lake lives in gs://."""
    if not lake_dir.startswith(("gs://", "s3://")):
        return
    con.execute("INSTALL httpfs; LOAD httpfs;")
    # Fail fast on missing/unauthorized objects instead of retrying for ~30s.
    try:
        con.execute("SET http_retries=1; SET http_timeout=5000;")
    except duckdb.Error:
        pass
    if lake_dir.startswith("gs://"):
        key_id = os.getenv("GCS_HMAC_KEY_ID")
        secret = os.getenv("GCS_HMAC_SECRET")
        if key_id and secret:
            # Explicit HMAC keys (portable, works off-GCP too).
            con.execute(
                f"CREATE OR REPLACE SECRET gcs_secret "
                f"(TYPE gcs, KEY_ID {_lit(key_id)}, SECRET {_lit(secret)});"
            )
        else:
            # On GCP (Cloud Run) fall back to the attached service account.
            try:
                con.execute(
                    "CREATE OR REPLACE SECRET gcs_secret "
                    "(TYPE gcs, PROVIDER credential_chain);"
                )
            except duckdb.Error:
                logger.warning(
                    "No GCS_HMAC_KEY_ID/SECRET and credential_chain unavailable; "
                    "gs:// reads may fail."
                )


def _build_connection(lake_dir: str) -> duckdb.DuckDBPyConnection:
    """Create a DuckDB connection with one VIEW per operational table."""
    con = duckdb.connect(database=":memory:")
    _configure_remote(con, lake_dir)
    for table in LAKE_TABLES:
        path = f"{lake_dir}/{table}.parquet"
        try:
            con.execute(
                f"CREATE VIEW {table} AS "
                f"SELECT * FROM read_parquet({_lit(path)})"
            )
        except duckdb.Error:
            # Table not yet synced — leave the view absent.
            logger.debug("lake view skipped (no parquet): %s", table)
    return con


@contextmanager
def lake_connection(lake_dir: Optional[str] = None):
    """Cached DuckDB connection with a VIEW per operational table over Parquet.

    The connection is built once per lake_dir and reused (views read Parquet
    lazily, so they always reflect the latest sync). Access is serialized by a
    lock — yield the connection only for the duration of a query.

    Args:
        lake_dir: lake root (local path or gs://). Defaults to LAKE_DIR env.

    Yields:
        duckdb connection. Missing Parquet files are skipped (view not created),
        so analytical queries must tolerate absent tables.
    """
    global _cached_dir, _cached_con
    lake_dir = (lake_dir or lake_dir_from_env() or "").rstrip("/")
    if not lake_dir:
        raise ValueError("lake_dir not provided and LAKE_DIR env is unset")

    with _cache_lock:
        if _cached_con is None or _cached_dir != lake_dir:
            if _cached_con is not None:
                _cached_con.close()
            _cached_con = _build_connection(lake_dir)
            _cached_dir = lake_dir
        yield _cached_con
