"""Tests for the token-aware chunker."""
from social_arb.notebooks.chunker import Chunker, ChunkerConfig
from social_arb.notebooks.parsers.base import ParsedSource
from social_arb.sources.models import SourceKind


def _parsed(text: str) -> ParsedSource:
    return ParsedSource(text=text, title="t", kind=SourceKind.TEXT, uri=None)


def test_short_text_yields_one_chunk():
    chunker = Chunker(ChunkerConfig(chunk_size_tokens=400, chunk_overlap_tokens=60, min_chunk_tokens=1))
    source, chunks = chunker.chunk(_parsed("hello world"))
    assert len(chunks) == 1
    assert source.chunk_count == 1
    assert chunks[0].chunk_index == 0


def test_long_text_yields_multiple_chunks_with_overlap():
    text = " ".join(f"word{i}" for i in range(1000))
    chunker = Chunker(ChunkerConfig(chunk_size_tokens=200, chunk_overlap_tokens=40, min_chunk_tokens=1))
    source, chunks = chunker.chunk(_parsed(text))
    assert len(chunks) > 1
    assert source.chunk_count == len(chunks)
    # Indices are 0..N-1 sequentially.
    assert [c.chunk_index for c in chunks] == list(range(len(chunks)))


def test_chunk_ids_are_deterministic():
    text = " ".join(f"word{i}" for i in range(500))
    chunker = Chunker(ChunkerConfig(chunk_size_tokens=200, chunk_overlap_tokens=40, min_chunk_tokens=1))
    _, a_chunks = chunker.chunk(_parsed(text))
    _, b_chunks = chunker.chunk(_parsed(text))
    assert [c.id for c in a_chunks] == [c.id for c in b_chunks]


def test_min_chunk_tokens_drops_tiny_tail():
    # 250 tokens, chunk_size=200, overlap=0 → step=200 → chunks at [0..200), [200..250)
    # Tail chunk has 50 tokens; if min=80, tail dropped (only the first chunk remains).
    text = " ".join(f"w{i}" for i in range(250))
    chunker = Chunker(ChunkerConfig(chunk_size_tokens=200, chunk_overlap_tokens=0, min_chunk_tokens=80))
    _, chunks = chunker.chunk(_parsed(text))
    assert len(chunks) == 1
