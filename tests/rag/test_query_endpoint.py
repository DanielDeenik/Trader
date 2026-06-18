"""FastAPI integration test for the new /query endpoint (NB-003)."""
from __future__ import annotations

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


@pytest.fixture
def client_with_notebook():
    app = FastAPI()
    notebook_store = NotebookStore()
    source_store = SqliteStore()
    embedder = DeterministicEmbedder(dim=32)

    # Seed an AMD notebook with a real source.
    parsed = parse_blob(
        b"AMD reported strong Q1 earnings. Revenue rose 32% YoY.",
        ContentHint(filename="amd.txt"),
    )
    chunker = Chunker()
    source, chunks = chunker.chunk(parsed)
    vectors = embedder.embed_batch([c.text for c in chunks])
    source_store.save(source, [ChunkWithVector(chunk=c, vector=v) for c, v in zip(chunks, vectors)])
    nb = notebook_store.create(Notebook(title="AMD Q1"))
    notebook_store.attach_source(nb.id, source.id)

    # EchoLLM that cites the real chunk.
    llm = EchoLLM(cite_chunks=[(source.id, chunks[0].id)])

    app.dependency_overrides[notebooks_router.get_notebook_store] = lambda: notebook_store
    app.dependency_overrides[notebooks_router.get_source_store] = lambda: source_store
    app.dependency_overrides[notebooks_router.get_embedder] = lambda: embedder
    app.dependency_overrides[notebooks_router.get_llm] = lambda: llm
    app.include_router(notebooks_router.router, prefix="/api/v1")

    return TestClient(app), nb.id, source.id, chunks[0].id


def test_query_returns_cited_answer(client_with_notebook):
    client, nb_id, src_id, chunk_id = client_with_notebook
    r = client.post(f"/api/v1/notebooks/{nb_id}/query", json={"prompt": "What's AMD's growth?"})
    assert r.status_code == 200
    body = r.json()
    assert body["notebook_id"] == nb_id
    assert len(body["citations"]) == 1
    assert body["citations"][0]["source_id"] == src_id
    assert body["citations"][0]["chunk_id"] == chunk_id
    assert body["hallucinated"] == []


def test_query_unknown_notebook_returns_404(client_with_notebook):
    client, *_ = client_with_notebook
    r = client.post("/api/v1/notebooks/missing/query", json={"prompt": "anything"})
    assert r.status_code == 404


def test_query_validates_request_shape(client_with_notebook):
    client, nb_id, *_ = client_with_notebook
    r = client.post(f"/api/v1/notebooks/{nb_id}/query", json={"prompt": ""})
    assert r.status_code == 422  # min_length=1
    r = client.post(f"/api/v1/notebooks/{nb_id}/query", json={"prompt": "ok", "max_chunks": 0})
    assert r.status_code == 422
