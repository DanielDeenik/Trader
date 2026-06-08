"""
Sync tier — snapshot the operational store into the Parquet lake.

DuckDB attaches the operational database directly (SQLite via the sqlite
extension, PostgreSQL via the postgres extension) and COPYs each table to a
Parquet file in ``lake_dir`` (local path or gs:// bucket). No pandas / row
marshalling — the columnar export is done entirely inside DuckDB.

Run periodically (CLI: ``social-arb lake-sync`` / a scheduled job). The
analytical tier (query.py) then reads the resulting Parquet.
"""

import os
import logging
from pathlib import Path
from typing import List, Optional

import duckdb

from social_arb.db.adapter import get_db_backend, DEFAULT_DB_PATH

logger = logging.getLogger(__name__)


def _lit(s: str) -> str:
    """Single-quote a string as a DuckDB SQL literal (DDL can't bind params)."""
    return "'" + str(s).replace("'", "''") + "'"


# Operational tables snapshotted to the lake. Tables absent in the source are
# skipped (logged), so this list can stay ahead of any given DB instance.
LAKE_TABLES: List[str] = [
    "signals",
    "mosaics",
    "theses",
    "decisions",
    "reviews",
    "positions",
    "ohlcv",
    "scans",
    "instruments",
    "stepps_scores",
    "audit_trail",
]


def _configure_remote(con: duckdb.DuckDBPyConnection, lake_dir: str) -> None:
    """Set up httpfs + GCS credentials when writing to gs://."""
    if not lake_dir.startswith(("gs://", "s3://")):
        # Local target: make sure the directory exists.
        Path(lake_dir).mkdir(parents=True, exist_ok=True)
        return
    con.execute("INSTALL httpfs; LOAD httpfs;")
    if lake_dir.startswith("gs://"):
        key_id = os.getenv("GCS_HMAC_KEY_ID")
        secret = os.getenv("GCS_HMAC_SECRET")
        if key_id and secret:
            con.execute(
                f"CREATE OR REPLACE SECRET gcs_secret "
                f"(TYPE gcs, KEY_ID {_lit(key_id)}, SECRET {_lit(secret)});"
            )
        else:
            con.execute(
                "CREATE OR REPLACE SECRET gcs_secret "
                "(TYPE gcs, PROVIDER credential_chain);"
            )


def _attach_operational(con: duckdb.DuckDBPyConnection, db_path: str) -> None:
    """Attach the operational store as schema ``op`` (read-only)."""
    backend = get_db_backend()
    if backend == "postgres":
        db_url = os.getenv("DATABASE_URL")
        con.execute("INSTALL postgres; LOAD postgres;")
        con.execute(f"ATTACH {_lit(db_url)} AS op (TYPE postgres, READ_ONLY);")
    else:
        con.execute("INSTALL sqlite; LOAD sqlite;")
        con.execute(f"ATTACH {_lit(db_path)} AS op (TYPE sqlite, READ_ONLY);")


def sync_to_parquet(
    db_path: str = DEFAULT_DB_PATH,
    lake_dir: Optional[str] = None,
    tables: Optional[List[str]] = None,
) -> dict:
    """Snapshot operational tables to Parquet in the lake.

    Args:
        db_path: SQLite path (ignored for the postgres backend).
        lake_dir: lake root (local path or gs://). Defaults to LAKE_DIR env.
        tables: subset to sync; defaults to LAKE_TABLES.

    Returns:
        {table: row_count} for tables successfully written.
    """
    lake_dir = (lake_dir or os.getenv("LAKE_DIR") or "").strip().rstrip("/")
    if not lake_dir:
        raise ValueError("lake_dir not provided and LAKE_DIR env is unset")

    tables = tables or LAKE_TABLES
    written: dict = {}

    con = duckdb.connect(database=":memory:")
    try:
        _configure_remote(con, lake_dir)
        _attach_operational(con, db_path)

        for table in tables:
            target = f"{lake_dir}/{table}.parquet"
            try:
                con.execute(
                    f"COPY (SELECT * FROM op.{table}) "
                    f"TO {_lit(target)} (FORMAT PARQUET);"
                )
                count = con.execute(
                    f"SELECT COUNT(*) FROM op.{table}"
                ).fetchone()[0]
                written[table] = count
                logger.info("lake-sync %s -> %s (%d rows)", table, target, count)
            except duckdb.Error as e:
                # Missing table in this DB instance — skip, don't fail the run.
                logger.debug("lake-sync skipped %s: %s", table, e)
    finally:
        con.close()

    logger.info("lake-sync complete: %d tables, %d total rows",
                len(written), sum(written.values()))
    return written
