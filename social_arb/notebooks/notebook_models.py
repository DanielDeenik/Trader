"""Notebook + Artifact models (NB-002).

A Notebook bundles Sources (NB-001) into a scoped working set. An
Artifact is a frozen Studio output (NB-004) — kept by content hash so
the same input never regenerates twice (DLOG-19).

DLOG-18: scope is optional — a notebook can be standalone (general
research) OR linked to a ticker / mosaic / thesis / decision.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class NotebookScope(BaseModel):
    """Optional scope binding a notebook to a domain entity."""

    ticker: str | None = None
    mosaic_id: str | None = None
    thesis_id: str | None = None
    decision_id: str | None = None

    @property
    def is_empty(self) -> bool:
        return all(
            v is None
            for v in (self.ticker, self.mosaic_id, self.thesis_id, self.decision_id)
        )


class Notebook(BaseModel):
    """A user-curated bundle of Sources with optional scope.

    `id` is generated server-side (UUID4). Sources reference the same
    notebook by `notebook_id` in the join table; the Pydantic model
    holds `source_ids` for convenience when fetching with
    `NotebookStore.get(id, include_sources=True)`.
    """

    model_config = ConfigDict(use_enum_values=True)

    id: str = Field(default_factory=lambda: uuid4().hex)
    title: str
    description: str | None = None
    scope: NotebookScope = Field(default_factory=NotebookScope)
    source_ids: list[str] = Field(default_factory=list)
    artifact_ids: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ArtifactKind(str, Enum):
    """Studio output kinds. Extended as NB-004+ ships generators."""

    OVERVIEW = "overview"        # Markdown brief
    MIND_MAP = "mind_map"        # Cytoscape JSON
    SLIDE_DECK = "slide_deck"    # NB-009
    AUDIO_OVERVIEW = "audio"     # NB-008
    REPORT = "report"            # NB-010
    FLASHCARDS = "flashcards"    # NB-010
    QUIZ = "quiz"                # NB-010
    DATA_TABLE = "data_table"    # NB-010


class Artifact(BaseModel):
    """A Studio output. Cached by content hash (DLOG-19).

    `content` shape depends on `kind`:
      - overview     → {"markdown": str}
      - mind_map     → {"nodes": [...], "edges": [...]}
      - slide_deck   → {"slides": [...]}
      - audio        → {"audio_url": str, "duration_s": int}
      - report       → {"sections": [...]}
      - flashcards   → {"cards": [...]}
      - quiz         → {"questions": [...]}
      - data_table   → {"columns": [...], "rows": [...]}
    """

    model_config = ConfigDict(use_enum_values=True)

    id: str = Field(default_factory=lambda: uuid4().hex)
    notebook_id: str
    kind: ArtifactKind
    content: dict[str, Any] = Field(default_factory=dict)
    params: dict[str, Any] = Field(default_factory=dict)
    content_hash: str = Field(default="", description="cache key from (notebook_id, kind, params)")
    citations: list[str] = Field(default_factory=list)
    generator_version: str = "v0"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


def make_artifact_hash(notebook_id: str, kind: str, params: dict[str, Any]) -> str:
    """Deterministic content hash so identical inputs hit cache (DLOG-19)."""
    payload = json.dumps(
        {"nb": notebook_id, "kind": kind, "params": params},
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:32]


# --- request/response shapes for the API layer ---------------------------- #

class CreateNotebookRequest(BaseModel):
    title: str
    description: str | None = None
    scope: NotebookScope = Field(default_factory=NotebookScope)


class UpdateNotebookRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    scope: NotebookScope | None = None


class AttachSourceRequest(BaseModel):
    source_id: str


class NotebookListItem(BaseModel):
    """Lightweight projection for list endpoints."""

    id: str
    title: str
    description: str | None
    scope: NotebookScope
    source_count: int
    artifact_count: int
    created_at: datetime
    updated_at: datetime
