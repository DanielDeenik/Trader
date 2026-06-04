"""
Agent Pipeline API Routes.

Exposes the agent orchestration layer to the frontend:
- Pipeline status and health
- Agent lifecycle control
- Pipeline flow graph for visualization
- Event history
"""

from fastapi import APIRouter, HTTPException

from ...agents.setup import get_registry, get_context_layer, get_knowledge_store
from ...agents.events import EventType

router = APIRouter(prefix="/agents", tags=["agents"])


def _require_registry():
    registry = get_registry()
    if not registry:
        raise HTTPException(503, "Agent pipeline not initialized")
    return registry


@router.get("/status")
async def get_pipeline_status():
    """Get status of all agents and event bus."""
    registry = _require_registry()
    return registry.get_all_status()


@router.get("/flow")
async def get_pipeline_flow():
    """Get pipeline as directed graph (nodes + edges) for visualization."""
    registry = _require_registry()
    return registry.get_pipeline_flow()


@router.get("/health")
async def get_pipeline_health():
    """Get full pipeline health report from Supervisor."""
    registry = _require_registry()
    supervisor = registry.get_agent("supervisor")
    if supervisor and hasattr(supervisor, "get_pipeline_health"):
        return supervisor.get_pipeline_health()
    return registry.get_all_status()


@router.get("/context")
async def get_pipeline_context():
    """
    Get real-time pipeline context — the pressure metrics that agents
    use to adapt their behavior dynamically.

    Returns signal velocity, divergence pressure, lifecycle distribution,
    HITL backlog, portfolio heat, bottleneck detection, and hot symbols.
    """
    ctx = get_context_layer()
    if not ctx:
        raise HTTPException(503, "Context layer not initialized")
    pipeline = ctx.get_context()
    return pipeline.to_dict()


@router.get("/knowledge")
async def get_knowledge_summary():
    """
    Get knowledge store summary — entity links, narrative threads,
    and research queue statistics.
    """
    store = get_knowledge_store()
    if not store:
        raise HTTPException(503, "Knowledge store not initialized")
    return store.get_knowledge_summary()


@router.get("/knowledge/links/{symbol}")
async def get_entity_links(symbol: str):
    """Get all entity links for a symbol."""
    store = get_knowledge_store()
    if not store:
        raise HTTPException(503, "Knowledge store not initialized")
    return store.get_entity_links(symbol.upper())


@router.get("/knowledge/threads")
async def get_narrative_threads(stage: str = None):
    """Get active narrative threads, optionally filtered by lifecycle stage."""
    store = get_knowledge_store()
    if not store:
        raise HTTPException(503, "Knowledge store not initialized")
    stages = [stage] if stage else None
    return store.get_active_threads(min_signals=1, stages=stages)


@router.get("/knowledge/queue")
async def get_research_queue():
    """Get research queue statistics and top pending hypotheses."""
    store = get_knowledge_store()
    if not store:
        raise HTTPException(503, "Knowledge store not initialized")
    return store.get_queue_stats()


@router.get("/events/history")
async def get_event_history(event_type: str = None, limit: int = 50):
    """Get recent event history."""
    registry = _require_registry()
    et = None
    if event_type:
        try:
            et = EventType(event_type)
        except ValueError:
            raise HTTPException(400, f"Unknown event type: {event_type}")

    events = registry.event_bus.get_history(event_type=et, limit=limit)
    return [
        {
            "id": e.event_id,
            "type": e.type.value,
            "source_agent": e.source_agent,
            "payload": e.payload,
            "timestamp": e.timestamp.isoformat(),
        }
        for e in events
    ]


@router.get("/{agent_name}")
async def get_agent_status(agent_name: str):
    """Get status of a specific agent."""
    registry = _require_registry()
    agent = registry.get_agent(agent_name)
    if not agent:
        raise HTTPException(404, f"Agent '{agent_name}' not found")
    return agent.get_status()


@router.post("/{agent_name}/restart")
async def restart_agent(agent_name: str):
    """Restart a specific agent."""
    registry = _require_registry()
    agent = registry.get_agent(agent_name)
    if not agent:
        raise HTTPException(404, f"Agent '{agent_name}' not found")

    await agent.stop()
    await agent.start()
    return {"status": "restarted", "agent": agent.get_status()}
