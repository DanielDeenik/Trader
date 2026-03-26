"""Database adapter — PostgreSQL/SQLite abstraction.

Detects DATABASE_URL env var to select backend:
- DATABASE_URL="postgres://..." uses PostgreSQL via psycopg2
- Otherwise uses SQLite (default for local dev)

Provides:
  - get_connection(db_path=None): context manager yielding conn with .execute(), .cursor(), .commit(), .rollback()
  - placeholder: SQL parameter marker ('%s' for postgres, '?' for sqlite)
  - row_factory: automatic handling of row→dict conversion
"""

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Optional

DEFAULT_DB_PATH = str(Path(__file__).parent / "social_arb.db")


def get_db_backend() -> str:
    """Detect backend from DATABASE_URL env var.

    Returns:
        'postgres' if DATABASE_URL starts with 'postgres://'
        'sqlite' otherwise
    """
    db_url = os.getenv("DATABASE_URL", "")
    if db_url.startswith("postgres://") or db_url.startswith("postgresql://"):
        return "postgres"
    return "sqlite"


def get_placeholder() -> str:
    """Get SQL parameter placeholder for current backend.

    Returns:
        '%s' for PostgreSQL
        '?' for SQLite
    """
    return "%s" if get_db_backend() == "postgres" else "?"


class PostgreSQLCursor:
    """Wraps psycopg2 RealDictCursor to add sqlite3-compatible lastrowid."""

    def __init__(self, cursor):
        self._cursor = cursor

    @property
    def lastrowid(self):
        """Get last inserted row ID. Requires INSERT ... RETURNING id."""
        row = self._cursor.fetchone()
        if row:
            return row.get("id") or row.get(list(row.keys())[0])
        return None

    def execute(self, sql, params=None):
        if params is None:
            params = ()
        self._cursor.execute(sql, params)
        return self

    def fetchone(self):
        return self._cursor.fetchone()

    def fetchall(self):
        return self._cursor.fetchall()

    def close(self):
        self._cursor.close()

    @property
    def description(self):
        return self._cursor.description


class PostgreSQLConnection:
    """Wrapper around psycopg2 connection to match sqlite3.Connection interface."""

    def __init__(self, conn, cursor_factory):
        self._conn = conn
        self._cursor_factory = cursor_factory

    def cursor(self):
        """Return a RealDictCursor wrapped for compatibility."""
        return PostgreSQLCursor(self._conn.cursor(cursor_factory=self._cursor_factory))

    def execute(self, sql: str, params=None):
        """Execute SQL and return cursor (mimics sqlite3.Connection.execute)."""
        cur = self.cursor()
        cur.execute(sql, params)
        return cur

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._conn.close()


@contextmanager
def get_connection(db_path: Optional[str] = None):
    """Get database connection as context manager.

    For SQLite: uses db_path (default: DEFAULT_DB_PATH)
    For PostgreSQL: ignores db_path, uses DATABASE_URL env var

    Yields connection with .execute(), .cursor(), .commit(), .rollback() interface.
    All rows returned as dicts in both backends.
    """
    backend = get_db_backend()

    if backend == "postgres":
        try:
            import psycopg2
            from psycopg2.extras import RealDictCursor
        except ImportError:
            raise ImportError(
                "psycopg2 required for PostgreSQL backend. "
                "Install with: pip install 'social-arb[postgres]'"
            )

        db_url = os.getenv("DATABASE_URL")
        conn = psycopg2.connect(db_url)
        conn.autocommit = False
        conn_wrapper = PostgreSQLConnection(conn, RealDictCursor)

        try:
            yield conn_wrapper
            conn_wrapper.commit()
        except Exception:
            conn_wrapper.rollback()
            raise
        finally:
            conn_wrapper.close()
    else:
        # SQLite
        if db_path is None:
            db_path = DEFAULT_DB_PATH

        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")

        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
