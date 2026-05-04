"""EmbedderProtocol + two implementations (DLOG-21).

DeterministicEmbedder is a tiny built-in fallback used in unit tests
that need vectors but don't want a 400MB model download or a Voyage
API key. Production wires SentenceTransformersEmbedder or
VoyageEmbedder via env config.
"""
from __future__ import annotations

import hashlib
import math
import os
from typing import Protocol


class EmbedderProtocol(Protocol):
    dim: int

    def embed_batch(self, texts: list[str]) -> list[list[float]]: ...

    def embed(self, text: str) -> list[float]:
        return self.embed_batch([text])[0]


# --------------------------------------------------------------------------- #
# Deterministic fallback (no deps, used in tests)
# --------------------------------------------------------------------------- #

class DeterministicEmbedder:
    """Hash-based embedder. Fast, dependency-free, deterministic.

    Not semantically meaningful — useful only for tests that exercise
    storage and retrieval mechanics. For real similarity, use
    SentenceTransformersEmbedder or VoyageEmbedder.
    """

    def __init__(self, dim: int = 64) -> None:
        self.dim = dim

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [self._hash_embed(t) for t in texts]

    def embed(self, text: str) -> list[float]:
        return self._hash_embed(text)

    def _hash_embed(self, text: str) -> list[float]:
        # Spread bytes of multiple sha256 digests across the dimension.
        out: list[float] = []
        seed = text.encode("utf-8")
        i = 0
        while len(out) < self.dim:
            h = hashlib.sha256(seed + i.to_bytes(4, "little")).digest()
            for byte in h:
                if len(out) >= self.dim:
                    break
                # Map byte (0..255) to (-1, 1)
                out.append((byte / 127.5) - 1.0)
            i += 1
        # Normalize so cosine sim is well-behaved.
        norm = math.sqrt(sum(v * v for v in out)) or 1.0
        return [v / norm for v in out]


# --------------------------------------------------------------------------- #
# Sentence-transformers (local, free)
# --------------------------------------------------------------------------- #

class SentenceTransformersEmbedder:
    """Local embedder using sentence-transformers.

    Default model `all-MiniLM-L6-v2` — 384 dim, ~80MB, decent quality
    for general English. Lazy-loads the model on first call so import
    of this module is free.
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2", dim: int = 384) -> None:
        self.model_name = model_name
        self.dim = dim
        self._model = None

    def _load(self):
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer  # type: ignore
            except ImportError as e:
                raise ImportError(
                    "sentence-transformers not installed — "
                    "`pip install sentence-transformers`"
                ) from e
            self._model = SentenceTransformer(self.model_name)
        return self._model

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        model = self._load()
        vecs = model.encode(texts, normalize_embeddings=True)
        return [v.tolist() for v in vecs]

    def embed(self, text: str) -> list[float]:
        return self.embed_batch([text])[0]


# --------------------------------------------------------------------------- #
# Voyage AI (production, finance-tuned)
# --------------------------------------------------------------------------- #

class VoyageEmbedder:
    """Voyage AI finance-tuned embedder (DLOG-21).

    Requires VOYAGE_API_KEY env var. Default model `voyage-finance-2`
    — 1024 dim, finance-domain-tuned.
    """

    def __init__(self, model_name: str = "voyage-finance-2", dim: int = 1024) -> None:
        self.model_name = model_name
        self.dim = dim
        self._client = None

    def _client_lazy(self):
        if self._client is not None:
            return self._client
        try:
            import voyageai  # type: ignore
        except ImportError as e:
            raise ImportError("voyageai not installed — `pip install voyageai`") from e
        api_key = os.environ.get("VOYAGE_API_KEY")
        if not api_key:
            raise RuntimeError("VOYAGE_API_KEY env var not set")
        self._client = voyageai.Client(api_key=api_key)
        return self._client

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        client = self._client_lazy()
        result = client.embed(texts, model=self.model_name, input_type="document")
        return list(result.embeddings)

    def embed(self, text: str) -> list[float]:
        return self.embed_batch([text])[0]


# --------------------------------------------------------------------------- #
# Factory
# --------------------------------------------------------------------------- #

def create_embedder(kind: str | None = None) -> EmbedderProtocol:
    """Pick an embedder by env or explicit kind.

    Resolution order:
      explicit `kind` arg > EMBEDDER env var > 'deterministic' default.

    Valid kinds: 'deterministic' | 'sentence-transformers' | 'voyage'
    """
    chosen = (kind or os.environ.get("EMBEDDER") or "deterministic").lower()
    if chosen in ("st", "sentence-transformers"):
        return SentenceTransformersEmbedder()
    if chosen == "voyage":
        return VoyageEmbedder()
    return DeterministicEmbedder()
