"""FastAPI integration tests for POST /artifacts (NB-004)."""
from __future__ import annotations

import json

import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi import FastAPI
from fastapi.testclient import TestClient

from social_arb.api import notebooks as notebooks_router
from social_arb.notebooks.chunker import Chunker
from social_arb.notebooks.embedder import DeterministicEmbedder
from social_arb.notebooks.notebook_models import Notebook
from social_arb.notebooks.notebook_store import NotebookStore
from social_arb.notebooks.parsers import ContentHint, parse_blob
from social_arb.rag import EchoLLM
from social_arb.sources import ChunkWithVector, SqliteStore
from social_arb.studio import default_studio


@pytest.fixture
def client_and_state():
    app = FastAPI()
    notebook_store = NotebookStore()
    source_store = SqliteStore()
    embedder = DeterministicEmbedder(dim=32)

    parsed = parse_blob(b"AMD competes with NVDA. Lisa Su is CEO.", ContentHint(filename="amd.txt"))
    source, chunks = Chunker().chunk(parsed)
    vectors = embedder.embed_batch([c.text for c in chunks])
    source_store.save(source, [ChunkWithVector(chunk=c, vector=v) for c, v in zip(chunks, vectors)])
    nb = notebook_store.create(Notebook(title="AMD"))
    notebook_store.attach_source(nb.id, source.id)

    # EchoLLM that returns canned JSON for mind-map AND a structured overview.
    # Switched per-test via dependency_overrides as needed.
    overview_template = (
        "## Thesis\nAMD has structural upside [s:{sid}:{cid}].\n\n"
        "## Catalysts\nQ1 earnings May 5 [s:{sid}:{cid}].\n\n"
        "## Risks\nHelios execution risk [s:{sid}:{cid}].\n\n"
        "## Recent signals\nReddit chatter [s:{sid}:{cid}]."
    ).format(sid=source.id, cid=chunks[0].id)
    overview_llm = EchoLLM(answer_template=overview_template)

    app.dependency_overrides[notebooks_router.get_notebook_store] = lambda: notebook_store
    app.dependency_overrides[notebooks_router.get_source_store] = lambda: source_store
    app.dependency_overrides[notebooks_router.get_embedder] = lambda: embedder
    app.dependency_overrides[notebooks_router.get_llm] = lambda: overview_llm
    app.dependency_overrides[notebooks_router.get_studio] = lambda: default_studio(notebook_store)
    app.include_router(notebooks_router.router, prefix="/api/v1")

    return TestClient(app), notebook_store, nb.id


def test_generate_overview_returns_201_with_sections(client_and_state):
    client, _, nb_id = client_and_state
    r = client.post(
        f"/api/v1/notebooks/{nb_id}/artifacts",
        json={"kind": "overview", "params": {"max_chunks": 5}},
    )
    assert r.status_code == 201
    body = r.json()
    assert body["kind"] == "overview"
    sections = body["content"]["sections"]
    assert "thesis" in sections


def test_generate_returns_cached_on_second_call(client_and_state):
    client, _, nb_id = client_and_state
    payload = {"kind": "overview", "params": {"max_chunks": 5}}
    a = client.post(f"/api/v1/notebooks/{nb_id}/artifacts", json=payload).json()
    b = client.post(f"/api/v1/notebooks/{nb_id}/artifacts", json=payload).json()
    assert a["id"] == b["id"]


def test_regenerate_creates_new_artifact(client_and_state):
    client, store, nb_id = client_and_state
    payload = {"kind": "overview", "params": {"max_chunks": 5}}
    first = client.post(f"/api/v1/notebooks/{nb_id}/artifacts", json=payload).json()
    again = client.post(
        f"/api/v1/notebooks/{nb_id}/artifacts",
        json={**payload, "regenerate": True},
    ).json()
    assert first["id"] != again["id"]
    assert len(store.list_artifacts(nb_id)) == 2


def test_generate_404_on_missing_notebook(client_and_state):
    client, *_ = client_and_state
    r = client.post(
        "/api/v1/notebooks/does-not-exist/artifacts",
        json={"kind": "overview"},
    )
    assert r.status_code == 404


def test_generate_400_on_unknown_artifact_kind(client_and_state):
    client, _, nb_id = client_and_state
    r = client.post(
        f"/api/v1/notebooks/{nb_id}/artifacts",
        json={"kind": "garbage_kind"},
    )
    assert r.status_code == 422   # FastAPI validates the enum before reaching the route
