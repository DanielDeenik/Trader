"""
Event Bus — In-process pub/sub for inter-agent communication.

Events flow through the cognitive pipeline:
  SIGNALS_COLLECTED → MOSAICS_ASSEMBLED → THESES_FORGED → DECISIONS_MADE → POSITIONS_UPDATED
                                                    ↑                              ↓
                                                    └──────── feedback loop ────────┘

Each event carries a payload dict with context about what happened.
Agents subscribe to events they care about and react accordingly.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Coroutine, Dict, List, Optional

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """Pipeline events following Camillo's cognitive flow."""

    # L0 → L1: Collection complete, fresh signals available
    SIGNALS_COLLECTED = "signals_collected"

    # L1 → L2: Signals scored and clustered into mosaics
    MOSAICS_ASSEMBLED = "mosaics_assembled"

    # L2 → L3: Mosaics forged into investment theses
    THESES_FORGED = "theses_forged"

    # L3 → L4: HITL decisions made on theses
    DECISIONS_MADE = "decisions_made"

    # L4 → L5: Positions opened/closed/updated
    POSITIONS_UPDATED = "positions_updated"

    # Meta events
    AGENT_STATE_CHANGED = "agent_state_changed"
    PIPELINE_ERROR = "pipeline_error"
    HITL_REQUIRED = "hitl_required"
    SOURCE_STALE = "source_stale"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"


@dataclass
class Event:
    """Immutable event flowing through the pipeline."""

    type: EventType
    payload: Dict[str, Any] = field(default_factory=dict)
    source_agent: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    event_id: str = ""

    def __post_init__(self):
        if not self.event_id:
            import uuid
            self.event_id = str(uuid.uuid4())[:8]

    def __repr__(self):
        return f"Event({self.type.value}, from={self.source_agent}, id={self.event_id})"


# Type alias for event handlers
EventHandler = Callable[[Event], Coroutine[Any, Any, None]]


class EventBus:
    """
    In-process async event bus.

    Agents publish events when they complete work.
    Other agents subscribe to events they need to react to.
    The bus delivers events asynchronously without blocking publishers.
    """

    def __init__(self):
        self._subscribers: Dict[EventType, List[EventHandler]] = {}
        self._history: List[Event] = []
        self._max_history = 500
        self._running = False

    def subscribe(self, event_type: EventType, handler: EventHandler):
        """Subscribe a handler to an event type."""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)
        logger.debug(f"Subscribed {handler.__qualname__} to {event_type.value}")

    def unsubscribe(self, event_type: EventType, handler: EventHandler):
        """Remove a handler subscription."""
        if event_type in self._subscribers:
            self._subscribers[event_type] = [
                h for h in self._subscribers[event_type] if h != handler
            ]

    async def publish(self, event: Event):
        """
        Publish an event to all subscribers.
        Handlers run concurrently but errors in one don't block others.
        """
        self._history.append(event)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

        handlers = self._subscribers.get(event.type, [])
        if not handlers:
            logger.debug(f"No subscribers for {event}")
            return

        logger.info(f"Publishing {event} to {len(handlers)} handler(s)")

        # Fire all handlers concurrently, catch individual errors
        results = await asyncio.gather(
            *[self._safe_handle(h, event) for h in handlers],
            return_exceptions=True,
        )

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(
                    f"Handler {handlers[i].__qualname__} failed on {event}: {result}"
                )

    async def _safe_handle(self, handler: EventHandler, event: Event):
        """Run a handler with error isolation."""
        try:
            await handler(event)
        except Exception as e:
            logger.error(f"Event handler error: {e}", exc_info=True)
            raise

    def get_history(
        self,
        event_type: Optional[EventType] = None,
        limit: int = 50,
    ) -> List[Event]:
        """Get recent event history, optionally filtered by type."""
        events = self._history
        if event_type:
            events = [e for e in events if e.type == event_type]
        return events[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        """Get event bus statistics."""
        type_counts = {}
        for event in self._history:
            key = event.type.value
            type_counts[key] = type_counts.get(key, 0) + 1

        return {
            "total_events": len(self._history),
            "subscriber_count": sum(len(h) for h in self._subscribers.values()),
            "event_types_active": list(self._subscribers.keys()),
            "event_counts": type_counts,
        }
