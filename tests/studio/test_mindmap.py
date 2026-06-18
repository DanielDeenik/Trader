"""Tests for the Mind Map generator + JSON parsing helpers."""
from __future__ import annotations

import json

import pytest

from social_arb.notebooks.chunker import Chunker
from social_arb.notebooks.embedder import DeterministicEmbedder
from social_arb.notebooks.notebook_models import Notebook
from social_arb.notebooks.notebook_store import NotebookStore
from social_arb.notebooks.parsers import ContentHint, parse_blob
from social_arb.rag import EchoLLM, Retriever
from social_arb.sources import ChunkWithVector, SqliteStore
from social_arb.studio.mindmap import (
    MindMapGenerator,
    extract_json,
    pick_focal,
    sanitize_graph,
)


# -- helper unit tests ------------------------------------------------------ #

def test_extract_json_direct():
    assert extract_json('{"a": 1}') == {"a": 1}


def test_extract_json_strips_markdown_fences():
    assert extract_json('```json\n{"a": 1}\n```') == {"a": 1}


def test_extract_json_greedy_match_with_prose():
    text = 'Here is the graph: {"nodes": [], "edges": []} (that\'s all).'
    assert extract_json(text) == {"nodes": [], "edges": []}


def test_extract_json_raises_when_no_json():
    with pytest.raises(ValueError):
        extract_json("no json here at all")


def test_sanitize_graph_drops_malformed():
    raw = {
        "nodes": [
            {"data": {"id": "AMD", "label": "AMD", "kind": "ticker"}},
            {"data": {"label": "no id here"}},          # dropped (no id)
            "not a dict",                                 # dropped
            {"data": {"id": "Bob", "kind": "alien"}},     # kept, kind → topic
        ],
        "edges": [
            {"data": {"source": "AMD", "target": "Bob", "label": "x", "etype": "thesis"}},
            {"data": {"source": "AMD", "target": "ghost"}},  # dropped (target not a node)
            {"data": {"source": "AMD"}},                      # dropped (missing target)
        ],
    }
    graph = sanitize_graph(raw)
    assert len(graph["nodes"]) == 2
    assert graph["nodes"][0]["data"]["id"] == "AMD"
    assert graph["nodes"][1]["data"]["kind"] == "topic"  # normalized
    assert len(graph["edges"]) == 1


def test_sanitize_graph_normalizes_etype():
    raw = {
        "nodes": [{"data": {"id": "a"}}, {"data": {"id": "b"}}],
        "edges": [{"data": {"source": "a", "target": "b", "etype": "unknown"}}],
    }
    assert sanitize_graph(raw)["edges"][0]["data"]["etype"] == "derived"


def test_pick_focal_prefers_ticker():
    nodes = [
        {"data": {"id": "topic1", "kind": "topic"}},
        {"data": {"id": "AMD", "kind": "ticker"}},
        {"data": {"id": "NVDA", "kind": "ticker"}},
    ]
    assert pick_focal(nodes) == "AMD"


def test_pick_focal_falls_back_to_first_node_when_no_ticker():
    nodes = [
        {"data": {"id": "Semi", "kind": "sector"}},
        {"data": {"id": "AI", "kind": "topic"}},
    ]
    assert pick_focal(nodes) == "Semi"


def test_pick_focal_returns_none_for_empty():
    assert pick_focal([]) is None


# -- end-to-end with EchoLLM ----------------------------------------------- #

@pytest.fixture
def populated_stack():
    sources = SqliteStore()
    notebooks = NotebookStore()
    embedder = DeterministicEmbedder(dim=32)
    chunker = Chunker()

    parsed = parse_blob(
        b"AMD competes with NVDA in AI compute. Lisa Su is AMD CEO. Oracle 50K-GPU commitment.",
        ContentHint(filename="amd.txt"),
    )
    source, chunks = chunker.chunk(parsed)
    vectors = embedder.embed_batch([c.text for c in chunks])
    sources.save(source, [ChunkWithVector(chunk=c, vector=v) for c, v in zip(chunks, vectors)])
    nb = notebooks.create(Notebook(title="AMD KG"))
    notebooks.attach_source(nb.id, source.id)
    return sources, notebooks, embedder, nb, source, chunks


def test_mindmap_extracts_graph_from_llm_json(populated_stack):
    sources, notebooks, embedder, nb, source, chunks = populated_stack
    graph_json = json.dumps({
        "nodes": [
            {"data": {"id": "AMD", "label": "AMD", "kind": "ticker",
                      "cite": f"[s:{source.id}:{chunks[0].id}]"}},
            {"data": {"id": "NVDA", "label": "NVDA", "kind": "ticker"}},
            {"data": {"id": "Lisa Su", "label": "Lisa Su", "kind": "person"}},
        ],
        "edges": [
            {"data": {"source": "AMD", "target": "NVDA",
                      "label": "competitor", "etype": "derived"}},
            {"data": {"source": "AMD", "target": "Lisa Su",
                      "label": "CEO", "etype": "derived"}},
        ],
    })
    llm = EchoLLM(answer_template=graph_json)

    gen = MindMapGenerator()
    content, citations = gen.build(
        nb.id, {},
        retriever=Retriever(sources, notebooks, embedder),
        llm=llm,
    )
    assert len(content["nodes"]) == 3
    assert len(content["edges"]) == 2
    assert content["focal"] == "AMD"
    assert len(citations) == 1   # only the AMD node had a cite
    assert citations[0].source_id == source.id


def test_mindmap_handles_no_sources_attached():
    sources = SqliteStore()
    notebooks = NotebookStore()
    embedder = DeterministicEmbedder(dim=32)
    nb = notebooks.create(Notebook(title="empty"))
    gen = MindMapGenerator()
    content, citations = gen.build(
        nb.id, {},
        retriever=Retriever(sources, notebooks, embedder),
        llm=EchoLLM(),
    )
    assert content["nodes"] == []
    assert content["edges"] == []
    assert content["focal"] is None
    assert citations == []


def test_mindmap_handles_non_json_llm_response(populated_stack):
    sources, notebooks, embedder, nb, _, _ = populated_stack
    llm = EchoLLM(answer_template="I refuse to output JSON, sorry.")
    gen = MindMapGenerator()
    content, citations = gen.build(
        nb.id, {},
        retriever=Retriever(sources, notebooks, embedder),
        llm=llm,
    )
    assert content["nodes"] == []
    assert "non-JSON" in content.get("note", "")
    assert citations == []
