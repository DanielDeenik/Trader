"""Sources — first-class user-curated and API-derived data items.

A `Source` is any thing-with-text that a Notebook (NB-002) can attach,
that a Mosaic / Thesis can cite, and that the cited-RAG generator
(NB-003) can retrieve from.

See docs/specs/NB-001.md and DLOG-14 (sources first-class).
"""
from social_arb.sources.models import (
    Source,
    SourceChunk,
    ChunkWithVector,
    SearchHit,
    SourceKind,
)
from social_arb.sources.store import (
    SourceStore,
    SqliteStore,
    PgvectorStore,
    create_store,
)

__all__ = [
    "Source",
    "SourceChunk",
    "ChunkWithVector",
    "SearchHit",
    "SourceKind",
    "SourceStore",
    "SqliteStore",
    "PgvectorStore",
    "create_store",
]
