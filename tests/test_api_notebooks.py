"""FastAPI integration tests for the notebooks router (NB-002).

Uses `TestClient` over an in-process FastAPI app — no real network.
DI hooks are overridden so each test gets fresh stores.
"""
from __future__ import annotations

import io

import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi import FastAPI
from fastapi.testclient import TestClient

from social_arb.api import notebooks as notebooks_router
from social_arb.notebooks.embedder import DeterministicEmbedder
from social_arb.notebooks.notebook_store import NotebookStore
from social_arb.sources import SqliteStore


@pytest.fixture
def app_and_stores():
    """Build a fresh FastAPI app + in-memory stores for one test."""
    app = FastAPI()
    notebook_store = NotebookStore()
    source_store = SqliteStore()
    embedder = DeterministicEmbedder(dim=32)

    app.dependency_overrides[notebooks_router.get_notebook_store] = lambda: notebook_store
    app.dependency_overrides[notebooks_router.get_source_store] = lambda: source_store
    app.dependency_overrides[notebooks_router.get_embedder] = lambda: embedder

    app.include_router(notebooks_router.router, prefix="/api/v1")

    return TestClient(app), notebook_store, source_store


# -- create / get / list --------------------------------------------------- #

def test_create_notebook_returns_201_with_id(app_and_stores):
    client, _, _ = app_and_stores
    r = client.post("/api/v1/notebooks", json={"title": "AMD Q1", "description": "thesis prep"})
    assert r.status_code == 201
    body = r.json()
    assert body["title"] == "AMD Q1"
    assert "id" in body and len(body["id"]) > 0


def test_get_notebook_returns_404_for_unknown(app_and_stores):
    client, _, _ = app_and_stores
    r = client.get("/api/v1/notebooks/does-not-exist")
    assert r.status_code == 404


def test_create_then_get_includes_empty_source_list(app_and_stores):
    client, _, _ = app_and_stores
    nb_id = client.post("/api/v1/notebooks", json={"title": "x"}).json()["id"]
    r = client.get(f"/api/v1/notebooks/{nb_id}")
    assert r.status_code == 200
    assert r.json()["source_ids"] == []


def test_list_notebooks_filters_by_ticker(app_and_stores):
    client, _, _ = app_and_stores
    client.post("/api/v1/notebooks", json={"title": "general"})
    client.post("/api/v1/notebooks", json={"title": "amd", "scope": {"ticker": "AMD"}})
    client.post("/api/v1/notebooks", json={"title": "sq", "scope": {"ticker": "SQ"}})

    r = client.get("/api/v1/notebooks?ticker=AMD")
    assert r.status_code == 200
    titles = [item["title"] for item in r.json()]
    assert titles == ["amd"]


# -- update / delete ------------------------------------------------------- #

def test_patch_updates_title_only(app_and_stores):
    client, _, _ = app_and_stores
    nb_id = client.post("/api/v1/notebooks", json={"title": "old"}).json()["id"]
    r = client.patch(f"/api/v1/notebooks/{nb_id}", json={"title": "new"})
    assert r.status_code == 200
    assert r.json()["title"] == "new"


def test_delete_returns_204_then_404(app_and_stores):
    client, _, _ = app_and_stores
    nb_id = client.post("/api/v1/notebooks", json={"title": "doomed"}).json()["id"]
    assert client.delete(f"/api/v1/notebooks/{nb_id}").status_code == 204
    assert client.delete(f"/api/v1/notebooks/{nb_id}").status_code == 404


# -- source attach / detach ----------------------------------------------- #

def test_attach_existing_source(app_and_stores):
    client, _, source_store = app_and_stores
    # Seed a Source in the source store.
    from social_arb.sources.models import Source, SourceKind
    src = Source.build(text="seed", kind=SourceKind.TEXT, title="seed")
    source_store.save(src, [])

    nb_id = client.post("/api/v1/notebooks", json={"title": "x"}).json()["id"]
    r = client.post(f"/api/v1/notebooks/{nb_id}/sources", json={"source_id": src.id})
    assert r.status_code == 200
    assert src.id in r.json()["source_ids"]


def test_attach_missing_source_returns_404(app_and_stores):
    client, _, _ = app_and_stores
    nb_id = client.post("/api/v1/notebooks", json={"title": "x"}).json()["id"]
    r = client.post(f"/api/v1/notebooks/{nb_id}/sources", json={"source_id": "missing"})
    assert r.status_code == 404


def test_attach_to_missing_notebook_returns_404(app_and_stores):
    client, _, source_store = app_and_stores
    from social_arb.sources.models import Source, SourceKind
    src = Source.build(text="x", kind=SourceKind.TEXT, title="x")
    source_store.save(src, [])
    r = client.post("/api/v1/notebooks/missing/sources", json={"source_id": src.id})
    assert r.status_code == 404


def test_detach_returns_204_then_404(app_and_stores):
    client, notebook_store, _ = app_and_stores
    nb_id = client.post("/api/v1/notebooks", json={"title": "x"}).json()["id"]
    notebook_store.attach_source(nb_id, "src-001")
    assert client.delete(f"/api/v1/notebooks/{nb_id}/sources/src-001").status_code == 204
    assert client.delete(f"/api/v1/notebooks/{nb_id}/sources/src-001").status_code == 404


# -- upload (parse + chunk + embed + attach in one shot) ------------------ #

def test_upload_text_file_round_trip(app_and_stores):
    client, _, source_store = app_and_stores
    nb_id = client.post("/api/v1/notebooks", json={"title": "x"}).json()["id"]

    blob = b"AMD reported strong Q1 earnings. Divergence 70.4. Coherence 100."
    files = {"file": ("amd.txt", io.BytesIO(blob), "text/plain")}
    r = client.post(f"/api/v1/notebooks/{nb_id}/sources/upload", files=files)
    assert r.status_code == 201
    body = r.json()
    assert len(body["source_ids"]) == 1
    # The uploaded source should now be in the source store too.
    assert source_store.get(body["source_ids"][0]) is not None


def test_upload_unsupported_type_returns_415(app_and_stores):
    client, _, _ = app_and_stores
    nb_id = client.post("/api/v1/notebooks", json={"title": "x"}).json()["id"]
    files = {"file": ("blob.bin", io.BytesIO(b"\x00\x01\x02"), "application/octet-stream")}
    r = client.post(f"/api/v1/notebooks/{nb_id}/sources/upload", files=files)
    assert r.status_code == 415


# -- artifacts ------------------------------------------------------------ #

def test_list_artifacts_empty(app_and_stores):
    client, _, _ = app_and_stores
    nb_id = client.post("/api/v1/notebooks", json={"title": "x"}).json()["id"]
    r = client.get(f"/api/v1/notebooks/{nb_id}/artifacts")
    assert r.status_code == 200
    assert r.json() == []


def test_list_artifacts_unknown_notebook_returns_404(app_and_stores):
    client, _, _ = app_and_stores
    r = client.get("/api/v1/notebooks/missing/artifacts")
    assert r.status_code == 404
