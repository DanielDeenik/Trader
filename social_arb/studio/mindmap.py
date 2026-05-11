"""Mind Map generator (NB-004) — Cytoscape JSON for V5 wireframe.

Asks the LLM to extract entities + relationships from notebook chunks and
return Cytoscape-compatible JSON. The frontend (NB-005 Mind Map viewer +
V5 KG wireframe) consumes this directly.

Output `content`:

    {
      "nodes": [{"data": {"id", "label", "kind"}}, ...],
      "edges": [{"data": {"source", "target", "label", "etype"}}, ...],
      "focal": "AMD",      # auto-picked highest-divergence node (DLOG-10)
      "model": "...",
    }

Citations track which chunks supported which nodes/edges; populated by
parsing inline `[s:src:chunk]` tokens from the LLM's structured output.
"""
from __future__ import annotations

import json
import re
from typing import Any

from social_arb.notebooks.notebook_models import ArtifactKind
from social_arb.rag import (
    Citation,
    LLMMessage,
    LLMProtocol,
    LLMRequest,
    Retriever,
    parse_citations,
)


VALID_NODE_KINDS = {"ticker", "person", "sector", "topic"}
VALID_EDGE_TYPES = {"signal", "derived", "thesis"}

MINDMAP_SYSTEM = """You are a knowledge-graph extractor for the Social Arb platform.
Given research chunks, extract the entities and their relationships as JSON.

Node kinds: ticker | person | sector | topic
Edge types: signal | derived | thesis

Return ONLY a JSON object with this exact shape:
{
  "nodes": [{"data": {"id": "AMD", "label": "AMD", "kind": "ticker", "cite": "[s:src:chunk]"}}, ...],
  "edges": [{"data": {"source": "AMD", "target": "NVDA", "label": "competitor", "etype": "derived", "cite": "[s:src:chunk]"}}, ...]
}

The `cite` field MUST reference a chunk that's in the sources. No prose, no commentary,
no markdown fences — just the JSON object.""".strip()


def _build_user_prompt(chunks_text: str) -> str:
    return (
        "Extract the entity graph from these sources. Cite each node and edge with the "
        "chunk_id that supports it.\n\n"
        f"Sources:\n{chunks_text}"
    )


def _format_chunks(chunks) -> str:
    parts: list[str] = []
    for rc in chunks:
        parts.append(
            f"<source source_id={rc.chunk.source_id!r} chunk_id={rc.chunk.id!r}>\n"
            f"{rc.chunk.text}\n"
            f"</source>"
        )
    return "\n\n".join(parts)


_JSON_BLOCK_RE = re.compile(r"\{.*\}", re.DOTALL)


def extract_json(text: str) -> dict[str, Any]:
    """Pull the JSON object out of an LLM response that may have fences or prose around it."""
    # Try direct parse first — happy path.
    try:
        return json.loads(text)
    except (json.JSONDecodeError, ValueError):
        pass
    # Strip common markdown fences.
    cleaned = text.strip()
    for fence in ("```json", "```JSON", "```"):
        if cleaned.startswith(fence):
            cleaned = cleaned[len(fence):].lstrip()
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3].rstrip()
    try:
        return json.loads(cleaned)
    except (json.JSONDecodeError, ValueError):
        pass
    # Greedy match — outermost {...}.
    match = _JSON_BLOCK_RE.search(text)
    if match:
        return json.loads(match.group(0))
    raise ValueError("no JSON object found in LLM response")


def sanitize_graph(graph: dict[str, Any]) -> dict[str, Any]:
    """Drop malformed nodes/edges; normalize kinds + etypes.

    Cytoscape is picky — keep only entries with a `data.id` (nodes) or
    `data.source`+`data.target` (edges). Unknown kinds default to "topic"
    so the viewer still has something to render.
    """
    raw_nodes = graph.get("nodes") or []
    raw_edges = graph.get("edges") or []

    nodes: list[dict[str, Any]] = []
    node_ids: set[str] = set()
    for n in raw_nodes:
        if not isinstance(n, dict):
            continue
        data = n.get("data") if isinstance(n.get("data"), dict) else n
        node_id = data.get("id")
        if not node_id:
            continue
        kind = (data.get("kind") or "topic").lower()
        if kind not in VALID_NODE_KINDS:
            kind = "topic"
        nodes.append({
            "data": {
                "id": str(node_id),
                "label": str(data.get("label", node_id)),
                "kind": kind,
                "cite": data.get("cite"),
            }
        })
        node_ids.add(str(node_id))

    edges: list[dict[str, Any]] = []
    for e in raw_edges:
        if not isinstance(e, dict):
            continue
        data = e.get("data") if isinstance(e.get("data"), dict) else e
        source = data.get("source")
        target = data.get("target")
        if not source or not target:
            continue
        if str(source) not in node_ids or str(target) not in node_ids:
            continue
        etype = (data.get("etype") or "derived").lower()
        if etype not in VALID_EDGE_TYPES:
            etype = "derived"
        edges.append({
            "data": {
                "source": str(source),
                "target": str(target),
                "label": str(data.get("label", etype)),
                "etype": etype,
                "cite": data.get("cite"),
            }
        })

    return {"nodes": nodes, "edges": edges}


def pick_focal(nodes: list[dict[str, Any]]) -> str | None:
    """DLOG-10: focal node is the first ticker, falling back to the first node."""
    for n in nodes:
        if n["data"].get("kind") == "ticker":
            return n["data"]["id"]
    return nodes[0]["data"]["id"] if nodes else None


class MindMapGenerator:
    kind = ArtifactKind.MIND_MAP
    version = "v0"

    def build(
        self,
        notebook_id: str,
        params: dict[str, Any],
        *,
        retriever: Retriever,
        llm: LLMProtocol,
    ) -> tuple[dict[str, Any], list[Citation]]:
        k = int(params.get("max_chunks", 16))
        max_tokens = int(params.get("max_tokens", 2000))

        # Use a representative query to pull diverse chunks; "entities" is broad
        # enough that embedding similarity returns a good cross-section.
        retrieval = retriever.retrieve(notebook_id, "entities relationships", k=k)

        if not retrieval.chunks:
            return (
                {
                    "nodes": [],
                    "edges": [],
                    "focal": None,
                    "model": "none",
                    "retrieval_ms": retrieval.elapsed_ms,
                    "note": "no sources attached to this notebook yet",
                },
                [],
            )

        response = llm.complete(
            LLMRequest(
                messages=[
                    LLMMessage(role="system", content=MINDMAP_SYSTEM),
                    LLMMessage(role="user", content=_build_user_prompt(_format_chunks(retrieval.chunks))),
                ],
                max_tokens=max_tokens,
            )
        )

        try:
            raw_graph = extract_json(response.text)
        except (ValueError, json.JSONDecodeError):
            # Degraded but non-fatal — return empty graph + diagnostic.
            return (
                {
                    "nodes": [],
                    "edges": [],
                    "focal": None,
                    "model": response.model,
                    "retrieval_ms": retrieval.elapsed_ms,
                    "note": "LLM returned non-JSON; nothing rendered",
                    "raw": response.text[:500],
                },
                [],
            )

        graph = sanitize_graph(raw_graph)
        graph["focal"] = pick_focal(graph["nodes"])
        graph["model"] = response.model
        graph["retrieval_ms"] = retrieval.elapsed_ms

        # Citations harvested from `cite` fields on nodes + edges.
        cite_tokens: list[str] = []
        for item in (*graph["nodes"], *graph["edges"]):
            cite = item["data"].get("cite")
            if cite:
                cite_tokens.append(str(cite))
        all_citations = parse_citations(" ".join(cite_tokens))

        # Validate against retrieved chunk set.
        allowed = {(rc.chunk.source_id, rc.chunk.id) for rc in retrieval.chunks}
        valid = [c for c in all_citations if (c.source_id, c.chunk_id) in allowed]
        hallucinated = [c for c in all_citations if (c.source_id, c.chunk_id) not in allowed]
        graph["hallucinated"] = [c.token for c in hallucinated]

        return graph, valid
