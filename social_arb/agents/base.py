"""
Base Agent — State machine foundation for all pipeline agents.

Each agent has a simple lifecycle:
  IDLE → WATCHING → ACTING → IDLE
       ↘ ERROR ↗

Agents don't do AI reasoning. They're orchestrators that:
1. Watch for events (triggers from other agents or the scheduler)
2. Decide whether to act based on pipeline state
3. Execute batch jobs via the existing task queue
4. Publish events for downstream agents
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from .events import Event, EventBus, EventType

logger = logging.getLogger(__name__)


class AgentState(str, Enum):
    """Agent lifecycle states."""
    IDLE = "idle"
    WATCHING = "watching"
    ACTING = "acting"
    ERROR = "error"
    STOPPED = "stopped"


@dataclass
class AgentMetrics:
    """Runtime metrics for an agent."""
    actions_taken: int = 0
    actions_failed: int = 0
    events_received: int = 0
    events_published: int = 0
    last_action_at: Optional[datetime] = None
    last_error: Optional[str] = None
    last_error_at: Optional[datetime] = None
    uptime_started: Optional[datetime] = None
    # Dynamic behavior tracking
    last_adapted_params: Optional[Dict[str, Any]] = None


class BaseAgent(ABC):
    """
    Abstract base for all pipeline agents.

    Subclasses implement:
      - subscriptions(): which events this agent reacts to
      - handle_event(): what to do when an event arrives
      - tick(): periodic check (optional, for polling-based logic)

    Context-aware agents also use self.ctx (ContextLayer) to read pipeline
    conditions and adapt their behavior dynamically via adapt_params().
    """

    def __init__(
        self,
        name: str,
        layer: str,
        event_bus: EventBus,
        db_path: str,
        config: Optional[Dict[str, Any]] = None,
    ):
        self.name = name
        self.layer = layer
        self.event_bus = event_bus
        self.db_path = db_path
        self.config = config or {}

        # Context layer — set by setup.py after construction
        self.ctx = None  # type: Optional[Any]  # ContextLayer

        self.state = AgentState.STOPPED
        self.metrics = AgentMetrics()
        self._tick_task: Optional[asyncio.Task] = None
        self._tick_interval: float = self.config.get("tick_interval", 60.0)
        self._base_tick_interval: float = self._tick_interval  # original for adaptation

    # ── Lifecycle ──────────────────────────────────────────────

    async def start(self):
        """Start the agent: subscribe to events, begin tick loop."""
        self.state = AgentState.WATCHING
        self.metrics.uptime_started = datetime.now(timezone.utc)

        # Subscribe to relevant events
        for event_type in self.subscriptions():
            self.event_bus.subscribe(event_type, self._on_event)

        # Start periodic tick if the agent uses it
        if self._tick_interval > 0:
            self._tick_task = asyncio.create_task(self._tick_loop())

        logger.info(f"Agent [{self.name}] started (layer={self.layer})")

    async def stop(self):
        """Stop the agent: unsubscribe, cancel tick loop."""
        self.state = AgentState.STOPPED

        for event_type in self.subscriptions():
            self.event_bus.unsubscribe(event_type, self._on_event)

        if self._tick_task:
            self._tick_task.cancel()
            try:
                await self._tick_task
            except asyncio.CancelledError:
                pass

        logger.info(f"Agent [{self.name}] stopped")

    # ── Event handling ─────────────────────────────────────────

    async def _on_event(self, event: Event):
        """Internal event dispatcher with state management."""
        self.metrics.events_received += 1

        if self.state == AgentState.STOPPED:
            return

        prev_state = self.state
        self.state = AgentState.ACTING

        try:
            await self.handle_event(event)
            self.metrics.actions_taken += 1
            self.metrics.last_action_at = datetime.now(timezone.utc)
        except Exception as e:
            self.metrics.actions_failed += 1
            self.metrics.last_error = str(e)
            self.metrics.last_error_at = datetime.now(timezone.utc)
            self.state = AgentState.ERROR
            logger.error(f"Agent [{self.name}] error handling {event}: {e}")

            # Publish error event for supervisor
            await self.emit(
                EventType.PIPELINE_ERROR,
                {
                    "agent": self.name,
                    "error": str(e),
                    "event": event.type.value,
                },
            )
            return
        finally:
            if self.state == AgentState.ACTING:
                self.state = AgentState.WATCHING

    # ── Periodic tick ──────────────────────────────────────────

    async def _tick_loop(self):
        """
        Periodic check loop with dynamic interval adaptation.

        Each tick cycle:
          1. Sleep for current _tick_interval (may have been adapted)
          2. Call adapt_params() to let agent adjust based on context
          3. Call tick() for the agent's actual logic
        """
        while self.state != AgentState.STOPPED:
            try:
                await asyncio.sleep(self._tick_interval)
                if self.state in (AgentState.WATCHING, AgentState.IDLE):
                    # Let agent adapt parameters before ticking
                    if self.ctx:
                        try:
                            adapted = self.adapt_params()
                            if adapted:
                                self.metrics.last_adapted_params = adapted
                        except Exception as e:
                            logger.warning(f"Agent [{self.name}] adapt_params error: {e}")
                    await self.tick()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Agent [{self.name}] tick error: {e}")
                self.metrics.last_error = str(e)
                self.metrics.last_error_at = datetime.now(timezone.utc)

    # ── Helpers ────────────────────────────────────────────────

    async def emit(self, event_type: EventType, payload: Dict[str, Any] = None):
        """Publish an event from this agent."""
        event = Event(
            type=event_type,
            payload=payload or {},
            source_agent=self.name,
        )
        self.metrics.events_published += 1
        await self.event_bus.publish(event)

    def get_status(self) -> Dict[str, Any]:
        """Get agent status for API/dashboard."""
        return {
            "name": self.name,
            "layer": self.layer,
            "state": self.state.value,
            "metrics": {
                "actions_taken": self.metrics.actions_taken,
                "actions_failed": self.metrics.actions_failed,
                "events_received": self.metrics.events_received,
                "events_published": self.metrics.events_published,
                "last_action_at": (
                    self.metrics.last_action_at.isoformat()
                    if self.metrics.last_action_at
                    else None
                ),
                "last_error": self.metrics.last_error,
                "uptime_started": (
                    self.metrics.uptime_started.isoformat()
                    if self.metrics.uptime_started
                    else None
                ),
                "adapted_params": self.metrics.last_adapted_params,
            },
        }

    # ── Abstract interface ─────────────────────────────────────

    @abstractmethod
    def subscriptions(self) -> List[EventType]:
        """Which events this agent reacts to."""
        ...

    @abstractmethod
    async def handle_event(self, event: Event):
        """React to an event. Override in subclass."""
        ...

    def adapt_params(self) -> Optional[Dict[str, Any]]:
        """
        Read pipeline context and adapt agent parameters dynamically.

        Override in subclass. Return a dict of adapted parameters for logging,
        or None if no adaptation needed.

        Called before each tick() when self.ctx is available.
        """
        return None

    async def tick(self):
        """
        Periodic check. Override for polling-based logic.
        Default: no-op.
        """
        pass
