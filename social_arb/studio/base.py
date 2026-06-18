"""Studio core — orchestrates generator selection, caching, and persistence.

A Studio generator is a pure function of `(notebook, params, retriever, llm)` →
`(content, citations)`. The Studio class wraps that function with:

- Content-hash cache lookup (DLOG-19) — same inputs return the existing artifact
  without re-burning LLM tokens.
- Artifact persistence — every output is stored frozen and listable via
  `GET /notebooks/{id}/artifacts`.
- Regenerate bypass — explicit re-run when the user wants a fresh artifact.

Per DLOG-19, frozen artifacts are kept by content hash. Old artifacts are never
deleted on regenerate; instead a new artifact with a new hash is saved alongside.
"""
from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from social_arb.notebooks.notebook_models import (
    Artifact,
    ArtifactKind,
    make_artifact_hash,
)
from social_arb.notebooks.notebook_store import NotebookStore
from social_arb.rag import Citation, LLMProtocol, Retriever


@runtime_checkable
class GeneratorProtocol(Protocol):
    """A Studio generator. One per ArtifactKind.

    Implementations live in `social_arb/studio/<kind>.py` and follow the
    contract: build content from the notebook's source chunks via the
    retriever + llm, return the content blob plus the list of citations
    that grounded it.
    """

    kind: ArtifactKind

    def build(
        self,
        notebook_id: str,
        params: dict[str, Any],
        *,
        retriever: Retriever,
        llm: LLMProtocol,
    ) -> tuple[dict[str, Any], list[Citation]]: ...


class Studio:
    """Orchestrator. Owns the generator registry + cache lookup."""

    def __init__(
        self,
        store: NotebookStore,
        generators: dict[ArtifactKind, GeneratorProtocol],
    ) -> None:
        self._store = store
        self._generators = dict(generators)

    @property
    def supported_kinds(self) -> list[ArtifactKind]:
        return list(self._generators.keys())

    def generate(
        self,
        notebook_id: str,
        kind: ArtifactKind,
        params: dict[str, Any],
        *,
        retriever: Retriever,
        llm: LLMProtocol,
        regenerate: bool = False,
    ) -> Artifact:
        """Cache-or-build. Returns the persisted Artifact.

        Cache key is `make_artifact_hash(notebook_id, kind, params)` — same
        notebook + same params + same kind → cache hit. The actual cache
        row uniqueness is enforced at the NotebookStore layer (DLOG-19).
        """
        if kind not in self._generators:
            raise ValueError(
                f"no generator registered for {kind!r}; "
                f"supported: {[k.value for k in self._generators]}"
            )

        content_hash = make_artifact_hash(notebook_id, kind.value, params)

        if not regenerate:
            cached = self._store.find_artifact_by_hash(notebook_id, kind, content_hash)
            if cached is not None:
                return cached

        generator = self._generators[kind]
        content, citations = generator.build(
            notebook_id,
            params,
            retriever=retriever,
            llm=llm,
        )
        artifact = Artifact(
            notebook_id=notebook_id,
            kind=kind,
            content=content,
            params=params,
            content_hash=content_hash if not regenerate else f"{content_hash}-r{_now_ns()}",
            citations=[c.token for c in citations],
            generator_version=getattr(generator, "version", "v0"),
        )
        return self._store.save_artifact(artifact)


def _now_ns() -> int:
    """Monotonic-ish suffix so regenerate produces a distinct content_hash.
    Keeps the original cached artifact intact (frozen) per DLOG-19."""
    import time
    return time.monotonic_ns()
