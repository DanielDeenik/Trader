"""Tests for social_arb.sources.models — stable IDs + Pydantic models."""
from social_arb.sources.models import (
    Source,
    SourceKind,
    make_chunk_id,
    make_source_id,
)


def test_source_id_is_deterministic():
    sid_a = make_source_id("hello", SourceKind.TEXT, "memo://1")
    sid_b = make_source_id("hello", SourceKind.TEXT, "memo://1")
    assert sid_a == sid_b
    assert len(sid_a) == 24
    assert all(c in "0123456789abcdef" for c in sid_a)


def test_source_id_changes_with_content():
    a = make_source_id("hello", SourceKind.TEXT, "memo://1")
    b = make_source_id("hella", SourceKind.TEXT, "memo://1")
    assert a != b


def test_source_id_changes_with_kind():
    a = make_source_id("hello", SourceKind.TEXT, "memo://1")
    b = make_source_id("hello", SourceKind.PDF, "memo://1")
    assert a != b


def test_chunk_id_is_deterministic():
    sid = make_source_id("body", SourceKind.TEXT, None)
    a = make_chunk_id(sid, 0, "first chunk text")
    b = make_chunk_id(sid, 0, "first chunk text")
    assert a == b
    assert len(a) == 24


def test_source_build_round_trip():
    s = Source.build(text="abc", kind=SourceKind.TEXT, title="t", uri=None)
    assert s.id == make_source_id("abc", SourceKind.TEXT, None)
    assert s.title == "t"
    assert s.kind == "text" or s.kind == SourceKind.TEXT
