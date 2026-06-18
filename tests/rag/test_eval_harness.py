"""Eval harness (NB-003): 5 known prompts × known notebooks.

Acceptance criterion: zero hallucinated citations across the eval set.
Uses EchoLLM so the test is deterministic. Real-LLM evals run as a
separate (manual) job because they cost tokens and have non-zero
flakiness.
"""
from __future__ import annotations

import pytest

from social_arb.notebooks.chunker import Chunker
from social_arb.notebooks.embedder import DeterministicEmbedder
from social_arb.notebooks.notebook_models import Notebook
from social_arb.notebooks.notebook_store import NotebookStore
from social_arb.notebooks.parsers import ContentHint, parse_blob
from social_arb.rag import CitedGenerator, EchoLLM, Retriever
from social_arb.sources import ChunkWithVector, SqliteStore


@pytest.fixture(scope="module")
def loaded_stack():
    """Build a small fixture corpus: 5 notebooks with one source each."""
    sources = SqliteStore()
    notebooks = NotebookStore()
    embedder = DeterministicEmbedder(dim=32)
    chunker = Chunker()

    fixtures = [
        ("AMD Q1 thesis",
         "AMD revenue +32% YoY. MI400 inflection H2 2026. Oracle 50K-GPU commitment."),
        ("SQ thesis",
         "Block GOLFTEC 200-loc live. Cash App BTC ecosystem revenue $1.7B Q1. Stock $66."),
        ("PLTR thesis",
         "Burry 2027 $50P. Trump endorsement Apr 10. MS strong setup. Coh 85 binary."),
        ("MSFT thesis",
         "Azure capacity tight. Copilot enterprise adoption beating estimates. Coh 86."),
        ("BTC thesis",
         "Lifecycle confirmed. Coh 98. Kelly 0.10. Lower urgency than AMD."),
    ]

    fixture_data: list[tuple[str, str, list]] = []  # (notebook_id, source_id, chunks)
    for title, body in fixtures:
        parsed = parse_blob(body.encode("utf-8"), ContentHint(filename=f"{title}.txt"))
        source, chunks = chunker.chunk(parsed)
        vectors = embedder.embed_batch([c.text for c in chunks])
        sources.save(source, [ChunkWithVector(chunk=c, vector=v) for c, v in zip(chunks, vectors)])
        nb = notebooks.create(Notebook(title=title))
        notebooks.attach_source(nb.id, source.id)
        fixture_data.append((nb.id, source.id, chunks))

    return sources, notebooks, embedder, fixture_data


PROMPTS = [
    "What is the catalyst for this thesis?",
    "How coherent are the layers?",
    "What is the lifecycle stage?",
    "What's the recommended action?",
    "What are the main risks?",
]


def _gen_with_only_real_chunks(sources, notebooks, embedder, source_id, chunks_for_source):
    """Make an EchoLLM that ALWAYS cites a real chunk in `chunks_for_source`."""
    real_chunk_id = chunks_for_source[0].id
    return CitedGenerator(
        EchoLLM(cite_chunks=[(source_id, real_chunk_id)]),
        Retriever(sources, notebooks, embedder),
    )


def test_eval_harness_zero_hallucinations(loaded_stack):
    """Across 5 notebooks × 5 prompts (25 generations), hallucinated count must be 0."""
    sources, notebooks, embedder, fixture_data = loaded_stack
    total = 0
    hallucinated = 0
    for nb_id, source_id, chunks_for_source in fixture_data:
        gen = _gen_with_only_real_chunks(sources, notebooks, embedder, source_id, chunks_for_source)
        for prompt in PROMPTS:
            answer = gen.generate(nb_id, prompt)
            total += 1
            hallucinated += len(answer.hallucinated)
            assert len(answer.citations) >= 1, f"no valid citations for {prompt!r} on {nb_id}"
    assert total == 25
    assert hallucinated == 0, f"expected 0 hallucinations across {total} generations, got {hallucinated}"


def test_eval_harness_detects_hallucinations_when_planted(loaded_stack):
    """Negative control: a deliberately-hallucinating LLM must be caught."""
    sources, notebooks, embedder, fixture_data = loaded_stack
    nb_id, source_id, _ = fixture_data[0]
    bad_llm = EchoLLM(cite_chunks=[("ghost-source", "ghost-chunk")])
    gen = CitedGenerator(bad_llm, Retriever(sources, notebooks, embedder))
    answer = gen.generate(nb_id, PROMPTS[0])
    assert len(answer.hallucinated) == 1
    assert len(answer.citations) == 0
