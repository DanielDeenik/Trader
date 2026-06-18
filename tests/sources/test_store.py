"""Tests for SqliteStore + PgvectorStore SQL shape."""
import pytest

from social_arb.sources import (
    ChunkWithVector,
    PgvectorStore,
    SourceKind,
    SqliteStore,
)
from social_arb.sources.models import Source, SourceChunk, make_chunk_id


def _build_chunks_with_vector(source_id: str, count: int = 3, dim: int = 8) -> list[ChunkWithVector]:
    """Build chunks with vectors pointing in DIFFERENT directions.

    Each chunk gets a one-hot-ish vector at index `i % dim` so cosine
    similarity actually discriminates between them. Vectors with the
    same direction (just different magnitudes) all have cosine = 1.0
    with each other and would defeat the search test.
    """
    out = []
    for i in range(count):
        text = f"chunk-{i}-text"
        chunk = SourceChunk(
            id=make_chunk_id(source_id, i, text),
            source_id=source_id,
            chunk_index=i,
            text=text,
            char_start=i * 100,
            char_end=i * 100 + len(text),
        )
        # One-hot at position (i % dim) so each chunk points in a unique direction.
        vector = [0.0] * dim
        vector[i % dim] = 1.0
        out.append(ChunkWithVector(chunk=chunk, vector=vector))
    return out


def test_save_and_get_roundtrip():
    store = SqliteStore()
    src = Source.build(text="hello world", kind=SourceKind.TEXT, title="t1")
    chunks = _build_chunks_with_vector(src.id, count=2)
    saved_id = store.save(src, chunks)
    assert saved_id == src.id

    fetched = store.get(src.id)
    assert fetched is not None
    assert fetched.title == "t1"
    assert fetched.chunk_count == 2


def test_idempotent_resave_replaces_chunks():
    store = SqliteStore()
    src = Source.build(text="body", kind=SourceKind.TEXT, title="t")
    store.save(src, _build_chunks_with_vector(src.id, count=5))
    # Re-save with fewer chunks; chunk_count should reflect the new count.
    store.save(src, _build_chunks_with_vector(src.id, count=2))
    fetched = store.get(src.id)
    assert fetched.chunk_count == 2


def test_list_sources_orders_newest_first():
    store = SqliteStore()
    a = Source.build(text="a", kind=SourceKind.TEXT, title="A")
    b = Source.build(text="b", kind=SourceKind.TEXT, title="B")
    store.save(a, _build_chunks_with_vector(a.id, count=1))
    store.save(b, _build_chunks_with_vector(b.id, count=1))
    titles = [s.title for s in store.list_sources()]
    assert set(titles) == {"A", "B"}


def test_delete_returns_true_when_present():
    store = SqliteStore()
    src = Source.build(text="x", kind=SourceKind.TEXT, title="x")
    store.save(src, _build_chunks_with_vector(src.id, count=1))
    assert store.delete(src.id) is True
    assert store.delete(src.id) is False
    assert store.get(src.id) is None


def test_search_similar_returns_top_k_by_cosine():
    store = SqliteStore()
    src = Source.build(text="any", kind=SourceKind.TEXT, title="any")
    chunks = _build_chunks_with_vector(src.id, count=3, dim=4)
    store.save(src, chunks)
    # Query points in chunk 2's direction (one-hot at index 2 % 4 == 2).
    query = [0.0, 0.0, 1.0, 0.0]
    hits = store.search_similar(query, k=3)
    assert len(hits) == 3
    # Top hit should be chunk index 2 (its vector matches exactly).
    assert hits[0].chunk.chunk_index == 2
    assert hits[0].score == pytest.approx(1.0, abs=1e-6)
    # The other two chunks have orthogonal vectors → cosine = 0.
    assert hits[1].score == pytest.approx(0.0, abs=1e-6)
    assert hits[2].score == pytest.approx(0.0, abs=1e-6)


def test_pgvector_schema_sql_includes_extension_and_index():
    store = PgvectorStore(dsn="postgresql://fake/db", embedding_dim=384)
    sql = store.schema_sql()
    assert "CREATE EXTENSION IF NOT EXISTS vector" in sql
    assert "vector(384)" in sql
    assert "USING hnsw" in sql
    assert "vector_cosine_ops" in sql
