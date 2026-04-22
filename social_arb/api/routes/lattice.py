"""Lattice graph API — HITL graph visualization of symbol research."""

import json
from typing import Optional
from fastapi import APIRouter, HTTPException
from social_arb.api.deps import get_db_path
from social_arb.api.schemas import (
    LatticeGraphResponse,
    LatticeNodeResponse,
    LatticeEdgeResponse,
    LatticeNodeCreate,
    LatticeEdgeCreate,
)
from social_arb.db.store import (
    query_signals,
    query_mosaics,
    query_theses,
    query_decisions,
    query_positions,
    insert_lattice_node,
    insert_lattice_edge,
    query_lattice_nodes,
    query_lattice_edges,
)

router = APIRouter(prefix="/api/v1/lattice", tags=["lattice"])


def _node_id(entity_type: str, entity_id: int) -> str:
    """Generate node ID from entity type and ID."""
    return f"{entity_type}-{entity_id}"


def _edge_id(source: str, target: str, label: str = "") -> str:
    """Generate edge ID from source, target, and optional label."""
    parts = [source.replace("-", "_"), target.replace("-", "_")]
    if label:
        parts.append(label.replace(" ", "_"))
    return "e_" + "_".join(parts)


@router.get("/{symbol}", response_model=LatticeGraphResponse)
def get_lattice(symbol: str):
    """
    GET /api/v1/lattice/{symbol}

    Build a graph from all related entities (signals, mosaics, theses, decisions, positions).
    Includes custom HITL nodes/edges from lattice_nodes and lattice_edges tables.

    Returns:
        LatticeGraphResponse with nodes, edges, and stats
    """
    db_path = get_db_path()

    nodes: dict[str, LatticeNodeResponse] = {}
    edges: list[LatticeEdgeResponse] = []
    node_counts: dict[str, int] = {}

    # 1. Add instrument root node
    instrument_node_id = _node_id("instrument", symbol)
    nodes[instrument_node_id] = LatticeNodeResponse(
        id=instrument_node_id,
        type="instrument",
        label=symbol,
        data={"symbol": symbol}
    )
    node_counts["instrument"] = 1

    # 2. Add signals as nodes
    signals = query_signals(symbol=symbol, limit=100, db_path=db_path)
    for sig in signals:
        node_id = _node_id("signal", sig["id"])
        nodes[node_id] = LatticeNodeResponse(
            id=node_id,
            type="signal",
            label=f"{sig.get('source', 'unknown')}: {sig.get('direction', 'neutral')}",
            data={
                "signal_id": sig["id"],
                "source": sig.get("source"),
                "direction": sig.get("direction"),
                "strength": sig.get("strength"),
                "confidence": sig.get("confidence"),
            }
        )
        # Edge: instrument -> signal
        edge_id = _edge_id(instrument_node_id, node_id, "contains")
        edges.append(LatticeEdgeResponse(
            id=edge_id,
            source=instrument_node_id,
            target=node_id,
            label="contains"
        ))
    node_counts["signal"] = len(signals)

    # 3. Add mosaics as nodes
    mosaics = query_mosaics(symbol=symbol, limit=100, db_path=db_path)
    for mosaic in mosaics:
        node_id = _node_id("mosaic", mosaic["id"])
        nodes[node_id] = LatticeNodeResponse(
            id=node_id,
            type="mosaic",
            label=f"Mosaic ({mosaic.get('coherence_score', 0):.2f})",
            data={
                "mosaic_id": mosaic["id"],
                "domain": mosaic.get("domain"),
                "coherence_score": mosaic.get("coherence_score"),
                "divergence_strength": mosaic.get("divergence_strength"),
                "narrative": mosaic.get("narrative"),
                "action": mosaic.get("action"),
            }
        )
        # Edge: instrument -> mosaic
        edge_id = _edge_id(instrument_node_id, node_id, "builds")
        edges.append(LatticeEdgeResponse(
            id=edge_id,
            source=instrument_node_id,
            target=node_id,
            label="builds"
        ))

        # Edges: signals -> mosaic (fragments)
        # Parse fragments_json if present
        if mosaic.get("fragments_json"):
            try:
                fragments = json.loads(mosaic["fragments_json"])
                if isinstance(fragments, list):
                    for frag_id in fragments[:5]:  # Limit to 5 fragments per mosaic for clarity
                        sig_node_id = _node_id("signal", frag_id)
                        if sig_node_id in nodes:
                            edge_id = _edge_id(sig_node_id, node_id, "fragment")
                            edges.append(LatticeEdgeResponse(
                                id=edge_id,
                                source=sig_node_id,
                                target=node_id,
                                label="fragment"
                            ))
            except (json.JSONDecodeError, TypeError):
                pass

    node_counts["mosaic"] = len(mosaics)

    # 4. Add theses as nodes
    theses = query_theses(symbol=symbol, limit=100, db_path=db_path)
    for thesis in theses:
        node_id = _node_id("thesis", thesis["id"])
        nodes[node_id] = LatticeNodeResponse(
            id=node_id,
            type="thesis",
            label=f"Thesis: {thesis.get('status', 'pending')}",
            data={
                "thesis_id": thesis["id"],
                "domain": thesis.get("domain"),
                "status": thesis.get("status"),
                "roi_bear": thesis.get("roi_bear"),
                "roi_base": thesis.get("roi_base"),
                "roi_bull": thesis.get("roi_bull"),
                "kelly_fraction": thesis.get("kelly_fraction"),
                "lifecycle_stage": thesis.get("lifecycle_stage"),
            }
        )
        # Edge: mosaic -> thesis (forged from)
        if thesis.get("mosaic_id"):
            mosaic_node_id = _node_id("mosaic", thesis["mosaic_id"])
            if mosaic_node_id in nodes:
                edge_id = _edge_id(mosaic_node_id, node_id, "forged")
                edges.append(LatticeEdgeResponse(
                    id=edge_id,
                    source=mosaic_node_id,
                    target=node_id,
                    label="forged"
                ))

    node_counts["thesis"] = len(theses)

    # 5. Add decisions as nodes
    decisions = query_decisions(symbol=symbol, limit=100, db_path=db_path)
    for decision in decisions:
        node_id = _node_id("decision", decision["id"])
        nodes[node_id] = LatticeNodeResponse(
            id=node_id,
            type="decision",
            label=f"Decision: {decision.get('decision', 'pending')}",
            data={
                "decision_id": decision["id"],
                "gate": decision.get("gate"),
                "decision": decision.get("decision"),
                "confidence": decision.get("confidence"),
                "trust_level": decision.get("trust_level"),
                "rationale": decision.get("rationale"),
            }
        )
        # Edge: thesis -> decision
        if decision.get("thesis_id"):
            thesis_node_id = _node_id("thesis", decision["thesis_id"])
            if thesis_node_id in nodes:
                edge_id = _edge_id(thesis_node_id, node_id, "decides")
                edges.append(LatticeEdgeResponse(
                    id=edge_id,
                    source=thesis_node_id,
                    target=node_id,
                    label="decides"
                ))

    node_counts["decision"] = len(decisions)

    # 6. Add positions as nodes
    positions = query_positions(limit=100, db_path=db_path)
    positions = [p for p in positions if p.get("symbol") == symbol]
    for position in positions:
        node_id = _node_id("position", position["id"])
        nodes[node_id] = LatticeNodeResponse(
            id=node_id,
            type="position",
            label=f"{position.get('direction', 'long').capitalize()} {position.get('allocation_pct', 0):.1f}%",
            data={
                "position_id": position["id"],
                "direction": position.get("direction"),
                "allocation_pct": position.get("allocation_pct"),
                "conviction": position.get("conviction"),
                "status": position.get("status"),
                "entry_price": position.get("entry_price"),
                "entry_date": position.get("entry_date"),
            }
        )
        # Edge: thesis -> position
        if position.get("thesis_id"):
            thesis_node_id = _node_id("thesis", position["thesis_id"])
            if thesis_node_id in nodes:
                edge_id = _edge_id(thesis_node_id, node_id, "executes")
                edges.append(LatticeEdgeResponse(
                    id=edge_id,
                    source=thesis_node_id,
                    target=node_id,
                    label="executes"
                ))

    node_counts["position"] = len(positions)

    # 7. Add custom HITL nodes and edges
    custom_nodes = query_lattice_nodes(symbol=symbol, db_path=db_path)
    for custom in custom_nodes:
        nodes[custom["node_id"]] = LatticeNodeResponse(
            id=custom["node_id"],
            type="custom",
            label=custom["label"],
            data=json.loads(custom["data_json"]) if custom.get("data_json") else None
        )
    node_counts["custom"] = len(custom_nodes)

    custom_edges = query_lattice_edges(symbol=symbol, db_path=db_path)
    for custom in custom_edges:
        edges.append(LatticeEdgeResponse(
            id=custom["edge_id"],
            source=custom["source_node_id"],
            target=custom["target_node_id"],
            label=custom.get("label")
        ))

    return LatticeGraphResponse(
        symbol=symbol,
        nodes=list(nodes.values()),
        edges=edges,
        stats=node_counts
    )


@router.post("/{symbol}/node", response_model=LatticeNodeResponse)
def add_custom_node(symbol: str, req: LatticeNodeCreate):
    """
    POST /api/v1/lattice/{symbol}/node

    Add a custom HITL node (research note, external insight, custom connection).
    Optionally connect to existing nodes.

    Body:
        {
            "type": "custom",
            "label": "My research note",
            "data": {"content": "Found competitor filing..."},
            "connect_to": ["mosaic-45", "signal-123"]
        }

    Returns:
        Created node with its connections
    """
    db_path = get_db_path()

    # Generate node ID
    import time
    node_id = f"custom-{int(time.time() * 1000)}"

    # Insert custom node
    data_json = json.dumps(req.data) if req.data else None
    insert_lattice_node(
        symbol=symbol,
        node_id=node_id,
        node_type=req.type,
        label=req.label,
        data_json=data_json,
        db_path=db_path
    )

    # Create edges to target nodes if specified
    if req.connect_to:
        for target_node_id in req.connect_to:
            edge_id = _edge_id(node_id, target_node_id, "custom_link")
            try:
                insert_lattice_edge(
                    symbol=symbol,
                    edge_id=edge_id,
                    source_node_id=node_id,
                    target_node_id=target_node_id,
                    label="custom_link",
                    db_path=db_path
                )
            except Exception:
                # Silently skip invalid target nodes
                pass

    return LatticeNodeResponse(
        id=node_id,
        type=req.type,
        label=req.label,
        data=req.data
    )


@router.post("/{symbol}/edge", response_model=LatticeEdgeResponse)
def add_custom_edge(symbol: str, req: LatticeEdgeCreate):
    """
    POST /api/v1/lattice/{symbol}/edge

    Create a custom edge between two existing nodes.

    Body:
        {
            "source": "signal-123",
            "target": "thesis-12",
            "label": "supports"
        }

    Returns:
        Created edge
    """
    db_path = get_db_path()

    # Verify both nodes exist
    all_nodes = query_lattice_nodes(symbol=symbol, db_path=db_path)
    node_ids = {n["node_id"] for n in all_nodes}

    # Check existing nodes from built graph
    signals = query_signals(symbol=symbol, limit=100, db_path=db_path)
    for sig in signals:
        node_ids.add(_node_id("signal", sig["id"]))

    mosaics = query_mosaics(symbol=symbol, limit=100, db_path=db_path)
    for mosaic in mosaics:
        node_ids.add(_node_id("mosaic", mosaic["id"]))

    theses = query_theses(symbol=symbol, limit=100, db_path=db_path)
    for thesis in theses:
        node_ids.add(_node_id("thesis", thesis["id"]))

    decisions = query_decisions(symbol=symbol, limit=100, db_path=db_path)
    for decision in decisions:
        node_ids.add(_node_id("decision", decision["id"]))

    positions = query_positions(limit=100, db_path=db_path)
    for position in positions:
        if position.get("symbol") == symbol:
            node_ids.add(_node_id("position", position["id"]))

    # Validate nodes exist
    if req.source not in node_ids:
        raise HTTPException(status_code=400, detail=f"Source node not found: {req.source}")
    if req.target not in node_ids:
        raise HTTPException(status_code=400, detail=f"Target node not found: {req.target}")

    # Generate edge ID and insert
    edge_id = _edge_id(req.source, req.target, req.label or "links")
    insert_lattice_edge(
        symbol=symbol,
        edge_id=edge_id,
        source_node_id=req.source,
        target_node_id=req.target,
        label=req.label,
        db_path=db_path
    )

    return LatticeEdgeResponse(
        id=edge_id,
        source=req.source,
        target=req.target,
        label=req.label
    )
