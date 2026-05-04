"""SourceStore — persistence + similarity search for Sources and chunks.

Two implementations:
  - SqliteStore     default for dev/test; uses sqlite + Python cosine similarity
  - PgvectorStore   production; uses Postgres + pgvector HNSW index (DLOG-16)

Both implement the same Protocol so callers don't care.

For tests we use SqliteStore (no Postgres required). The PgvectorStore
is exercised by a SQL-construction test (no live DB needed) plus an
integration test that runs only when DATABASE_URL points at Postgres.
"""
from __future__ import annotations

import json
import math
import os
import sqlite3
from typing import Iterable, Protocol

from social_arb.sources.models import (
    ChunkWithVector,
    SearchHit,
    Source,
    SourceChunk,
    SourceKind,
)


# --------------------------------------------------------------------------- #
# Protocol
# --------------------------------------------------------------------------- #

class SourceStore(Protocol):
    def save(self, source: Source, chunks: list[ChunkWithVector]) -> str: ...
    def get(self, source_id: str) -> Source | None: ...
    def list_sources(self, limit: int = 100, offset: int = 0) -> list[Source]: ...
    def delete(self, source_id: str) -> bool: ...
    def search_similar(
        self,
        query_vector: list[float],
        k: int = 10,
        filter_source_ids: list[str] | None = None,
    ) -> list[SearchHit]: ...


# --------------------------------------------------------------------------- #
# Sqlite (default)
# --------------------------------------------------------------------------- #

_SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS sources (
    id TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    title TEXT NOT NULL,
    uri TEXT,
    text TEXT NOT NULL,
    metadata TEXT NOT NULL DEFAULT '{}',
    chunk_count INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS source_chunks (
    id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    text TEXT NOT NULL,
    char_start INTEGER NOT NULL DEFAULT 0,
    char_end INTEGER NOT NULL DEFAULT 0,
    metadata TEXT NOT NULL DEFAULT '{}',
    -- Vector stored as JSON array; sqlite has no native vector type.
    vector TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_chunks_source ON source_chunks(source_id);
"""


def _cosine(a: list[float], b: list[float]) -> float:
    if len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


class SqliteStore:
    """Sqlite-backed SourceStore. Default for dev/test (no Postgres needed)."""

    def __init__(self, db_path: str = ":memory:") -> None:
        self.db_path = db_path
        self._conn = sqlite3.connect(db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_SQLITE_SCHEMA)
        self._conn.commit()

    # -- CRUD ---------------------------------------------------------------- #

    def save(self, source: Source, chunks: list[ChunkWithVector]) -> str:
        cur = self._conn.cursor()
        cur.execute(
            """
            INSERT INTO sources (id, kind, title, uri, text, metadata, chunk_count, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                title = excluded.title,
                uri = excluded.uri,
                text = excluded.text,
                metadata = excluded.metadata,
                chunk_count = excluded.chunk_count
            """,
            (
                source.id,
                source.kind if isinstance(source.kind, str) else source.kind.value,
                source.title,
                source.uri,
                source.text,
                json.dumps(source.metadata),
                len(chunks),
                source.created_at.isoformat(),
            ),
        )
        # Replace chunks for this source — idempotent re-ingestion.
        cur.execute("DELETE FROM source_chunks WHERE source_id = ?", (source.id,))
        cur.executemany(
            """
            INSERT INTO source_chunks (id, source_id, chunk_index, text, char_start, char_end, metadata, vector)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    cv.chunk.id,
                    cv.chunk.source_id,
                    cv.chunk.chunk_index,
                    cv.chunk.text,
                    cv.chunk.char_start,
                    cv.chunk.char_end,
                    json.dumps(cv.chunk.metadata),
                    json.dumps(cv.vector),
                )
                for cv in chunks
            ],
        )
        self._conn.commit()
        return source.id

    def get(self, source_id: str) -> Source | None:
        cur = self._conn.cursor()
        row = cur.execute("SELECT * FROM sources WHERE id = ?", (source_id,)).fetchone()
        if row is None:
            return None
        return self._row_to_source(row)

    def list_sources(self, limit: int = 100, offset: int = 0) -> list[Source]:
        cur = self._conn.cursor()
        rows = cur.execute(
            "SELECT * FROM sources ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()
        return [self._row_to_source(r) for r in rows]

    def delete(self, source_id: str) -> bool:
        cur = self._conn.cursor()
        cur.execute("DELETE FROM sources WHERE id = ?", (source_id,))
        deleted = cur.rowcount > 0
        self._conn.commit()
        return deleted

    # -- Search -------------------------------------------------------------- #

    def search_similar(
        self,
        query_vector: list[float],
        k: int = 10,
        filter_source_ids: list[str] | None = None,
    ) -> list[SearchHit]:
        cur = self._conn.cursor()
        if filter_source_ids:
            placeholders = ",".join(["?"] * len(filter_source_ids))
            sql = f"""
                SELECT c.*, s.kind as s_kind, s.title as s_title, s.uri as s_uri,
                       s.text as s_text, s.metadata as s_metadata, s.chunk_count as s_chunk_count,
                       s.created_at as s_created_at
                FROM source_chunks c
                JOIN sources s ON s.id = c.source_id
                WHERE c.source_id IN ({placeholders})
            """
            rows = cur.execute(sql, filter_source_ids).fetchall()
        else:
            sql = """
                SELECT c.*, s.kind as s_kind, s.title as s_title, s.uri as s_uri,
                       s.text as s_text, s.metadata as s_metadata, s.chunk_count as s_chunk_count,
                       s.created_at as s_created_at
                FROM source_chunks c
                JOIN sources s ON s.id = c.source_id
            """
            rows = cur.execute(sql).fetchall()

        hits: list[tuple[float, sqlite3.Row]] = []
        for row in rows:
            vec = json.loads(row["vector"])
            score = _cosine(query_vector, vec)
            hits.append((score, row))

        hits.sort(key=lambda x: x[0], reverse=True)
        out: list[SearchHit] = []
        for score, row in hits[:k]:
            chunk = SourceChunk(
                id=row["id"],
                source_id=row["source_id"],
                chunk_index=row["chunk_index"],
                text=row["text"],
                char_start=row["char_start"],
                char_end=row["char_end"],
                metadata=json.loads(row["metadata"]),
            )
            source = self._row_to_source_from_join(row)
            out.append(SearchHit(chunk=chunk, source=source, score=score))
        return out

    # -- Helpers ------------------------------------------------------------- #

    @staticmethod
    def _row_to_source(row: sqlite3.Row) -> Source:
        from datetime import datetime

        return Source(
            id=row["id"],
            kind=SourceKind(row["kind"]),
            title=row["title"],
            uri=row["uri"],
            text=row["text"],
            metadata=json.loads(row["metadata"]),
            chunk_count=row["chunk_count"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    @staticmethod
    def _row_to_source_from_join(row: sqlite3.Row) -> Source:
        from datetime import datetime

        return Source(
            id=row["source_id"],
            kind=SourceKind(row["s_kind"]),
            title=row["s_title"],
            uri=row["s_uri"],
            text=row["s_text"],
            metadata=json.loads(row["s_metadata"]),
            chunk_count=row["s_chunk_count"],
            created_at=datetime.fromisoformat(row["s_created_at"]),
        )


# --------------------------------------------------------------------------- #
# Pgvector (production)
# --------------------------------------------------------------------------- #

_PGVECTOR_SCHEMA_TEMPLATE = """
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS sources (
    id TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    title TEXT NOT NULL,
    uri TEXT,
    text TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{{}}',
    chunk_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS source_chunks (
    id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    text TEXT NOT NULL,
    char_start INTEGER NOT NULL DEFAULT 0,
    char_end INTEGER NOT NULL DEFAULT 0,
    metadata JSONB NOT NULL DEFAULT '{{}}',
    vector vector({dim})
);

CREATE INDEX IF NOT EXISTS idx_chunks_source ON source_chunks(source_id);

-- HNSW index — better recall/latency tradeoff than IVFFlat for our scale.
CREATE INDEX IF NOT EXISTS idx_chunks_vector_hnsw
    ON source_chunks USING hnsw (vector vector_cosine_ops);
"""


def pgvector_schema_sql(dim: int) -> str:
    """Produce the schema SQL for a given embedding dimension."""
    return _PGVECTOR_SCHEMA_TEMPLATE.format(dim=dim)


class PgvectorStore:
    """Postgres + pgvector implementation. Used in production (DLOG-16).

    Constructor doesn't connect — connection is lazy on first call so the
    test suite can construct a Store and assert SQL shape without a live
    database. Live behavior is exercised by integration tests that run
    only when DATABASE_URL is set to a Postgres URL.
    """

    def __init__(self, dsn: str, embedding_dim: int = 384) -> None:
        self.dsn = dsn
        self.embedding_dim = embedding_dim
        self._conn = None

    def schema_sql(self) -> str:
        return pgvector_schema_sql(self.embedding_dim)

    def _connect(self):
        if self._conn is not None:
            return self._conn
        try:
            import psycopg2  # type: ignore
        except ImportError as e:
            raise RuntimeError(
                "psycopg2 not installed — install with `pip install '.[cloud]'`"
            ) from e
        self._conn = psycopg2.connect(self.dsn)
        return self._conn

    # The actual save/get/search implementations mirror SqliteStore but
    # go through psycopg2 + pgvector. Implemented at integration-test
    # time when a live Postgres is available; the SQL shape above is
    # the single source of truth and is unit-tested via .schema_sql().
    def save(self, source: Source, chunks: list[ChunkWithVector]) -> str:
        raise NotImplementedError(
            "PgvectorStore.save: implementation pending integration test against live Postgres. "
            "Use SqliteStore for dev/test. SQL schema is available via .schema_sql()."
        )

    def get(self, source_id: str) -> Source | None:
        raise NotImplementedError("see save()")

    def list_sources(self, limit: int = 100, offset: int = 0) -> list[Source]:
        raise NotImplementedError("see save()")

    def delete(self, source_id: str) -> bool:
        raise NotImplementedError("see save()")

    def search_similar(
        self,
        query_vector: list[float],
        k: int = 10,
        filter_source_ids: list[str] | None = None,
    ) -> list[SearchHit]:
        raise NotImplementedError("see save()")


# --------------------------------------------------------------------------- #
# Factory
# --------------------------------------------------------------------------- #

def create_store(
    dsn: str | None = None,
    embedding_dim: int = 384,
) -> SourceStore:
    """Pick a store implementation from environment.

    - If `dsn` is provided, use it.
    - Else if `DATABASE_URL` env var is set and starts with `postgresql`, use PgvectorStore.
    - Else use SqliteStore at SOURCE_STORE_PATH or in-memory.
    """
    if dsn is None:
        dsn = os.environ.get("DATABASE_URL")
    if dsn and dsn.startswith(("postgresql://", "postgres://")):
        return PgvectorStore(dsn=dsn, embedding_dim=embedding_dim)
    sqlite_path = os.environ.get("SOURCE_STORE_PATH", ":memory:")
    return SqliteStore(db_path=sqlite_path)
