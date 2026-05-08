"""Tests for the embedder factory + DeterministicEmbedder."""
import math

from social_arb.notebooks.embedder import (
    DeterministicEmbedder,
    create_embedder,
)


def test_deterministic_embedder_is_normalized():
    e = DeterministicEmbedder(dim=32)
    v = e.embed("hello")
    norm = math.sqrt(sum(x * x for x in v))
    assert math.isclose(norm, 1.0, abs_tol=1e-6)
    assert len(v) == 32


def test_deterministic_embedder_stable_for_same_input():
    e = DeterministicEmbedder(dim=16)
    a = e.embed("the quick brown fox")
    b = e.embed("the quick brown fox")
    assert a == b


def test_deterministic_embedder_differs_for_different_input():
    e = DeterministicEmbedder(dim=16)
    a = e.embed("alpha")
    b = e.embed("beta")
    assert a != b


def test_embed_batch_returns_one_vector_per_input():
    e = DeterministicEmbedder(dim=8)
    out = e.embed_batch(["one", "two", "three"])
    assert len(out) == 3
    assert all(len(v) == 8 for v in out)


def test_factory_default_returns_deterministic(monkeypatch):
    monkeypatch.delenv("EMBEDDER", raising=False)
    e = create_embedder()
    assert isinstance(e, DeterministicEmbedder)
