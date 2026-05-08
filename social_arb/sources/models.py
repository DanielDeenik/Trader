"""Pydantic models for the Source layer (NB-001).

`Source` is the entity. `SourceChunk` is a sub-unit produced by the
chunker. `ChunkWithVector` is a chunk that has been embedded.
`SearchHit` is what `SourceStore.search_similar` returns.

Stable IDs:
    source_id   sha256(content || kind || canonical_uri)[:24] hex
    chunk_id    sha256(source_id || chunk_index || chunk_text)[:24] hex

Stable IDs make ingestion idempotent: re-ingesting the same content
produces the same IDs, so re-runs are cheap and provenance survives.

DLOG-14: Sources are first-class (separate table, FK references).
DLOG-15: Citation tokens reference (source_id, chunk_id).
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SourceKind(str, Enum):
    """The kind of source this came from. Extend as parsers/collectors are added."""

    # Manual / user-curated (NB-001 scope)
    PDF = "pdf"
    DOCX = "docx"
    URL = "url"
    TEXT = "text"          # uploaded text file
    PASTED = "pasted"      # pasted-into-textarea text

    # Deferred to NB-007
    AUDIO = "audio"
    YOUTUBE = "youtube"

    # Auto-collected (existing 12 collectors map to these via NB-006)
    YFINANCE = "yfinance"
    REDDIT = "reddit"
    SEC_FILING = "sec_filing"
    COINGECKO = "coingecko"
    DEFILLAMA = "defillama"
    GITHUB = "github"
    HIRING = "hiring"
    NEWS = "news"
    PATENT = "patent"
    TRENDS = "trends"
    WEB_PRESENCE = "web_presence"
    APPSTORE = "appstore"
    CRYPTO_SENTIMENT = "crypto_sentiment"


def _stable_id(*parts: str, length: int = 24) -> str:
    """Produce a stable hex ID from parts. Used for source_id and chunk_id."""
    h = hashlib.sha256()
    for p in parts:
        h.update(p.encode("utf-8"))
        h.update(b"\x00")  # separator so ('a','bc') != ('ab','c')
    return h.hexdigest()[:length]


def make_source_id(content: str, kind: SourceKind | str, uri: str | None) -> str:
    """Deterministic source_id given canonical content + kind + URI."""
    return _stable_id(content, str(kind), uri or "")


def make_chunk_id(source_id: str, chunk_index: int, text: str) -> str:
    """Deterministic chunk_id within a source."""
    return _stable_id(source_id, str(chunk_index), text)


class Source(BaseModel):
    """A canonical source — once stored, identified by a stable `id`.

    `text` is the parsed full text. `metadata` is parser-specific (e.g.
    page count for PDFs, author for DOCX, status code for URL fetches).
    `chunk_count` is denormalized for fast UI listing without joins.
    """

    model_config = ConfigDict(use_enum_values=True)

    id: str = Field(..., description="sha256 of (content||kind||uri), 24 hex chars")
    kind: SourceKind
    title: str
    uri: str | None = None              # original URL or filename
    text: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    chunk_count: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @classmethod
    def build(
        cls,
        *,
        text: str,
        kind: SourceKind | str,
        title: str,
        uri: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Source:
        """Construct a Source with the deterministic ID computed for you."""
        return cls(
            id=make_source_id(text, kind, uri),
            kind=kind,
            title=title,
            uri=uri,
            text=text,
            metadata=metadata or {},
        )


class SourceChunk(BaseModel):
    """A chunk of a Source, produced by the chunker.

    `chunk_index` is 0-based ordering within the parent Source. Embedding
    is stored separately on `ChunkWithVector` so the chunk model itself
    is dimension-agnostic.
    """

    id: str = Field(..., description="sha256 of (source_id||index||text), 24 hex chars")
    source_id: str
    chunk_index: int
    text: str
    char_start: int = 0
    char_end: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)


class ChunkWithVector(BaseModel):
    """A SourceChunk + its embedding vector. Persisted by the SourceStore."""

    chunk: SourceChunk
    vector: list[float]


class SearchHit(BaseModel):
    """One result from SourceStore.search_similar."""

    chunk: SourceChunk
    source: Source
    score: float = Field(..., description="cosine similarity in [-1, 1]")
