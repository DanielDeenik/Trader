"""
Agent Registry — Lifecycle management for all pipeline agents.

The registry owns the event bus and manages agent start/stop ordering.
Agents are started in pipeline order (L0→L5) and stopped in reverse.
"""

import logging
from typing import Any, Dict, List, Optional

from .base import BaseAgent
from .events import EventBus

logger = logging.getLogger(__name__)


class AgentRegistry:
    """
    Central registry for all pipeline agents.

    Responsibilities:
    - Owns the shared EventBus
    - Manages agent lifecycle (ordered start/stop)
    - Provides status overview for API/dashboard
    """

    def __init__(self, event_bus: Optional[EventBus] = None):
        self.event_bus = event_bus or EventBus()
        self._agents: Dict[str, BaseAgent] = {}
        self._start_order: List[str] = []
        self._running = False

    def register(self, agent: BaseAgent):
        """Register an agent. Call before start_all()."""
        if agent.name in self._agents:
            raise ValueError(f"Agent '{agent.name}' already registered")
        self._agents[agent.name] = agent
        self._start_order.append(agent.name)
        logger.info(f"Registered agent: {agent.name} (layer={agent.layer})")

    async def start_all(self):
        """Start all agents in registration order."""
        logger.info(f"Starting {len(self._agents)} agents...")
        for name in self._start_order:
            agent = self._agents[name]
            try:
                await agent.start()
                logger.info(f"  ✓ {name} started")
            except Exception as e:
                logger.error(f"  ✗ {name} failed to start: {e}")
        self._running = True
        logger.info("All agents started")

    async def stop_all(self):
        """Stop all agents in reverse order."""
        logger.info("Stopping all agents...")
        for name in reversed(self._start_order):
            agent = self._agents[name]
            try:
                await agent.stop()
            except Exception as e:
                logger.error(f"Error stopping {name}: {e}")
        self._running = False
        logger.info("All agents stopped")

    def get_agent(self, name: str) -> Optional[BaseAgent]:
        """Get an agent by name."""
        return self._agents.get(name)

    def get_all_status(self) -> Dict[str, Any]:
        """Get status of all agents + event bus for dashboard."""
        agents = []
        for name in self._start_order:
            agent = self._agents[name]
            agents.append(agent.get_status())

        return {
            "running": self._running,
            "agent_count": len(self._agents),
            "agents": agents,
            "event_bus": self.event_bus.get_stats(),
        }

    def get_pipeline_flow(self) -> Dict[str, Any]:
        """
        Get the pipeline as a directed graph for visualization.
        Returns nodes (agents) and edges (event subscriptions).
        """
        nodes = []
        edges = []

        for i, name in enumerate(self._start_order):
            agent = self._agents[name]
            status = agent.get_status()
            nodes.append({
                "id": name,
                "label": name,
                "layer": agent.layer,
                "state": status["state"],
                "metrics": status["metrics"],
                "position": i,
            })

        # Derive edges from the cognitive flow
        flow = [
            ("sentinel", "assembler", "SIGNALS_COLLECTED"),
            ("assembler", "strategist", "MOSAICS_ASSEMBLED"),
            ("strategist", "gatekeeper", "THESES_FORGED"),
            ("gatekeeper", "executor", "DECISIONS_MADE"),
            ("executor", "sentinel", "POSITIONS_UPDATED"),
            ("assembler", "gatekeeper", "HITL_REQUIRED"),
            ("strategist", "gatekeeper", "HITL_REQUIRED"),
        ]

        for source, target, label in flow:
            if source in self._agents and target in self._agents:
                edges.append({
                    "source": source,
                    "target": target,
                    "label": label,
                })

        return {"nodes": nodes, "edges": edges}
