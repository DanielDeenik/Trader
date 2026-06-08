"""
Lakehouse layer (Option B architecture).

Two-tier design:
  - Operational tier (OLTP): the live store written by agents/API
    (SQLite locally, PostgreSQL in cloud) — owned by db/adapter.py.
  - Analytical tier (OLAP): operational tables are snapshotted to columnar
    Parquet (local dir or gs:// bucket); DuckDB queries that Parquet for all
    heavy analytics (trend scoring, divergence, dashboards).

DuckDB is the single engine for both sync (it attaches the operational store
and COPYs to Parquet) and analytics (it reads Parquet back as views). Nothing
in this package writes to the operational store.

Entry points:
  - sync.sync_to_parquet(db_path, lake_dir) — snapshot operational -> Parquet
  - query.lake_connection(lake_dir)         — DuckDB conn with views over Parquet
"""

from .sync import sync_to_parquet, LAKE_TABLES
from .query import lake_connection, lake_dir_from_env, is_lake_enabled

__all__ = [
    "sync_to_parquet",
    "LAKE_TABLES",
    "lake_connection",
    "lake_dir_from_env",
    "is_lake_enabled",
]
