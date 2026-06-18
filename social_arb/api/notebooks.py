"""FastAPI router — Notebook REST endpoints (NB-002).

Mounts at `/api/v1/notebooks` (caller wires via `include_router`).

Endpoints
---------
POST   /notebooks                       Create
GET    /notebooks                       List (filter by scope)
GET    /notebooks/{id}                  Fetch with source + artifact IDs
PATCH  /notebooks/{id}                  Update title / description / scope
DELETE /notebooks/{id}                  Delete (cascade artifacts + attachments)
POST   /notebooks/{id}/sources          Attach existing Source by id
POST   /notebooks/{id}/sources/upload   Upload file → parse → Source → attach (one shot)
DELETE /notebooks/{id}/sources/{sid}    Detach
GET    /notebooks/{id}/artifacts        List artifacts on this notebook
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from social_arb.notebooks.chunker import Chunker
from social_arb.notebooks.embedder import EmbedderProtocol, create_embedder
from social_arb.notebooks.notebook_models import (
    Artifact,
    AttachSourceRequest,
    CreateNotebookRequest,
    Notebook,
    NotebookListItem,
    NotebookScope,
    UpdateNotebookRequest,
)
from social_arb.notebooks.notebook_store import NotebookStore
from social_arb.notebooks.parsers import ContentHint, parse_blob
from social_arb.sources import ChunkWithVector, SourceStore, create_store
from social_arb.sources.models import Source

router = APIRouter(prefix="/notebooks", tags=["notebooks"])


# --- DI hooks (overridable in tests) -------------------------------------- #

def get_notebook_store() -> NotebookStore:
    """Default DI: in-memory NotebookStore. Override in production wiring."""
    if not hasattr(get_notebook_store, "_singleton"):
        get_notebook_store._singleton = NotebookStore()
    return get_notebook_store._singleton


def get_source_store() -> SourceStore:
    if not hasattr(get_source_store, "_singleton"):
        get_source_store._singleton = create_store()
    return get_source_store._singleton


def get_embedder() -> EmbedderProtocol:
    if not hasattr(get_embedder, "_singleton"):
        get_embedder._singleton = create_embedder()
    return get_embedder._singleton


# --- endpoints ------------------------------------------------------------ #

@router.post("", response_model=Notebook, status_code=status.HTTP_201_CREATED)
def create_notebook(
    body: CreateNotebookRequest,
    store: Annotated[NotebookStore, Depends(get_notebook_store)],
) -> Notebook:
    notebook = Notebook(
        title=body.title,
        description=body.description,
        scope=body.scope,
    )
    return store.create(notebook)


@router.get("", response_model=list[NotebookListItem])
def list_notebooks(
    store: Annotated[NotebookStore, Depends(get_notebook_store)],
    ticker: str | None = None,
    mosaic_id: str | None = None,
    thesis_id: str | None = None,
    decision_id: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[NotebookListItem]:
    return store.list(
        ticker=ticker,
        mosaic_id=mosaic_id,
        thesis_id=thesis_id,
        decision_id=decision_id,
        limit=limit,
        offset=offset,
    )


@router.get("/{notebook_id}", response_model=Notebook)
def get_notebook(
    notebook_id: str,
    store: Annotated[NotebookStore, Depends(get_notebook_store)],
) -> Notebook:
    nb = store.get(notebook_id)
    if nb is None:
        raise HTTPException(404, f"notebook {notebook_id} not found")
    return nb


@router.patch("/{notebook_id}", response_model=Notebook)
def update_notebook(
    notebook_id: str,
    body: UpdateNotebookRequest,
    store: Annotated[NotebookStore, Depends(get_notebook_store)],
) -> Notebook:
    nb = store.update(
        notebook_id,
        title=body.title,
        description=body.description,
        scope=body.scope,
    )
    if nb is None:
        raise HTTPException(404, f"notebook {notebook_id} not found")
    return nb


@router.delete("/{notebook_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_notebook(
    notebook_id: str,
    store: Annotated[NotebookStore, Depends(get_notebook_store)],
) -> None:
    if not store.delete(notebook_id):
        raise HTTPException(404, f"notebook {notebook_id} not found")


@router.post("/{notebook_id}/sources", response_model=Notebook, status_code=status.HTTP_200_OK)
def attach_source(
    notebook_id: str,
    body: AttachSourceRequest,
    store: Annotated[NotebookStore, Depends(get_notebook_store)],
    sources: Annotated[SourceStore, Depends(get_source_store)],
) -> Notebook:
    nb = store.get(notebook_id, include_attached=False)
    if nb is None:
        raise HTTPException(404, f"notebook {notebook_id} not found")
    if sources.get(body.source_id) is None:
        raise HTTPException(404, f"source {body.source_id} not found")
    store.attach_source(notebook_id, body.source_id)
    return store.get(notebook_id)


@router.post(
    "/{notebook_id}/sources/upload",
    response_model=Notebook,
    status_code=status.HTTP_201_CREATED,
)
async def upload_source(
    notebook_id: str,
    store: Annotated[NotebookStore, Depends(get_notebook_store)],
    sources: Annotated[SourceStore, Depends(get_source_store)],
    embedder: Annotated[EmbedderProtocol, Depends(get_embedder)],
    file: UploadFile = File(...),
    title: str | None = Form(default=None),
) -> Notebook:
    """One-shot: upload file → parse → chunk → embed → store as Source → attach to Notebook."""
    nb = store.get(notebook_id, include_attached=False)
    if nb is None:
        raise HTTPException(404, f"notebook {notebook_id} not found")

    blob = await file.read()
    hint = ContentHint(
        content_type=file.content_type,
        filename=file.filename,
        title_hint=title,
    )
    try:
        parsed = parse_blob(blob, hint)
    except ValueError as e:
        raise HTTPException(415, f"unsupported file type: {e}") from e

    chunker = Chunker()
    source, chunks = chunker.chunk(parsed)
    vectors = embedder.embed_batch([c.text for c in chunks])
    chunks_with_vec = [
        ChunkWithVector(chunk=c, vector=v) for c, v in zip(chunks, vectors)
    ]
    sources.save(source, chunks_with_vec)
    store.attach_source(notebook_id, source.id)

    return store.get(notebook_id)


@router.delete(
    "/{notebook_id}/sources/{source_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def detach_source(
    notebook_id: str,
    source_id: str,
    store: Annotated[NotebookStore, Depends(get_notebook_store)],
) -> None:
    if not store.detach_source(notebook_id, source_id):
        raise HTTPException(404, f"attachment ({notebook_id}, {source_id}) not found")


@router.get("/{notebook_id}/artifacts", response_model=list[Artifact])
def list_artifacts(
    notebook_id: str,
    store: Annotated[NotebookStore, Depends(get_notebook_store)],
) -> list[Artifact]:
    if store.get(notebook_id, include_attached=False) is None:
        raise HTTPException(404, f"notebook {notebook_id} not found")
    return store.list_artifacts(notebook_id)
