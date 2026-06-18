"""Retriever — top-k chunk lookup scoped to a Notebook's source set.

Wraps the existing `SourceStore.search_similar` (NB-001) with the
notebook-scope filter from the Notebook's `source_ids` (NB-002). Adds
no per-chunk re-ranking yet — that's an NB-003.5 if cited-RAG quality
demands it.
"""
from __future__ import annotations

import time

from pydantic import BaseModel

from social_arb.notebooks.embedder import EmbedderProtocol
from social_arb.notebooks.notebook_store import NotebookStore
from social_arb.sources import SourceStore
from social_arb.sources.models import SourceChunk


class RetrievedChunk(BaseModel):
    chunk: SourceChunk
    score: float


class RetrievalResult(BaseModel):
    notebook_id: str
    query: str
    chunks: list[RetrievedChunk]
    elapsed_ms: float


class Retriever:
    def __init__(
        self,
        sources: SourceStore,
        notebooks: NotebookStore,
        embedder: EmbedderProtocol,
    ) -> None:
        self._sources = sources
        self._notebooks = notebooks
        self._embedder = embedder

    def retrieve(
        self,
        notebook_id: str,
        query: str,
        *,
        k: int = 8,
    ) -> RetrievalResult:
        notebook = self._notebooks.get(notebook_id)
        if notebook is None:
            raise LookupError(f"notebook {notebook_id} not found")

        t0 = time.perf_counter()
        if not notebook.source_ids:
            return RetrievalResult(
                notebook_id=notebook_id,
                query=query,
                chunks=[],
                elapsed_ms=(time.perf_counter() - t0) * 1000,
            )

        query_vec = self._embedder.embed_batch([query])[0]
        hits = self._sources.search_similar(
            query_vec,
            k=k,
            filter_source_ids=notebook.source_ids,
        )
        elapsed_ms = (time.perf_counter() - t0) * 1000
        return RetrievalResult(
            notebook_id=notebook_id,
            query=query,
            chunks=[RetrievedChunk(chunk=h.chunk, score=h.score) for h in hits],
            elapsed_ms=elapsed_ms,
        )
