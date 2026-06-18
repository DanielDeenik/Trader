"""Tests for the Overview generator."""
from __future__ import annotations

import pytest

from social_arb.notebooks.chunker import Chunker
from social_arb.notebooks.embedder import DeterministicEmbedder
from social_arb.notebooks.notebook_models import Notebook
from social_arb.notebooks.notebook_store import NotebookStore
from social_arb.notebooks.parsers import ContentHint, parse_blob
from social_arb.rag import EchoLLM, Retriever
from social_arb.sources import ChunkWithVector, SqliteStore
from social_arb.studio.overview import OverviewGenerator, parse_sections


@pytest.fixture
def populated_stack():
    sources = SqliteStore()
    notebooks = NotebookStore()
    embedder = DeterministicEmbedder(dim=32)
    chunker = Chunker()

    parsed = parse_blob(
        b"AMD reported strong Q1 earnings. Revenue rose 32 percent. "
        b"Coherence across the five layers held at 100. "
        b"Oracle 50K-GPU commitment is a key catalyst. "
        b"MI400 inflection in H2 2026.",
        ContentHint(filename="amd.txt"),
    )
    source, chunks = chunker.chunk(parsed)
    vectors = embedder.embed_batch([c.text for c in chunks])
    sources.save(source, [ChunkWithVector(chunk=c, vector=v) for c, v in zip(chunks, vectors)])
    nb = notebooks.create(Notebook(title="AMD Q1"))
    notebooks.attach_source(nb.id, source.id)
    return sources, notebooks, embedder, nb, source, chunks


def test_overview_generates_content_with_citations(populated_stack):
    sources, notebooks, embedder, nb, source, chunks = populated_stack
    template = (
        "## Thesis\nAMD has structural upside [s:{sid}:{cid}].\n\n"
        "## Catalysts\nQ1 earnings May 5 [s:{sid}:{cid}].\n\n"
        "## Risks\nHelios execution delay [s:{sid}:{cid}].\n\n"
        "## Recent signals\nReddit chatter +180% [s:{sid}:{cid}]."
    ).format(sid=source.id, cid=chunks[0].id).replace("{chunk_count}", "")

    llm = EchoLLM(
        answer_template=template,
        cite_chunks=[],  # citations already in the template
    )

    gen = OverviewGenerator()
    content, citations = gen.build(
        nb.id,
        {"max_chunks": 8},
        retriever=Retriever(sources, notebooks, embedder),
        llm=llm,
    )

    assert "thesis" in content["sections"]
    assert "catalysts" in content["sections"]
    assert "risks" in content["sections"]
    assert "recent_signals" in content["sections"]
    assert content["model"] == "echo-test-v1"
    assert len(citations) == 4
    assert all(c.source_id == source.id for c in citations)


def test_parse_sections_handles_well_formed_markdown():
    md = (
        "## Thesis\nA short claim.\n\n"
        "## Catalysts\nB.\n\n"
        "## Risks\nC.\n\n"
        "## Recent signals\nD."
    )
    sections = parse_sections(md)
    assert sections["thesis"] == "A short claim."
    assert sections["catalysts"] == "B."
    assert sections["risks"] == "C."
    assert sections["recent_signals"] == "D."


def test_parse_sections_returns_empty_on_unrecognized_format():
    assert parse_sections("Just some prose with no headers") == {}


def test_overview_falls_back_to_full_text_on_unparseable_output(populated_stack):
    sources, notebooks, embedder, nb, source, chunks = populated_stack
    # Template has no section headers — parser should give up gracefully.
    llm = EchoLLM(answer_template="No structure here.")
    gen = OverviewGenerator()
    content, _ = gen.build(
        nb.id,
        {},
        retriever=Retriever(sources, notebooks, embedder),
        llm=llm,
    )
    assert content["sections"] == {"_full": content["markdown"]}
