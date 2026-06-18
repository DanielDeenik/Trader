"""Tests for the cited-RAG layer — parse, validate, generate, end-to-end."""
from __future__ import annotations

import pytest

from social_arb.notebooks.chunker import Chunker
from social_arb.notebooks.embedder import DeterministicEmbedder
from social_arb.notebooks.notebook_models import Notebook
from social_arb.notebooks.notebook_store import NotebookStore
from social_arb.notebooks.parsers import ContentHint, parse_blob
from social_arb.rag import (
    Citation,
    CitedGenerator,
    EchoLLM,
    Retriever,
    parse_citations,
    strip_hallucinated,
    validate_citations,
)
from social_arb.rag.retriever import RetrievedChunk
from social_arb.sources import ChunkWithVector, SqliteStore
from social_arb.sources.models import Source, SourceKind


# -- citation parsing -------------------------------------------------------- #

def test_parse_citations_extracts_all():
    text = "Earnings rose 32% [s:src-amd:c-001]. Coherence held [s:src-amd:c-002] flat."
    cites = parse_citations(text)
    assert [(c.source_id, c.chunk_id) for c in cites] == [
        ("src-amd", "c-001"),
        ("src-amd", "c-002"),
    ]


def test_parse_citations_handles_no_citations():
    assert parse_citations("Nothing here.") == []


def test_parse_citations_handles_dashes_and_ids_with_colons():
    text = "Look [s:src-edgar:filings:ch-7] here."
    cites = parse_citations(text)
    # The regex is greedy: `src-edgar:filings` is the source_id, `ch-7` the chunk_id.
    assert cites[0].source_id == "src-edgar:filings"
    assert cites[0].chunk_id == "ch-7"


# -- validation -------------------------------------------------------------- #

def _retrieved(source_id: str, chunk_id: str, text: str = "x") -> RetrievedChunk:
    from social_arb.sources.models import SourceChunk
    return RetrievedChunk(
        chunk=SourceChunk(
            id=chunk_id,
            source_id=source_id,
            chunk_index=0,
            text=text,
            token_count=1,
            char_count=len(text),
        ),
        score=0.99,
    )


def test_validate_citations_splits_valid_and_hallucinated():
    retrieved = [_retrieved("s1", "c1"), _retrieved("s1", "c2")]
    cites = [
        Citation(source_id="s1", chunk_id="c1"),    # valid
        Citation(source_id="s1", chunk_id="c99"),   # hallucinated
        Citation(source_id="ghost", chunk_id="c1"), # hallucinated
    ]
    valid, hallucinated = validate_citations(cites, retrieved)
    assert [(c.source_id, c.chunk_id) for c in valid] == [("s1", "c1")]
    assert {(c.source_id, c.chunk_id) for c in hallucinated} == {
        ("s1", "c99"),
        ("ghost", "c1"),
    }


def test_strip_hallucinated_removes_only_hallucinated_tokens():
    text = "Real claim [s:s1:c1] and fake [s:s1:c99] together."
    hallucinated = [Citation(source_id="s1", chunk_id="c99")]
    cleaned = strip_hallucinated(text, hallucinated)
    assert "[s:s1:c1]" in cleaned
    assert "[s:s1:c99]" not in cleaned


def test_strip_hallucinated_no_op_when_none():
    text = "All real [s:s1:c1]."
    assert strip_hallucinated(text, []) == text


# -- end-to-end with EchoLLM ----------------------------------------------- #

@pytest.fixture
def stores_and_notebook():
    """Build an end-to-end stack: source store + notebook store + chunked source."""
    sources = SqliteStore()
    notebooks = NotebookStore()
    embedder = DeterministicEmbedder(dim=32)
    chunker = Chunker()

    parsed = parse_blob(
        b"AMD reported strong Q1 earnings with revenue up 32 percent. "
        b"Coherence across the five layers held at 100 throughout the cycle. "
        b"Oracle committed to a 50,000-GPU supercluster.",
        ContentHint(filename="amd.txt"),
    )
    source, chunks = chunker.chunk(parsed)
    vectors = embedder.embed_batch([c.text for c in chunks])
    sources.save(source, [ChunkWithVector(chunk=c, vector=v) for c, v in zip(chunks, vectors)])

    nb = notebooks.create(Notebook(title="AMD Q1"))
    notebooks.attach_source(nb.id, source.id)
    return sources, notebooks, embedder, nb, source, chunks


def test_generate_returns_valid_citations_when_llm_emits_real_chunks(stores_and_notebook):
    sources, notebooks, embedder, nb, source, chunks = stores_and_notebook
    # EchoLLM cites the first retrieved chunk — valid.
    llm = EchoLLM(cite_chunks=[(source.id, chunks[0].id)])
    gen = CitedGenerator(llm, Retriever(sources, notebooks, embedder))
    answer = gen.generate(nb.id, "What's AMD's revenue growth?")
    assert len(answer.citations) == 1
    assert answer.hallucinated == []
    assert answer.citations[0].chunk_id == chunks[0].id


def test_generate_strips_hallucinated_citations(stores_and_notebook):
    sources, notebooks, embedder, nb, source, chunks = stores_and_notebook
    llm = EchoLLM(
        cite_chunks=[(source.id, chunks[0].id), ("ghost", "fake-chunk")]
    )
    gen = CitedGenerator(llm, Retriever(sources, notebooks, embedder))
    answer = gen.generate(nb.id, "anything")
    assert len(answer.citations) == 1
    assert len(answer.hallucinated) == 1
    assert "[s:ghost:fake-chunk]" not in answer.answer
    assert f"[s:{source.id}:{chunks[0].id}]" in answer.answer


def test_generate_handles_empty_notebook_gracefully():
    sources = SqliteStore()
    notebooks = NotebookStore()
    embedder = DeterministicEmbedder(dim=32)
    nb = notebooks.create(Notebook(title="empty"))
    gen = CitedGenerator(EchoLLM(), Retriever(sources, notebooks, embedder))
    answer = gen.generate(nb.id, "anything")
    assert answer.citations == []
    assert "No sources are attached" in answer.answer


def test_generate_raises_lookuperror_on_missing_notebook():
    sources = SqliteStore()
    notebooks = NotebookStore()
    embedder = DeterministicEmbedder(dim=32)
    gen = CitedGenerator(EchoLLM(), Retriever(sources, notebooks, embedder))
    with pytest.raises(LookupError):
        gen.generate("does-not-exist", "anything")


def test_retrieval_p95_under_threshold(stores_and_notebook):
    """DLOG-spec: retrieval p95 < 200ms on a notebook of 50 sources.
    With our small fixture (1 source, ~1 chunk) we just check the mechanism
    populates `elapsed_ms` and is well under threshold.
    """
    sources, notebooks, embedder, nb, _, _ = stores_and_notebook
    gen = CitedGenerator(EchoLLM(), Retriever(sources, notebooks, embedder))
    answer = gen.generate(nb.id, "anything")
    assert answer.retrieval.elapsed_ms >= 0
    assert answer.retrieval.elapsed_ms < 200
