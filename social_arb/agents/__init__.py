"""
Social Arb Agent Orchestration Layer

Pure orchestration agents that coordinate batch jobs through
Camillo's 5-layer cognitive architecture:

  Sentinel  → Collection orchestration (Peripheral Vision)
  Assembler → Signal→Mosaic pipeline   (Pattern Recognition)
  Strategist→ Thesis generation         (Divergence + Conviction)
  Gatekeeper→ HITL queue management     (Decision Gates)
  Executor  → Position lifecycle        (Execution + Monitoring)
  Supervisor→ Pipeline health           (Meta-cognition)

No LLM calls. Agents are event-driven state machines that
watch for triggers, execute batch jobs, and route outputs
to the next layer or to HITL gates.
"""

from .base import BaseAgent, AgentState
from .events import EventBus, Event, EventType
from .sentinel import Sentinel
from .assembler import Assembler

__all__ = [
    "BaseAgent",
    "AgentState",
    "EventBus",
    "Event",
    "EventType",
    "Sentinel",
    "Assembler",
]
