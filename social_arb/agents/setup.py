"""
Agent Pipeline Setup — Factory function to wire all agents together.

Called from FastAPI lifespan to initialize the full cognitive pipeline.
Includes:
  - ContextLayer for dynamic, context-aware behavior
  - KnowledgeStore for persistent inferred connections
  - ResearchOrchestrator for continuous hypothesis-driven research
"""

import logging
import os
from typing import Optional

from .context import ContextLayer
from .events import EventBus
from .knowledge import KnowledgeStore
from .registry import AgentRegistry
from .researcher import ResearchOrchestrator
from .sentinel import Sentinel
from .assembler import Assembler
from .strategist import StrategistAgent as Strategist
from .gatekeeper import GatekeeperAgent as Gatekeeper
from .executor import ExecutorAgent as Executor
from .supervisor import Supervisor

logger = logging.getLogger(__name__)

# Module-level references so API routes can access them
_registry: Optional[AgentRegistry] = None
_context_layer: Optional[ContextLayer] = None
_knowledge_store: Optional[KnowledgeStore] = None


def get_registry() -> Optional[AgentRegistry]:
    """Get the global agent registry (set during lifespan)."""
    return _registry


def get_context_layer() -> Optional[ContextLayer]:
    """Get the global context layer (set during lifespan)."""
    return _context_layer


def get_knowledge_store() -> Optional[KnowledgeStore]:
    """Get the global knowledge store (set during lifespan)."""
    return _knowledge_store


async def setup_agents(db_path: str) -> AgentRegistry:
    """
    Create and wire all pipeline agents with shared services.

    Three shared services:
      1. ContextLayer — real-time pipeline pressure metrics
      2. KnowledgeStore — persistent entity links, narrative threads, research queue
      3. ResearchOrchestrator — generates and investigates hypotheses

    Every agent gets all three. Between batch cycles, agents enter
    research mode: generating hypotheses from what they found, then
    claiming and investigating hypotheses from the queue.

    The knowledge accumulated feeds back into the next pipeline cycle
    through the ContextLayer (which reads entity_links and narrative_threads)
    and through agents that check the knowledge store before processing.

    Agent start order follows the cognitive pipeline:
      Sentinel (L0) → Assembler (L1) → Strategist (L2)
      → Gatekeeper (L3) → Executor (L4) → Supervisor (meta)

    Returns the registry. Call registry.start_all() to activate.
    """
    global _registry, _context_layer, _knowledge_store

    event_bus = EventBus()
    registry = AgentRegistry(event_bus)

    # ── Shared Services ───────────────────────────────────────

    # Context: real-time pipeline pressure (caches 10s)
    context = ContextLayer(db_path=db_path, ttl_seconds=10.0)
    _context_layer = context

    # Knowledge: persistent inferred connections (creates tables on init)
    knowledge = KnowledgeStore(db_path=db_path)
    _knowledge_store = knowledge

    # Research: hypothesis generation and investigation
    researcher = ResearchOrchestrator(db_path=db_path, knowledge=knowledge)

    # ── Agents ────────────────────────────────────────────────

    # L0: Peripheral Vision — collection orchestration
    sentinel = Sentinel(
        event_bus=event_bus,
        db_path=db_path,
        config={
            "stale_threshold_hours": float(
                os.environ.get("AGENT_STALE_HOURS", "4")
            ),
            "tick_interval": 60.0,
            "sources": [
                "yfinance", "reddit", "sec_edgar", "google_trends",
                "github", "coingecko", "defillama",
            ],
        },
    )
    sentinel.ctx = context
    sentinel.knowledge = knowledge
    sentinel.researcher = researcher
    registry.register(sentinel)

    # L1→L2: Pattern Recognition — signal→mosaic pipeline
    assembler = Assembler(
        event_bus=event_bus,
        db_path=db_path,
        config={
            "min_signals_for_analysis": 3,
            "tick_interval": 0,  # Event-driven only, no polling
        },
    )
    assembler.ctx = context
    assembler.knowledge = knowledge
    assembler.researcher = researcher
    registry.register(assembler)

    # L2→L3: Divergence + Conviction — thesis generation
    strategist = Strategist(
        name="strategist",
        event_bus=event_bus,
        db_path=db_path,
        config={
            "min_coherence": 0.5,
            "min_kelly": 0.02,
            "tick_interval": 0,
        },
    )
    strategist.ctx = context
    strategist.knowledge = knowledge
    strategist.researcher = researcher
    registry.register(strategist)

    # L3→L4: HITL Queue — review management
    gatekeeper = Gatekeeper(
        name="gatekeeper",
        event_bus=event_bus,
        db_path=db_path,
        config={
            "auto_promote_threshold": 15.0,
            "review_poll_interval": 30.0,
            "tick_interval": 30.0,
        },
    )
    gatekeeper.ctx = context
    gatekeeper.knowledge = knowledge
    gatekeeper.researcher = researcher
    registry.register(gatekeeper)

    # L4→L5: Execution — position lifecycle
    executor = Executor(
        name="executor",
        event_bus=event_bus,
        db_path=db_path,
        config={
            "max_positions": 10,
            "max_allocation_pct": 5.0,
            "tick_interval": 120.0,
        },
    )
    executor.ctx = context
    registry.register(executor)

    # Meta: Supervisor — pipeline health + knowledge maintenance
    supervisor = Supervisor(
        event_bus=event_bus,
        db_path=db_path,
        registry=registry,
        config={
            "health_check_interval": 120.0,
            "stuck_threshold_hours": 12,
            "max_hitl_backlog": 20,
            "tick_interval": 120.0,
        },
    )
    supervisor.ctx = context
    supervisor.knowledge = knowledge
    registry.register(supervisor)

    _registry = registry
    logger.info(
        "Agent pipeline wired: 6 agents + ContextLayer + KnowledgeStore + ResearchOrchestrator"
    )
    return registry


async def teardown_agents():
    """Stop all agents and clean up."""
    global _registry, _context_layer, _knowledge_store
    if _registry:
        await _registry.stop_all()
        _registry = None
    _context_layer = None
    _knowledge_store = None
