"""Tests for NotebookStore — CRUD, scope filters, attach/detach, artifact cache."""
from datetime import datetime

import pytest

from social_arb.notebooks.notebook_models import (
    Artifact,
    ArtifactKind,
    Notebook,
    NotebookScope,
    make_artifact_hash,
)
from social_arb.notebooks.notebook_store import NotebookStore


def _nb(title: str = "T", **scope_kwargs) -> Notebook:
    return Notebook(title=title, scope=NotebookScope(**scope_kwargs))


def test_create_and_get_roundtrip():
    store = NotebookStore()
    nb = store.create(_nb(title="AMD Q1"))
    fetched = store.get(nb.id)
    assert fetched is not None
    assert fetched.title == "AMD Q1"
    assert fetched.scope.is_empty


def test_get_unknown_returns_none():
    store = NotebookStore()
    assert store.get("nope") is None


def test_list_filters_by_ticker():
    store = NotebookStore()
    store.create(_nb(title="standalone"))
    store.create(_nb(title="amd-thesis", ticker="AMD"))
    store.create(_nb(title="sq-thesis", ticker="SQ"))
    amd = store.list(ticker="AMD")
    assert len(amd) == 1
    assert amd[0].title == "amd-thesis"


def test_list_returns_zero_for_unknown_ticker():
    store = NotebookStore()
    store.create(_nb(title="x", ticker="AMD"))
    assert store.list(ticker="NVDA") == []


def test_update_changes_title_and_touches_updated_at():
    store = NotebookStore()
    nb = store.create(_nb(title="old"))
    original_updated = nb.updated_at
    updated = store.update(nb.id, title="new")
    assert updated is not None
    assert updated.title == "new"
    assert updated.updated_at >= original_updated


def test_update_unknown_returns_none():
    store = NotebookStore()
    assert store.update("nope", title="x") is None


def test_delete_returns_true_then_false():
    store = NotebookStore()
    nb = store.create(_nb())
    assert store.delete(nb.id) is True
    assert store.delete(nb.id) is False
    assert store.get(nb.id) is None


def test_attach_source_idempotent():
    store = NotebookStore()
    nb = store.create(_nb())
    assert store.attach_source(nb.id, "src-001") is True
    # Second attach is a no-op (returns False because already linked).
    assert store.attach_source(nb.id, "src-001") is False
    fetched = store.get(nb.id)
    assert fetched.source_ids == ["src-001"]


def test_detach_source_returns_true_only_when_present():
    store = NotebookStore()
    nb = store.create(_nb())
    store.attach_source(nb.id, "src-001")
    assert store.detach_source(nb.id, "src-001") is True
    assert store.detach_source(nb.id, "src-001") is False
    assert store.get(nb.id).source_ids == []


def test_delete_notebook_cascades_attachments_and_artifacts():
    store = NotebookStore()
    nb = store.create(_nb())
    store.attach_source(nb.id, "src-001")
    store.attach_source(nb.id, "src-002")
    store.save_artifact(_artifact_for(nb.id))
    assert len(store.list_artifacts(nb.id)) == 1

    assert store.delete(nb.id) is True
    # Reuse the same store after delete: lists should be empty.
    assert store.list_artifacts(nb.id) == []


def _artifact_for(nb_id: str, params: dict | None = None) -> Artifact:
    p = params or {"max_chunks": 5}
    return Artifact(
        notebook_id=nb_id,
        kind=ArtifactKind.OVERVIEW,
        content={"markdown": "summary"},
        params=p,
        content_hash=make_artifact_hash(nb_id, "overview", p),
    )


def test_save_artifact_returns_input_when_new():
    store = NotebookStore()
    nb = store.create(_nb())
    artifact = _artifact_for(nb.id)
    saved = store.save_artifact(artifact)
    assert saved.id == artifact.id


def test_save_artifact_is_cache_idempotent_on_same_hash():
    store = NotebookStore()
    nb = store.create(_nb())
    a = _artifact_for(nb.id, params={"max_chunks": 5})
    saved_a = store.save_artifact(a)
    # Different artifact instance, SAME content_hash → cache hit, same row.
    b = _artifact_for(nb.id, params={"max_chunks": 5})
    saved_b = store.save_artifact(b)
    assert saved_a.id == saved_b.id


def test_save_artifact_creates_separate_row_for_different_params():
    store = NotebookStore()
    nb = store.create(_nb())
    a = _artifact_for(nb.id, params={"max_chunks": 5})
    b = _artifact_for(nb.id, params={"max_chunks": 10})
    saved_a = store.save_artifact(a)
    saved_b = store.save_artifact(b)
    assert saved_a.id != saved_b.id
    assert len(store.list_artifacts(nb.id)) == 2


def test_make_artifact_hash_is_stable():
    h1 = make_artifact_hash("nb-1", "overview", {"max_chunks": 5})
    h2 = make_artifact_hash("nb-1", "overview", {"max_chunks": 5})
    assert h1 == h2
    h3 = make_artifact_hash("nb-1", "overview", {"max_chunks": 10})
    assert h1 != h3
