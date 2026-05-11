"""Tests for the Studio orchestrator: cache lookup, regenerate bypass,
generator registry."""
from __future__ import annotations

import pytest

from social_arb.notebooks.chunker import Chunker
from social_arb.notebooks.embedder import DeterministicEmbedder
from social_arb.notebooks.notebook_models import ArtifactKind, Notebook
from social_arb.notebooks.notebook_store import NotebookStore
from social_arb.notebooks.parsers import ContentHint, parse_blob
from social_arb.rag import Citation, EchoLLM, Retriever
from social_arb.sources import ChunkWithVector, SqliteStore
from social_arb.studio import Studio, default_studio
from social_arb.studio.base import GeneratorProtocol


class FakeGenerator:
    """Counts build() calls so cache tests can detect cache hit vs miss."""

    kind = ArtifactKind.OVERVIEW
    version = "vfake"

    def __init__(self) -> None:
        self.call_count = 0

    def build(self, notebook_id, params, *, retriever, llm):
        self.call_count += 1
        return ({"markdown": f"build #{self.call_count}", "sections": {}}, [])


@pytest.fixture
def basic_stack():
    sources = SqliteStore()
    notebooks = NotebookStore()
    embedder = DeterministicEmbedder(dim=32)
    parsed = parse_blob(b"hello world", ContentHint(filename="x.txt"))
    source, chunks = Chunker().chunk(parsed)
    vectors = embedder.embed_batch([c.text for c in chunks])
    sources.save(source, [ChunkWithVector(chunk=c, vector=v) for c, v in zip(chunks, vectors)])
    nb = notebooks.create(Notebook(title="x"))
    notebooks.attach_source(nb.id, source.id)
    return sources, notebooks, embedder, nb


def test_default_studio_supports_overview_and_mindmap(basic_stack):
    _, notebooks, _, _ = basic_stack
    s = default_studio(notebooks)
    assert set(s.supported_kinds) == {ArtifactKind.OVERVIEW, ArtifactKind.MIND_MAP}


def test_generate_calls_generator_once_then_cache(basic_stack):
    sources, notebooks, embedder, nb = basic_stack
    fake = FakeGenerator()
    studio = Studio(notebooks, generators={ArtifactKind.OVERVIEW: fake})

    retriever = Retriever(sources, notebooks, embedder)
    llm = EchoLLM()

    a1 = studio.generate(nb.id, ArtifactKind.OVERVIEW, {"max_chunks": 5},
                         retriever=retriever, llm=llm)
    a2 = studio.generate(nb.id, ArtifactKind.OVERVIEW, {"max_chunks": 5},
                         retriever=retriever, llm=llm)
    assert fake.call_count == 1  # second call is a cache hit
    assert a1.id == a2.id


def test_generate_with_regenerate_creates_new_artifact(basic_stack):
    sources, notebooks, embedder, nb = basic_stack
    fake = FakeGenerator()
    studio = Studio(notebooks, generators={ArtifactKind.OVERVIEW: fake})

    retriever = Retriever(sources, notebooks, embedder)
    llm = EchoLLM()

    a1 = studio.generate(nb.id, ArtifactKind.OVERVIEW, {"x": 1},
                         retriever=retriever, llm=llm)
    a2 = studio.generate(nb.id, ArtifactKind.OVERVIEW, {"x": 1},
                         retriever=retriever, llm=llm, regenerate=True)
    assert fake.call_count == 2
    assert a1.id != a2.id
    # Both artifacts are kept (frozen per DLOG-19).
    assert len(notebooks.list_artifacts(nb.id)) == 2


def test_generate_different_params_produces_different_artifacts(basic_stack):
    sources, notebooks, embedder, nb = basic_stack
    fake = FakeGenerator()
    studio = Studio(notebooks, generators={ArtifactKind.OVERVIEW: fake})

    retriever = Retriever(sources, notebooks, embedder)
    llm = EchoLLM()

    a1 = studio.generate(nb.id, ArtifactKind.OVERVIEW, {"k": 5},
                         retriever=retriever, llm=llm)
    a2 = studio.generate(nb.id, ArtifactKind.OVERVIEW, {"k": 10},
                         retriever=retriever, llm=llm)
    assert fake.call_count == 2
    assert a1.content_hash != a2.content_hash


def test_generate_unsupported_kind_raises(basic_stack):
    _, notebooks, _, nb = basic_stack
    studio = Studio(notebooks, generators={})
    with pytest.raises(ValueError):
        studio.generate(nb.id, ArtifactKind.SLIDE_DECK, {},
                        retriever=None, llm=None)
