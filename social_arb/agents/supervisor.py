"""
Supervisor — Meta-cognition layer for the agent pipeline.

The Supervisor doesn't process data — it monitors the health of the
entire cognitive pipeline and intervenes when things go wrong:
- Detects stuck agents (no activity for too long)
- Detects growing HITL backlogs
- Tracks pipeline throughput (signals→positions conversion rate)
- Restarts failed agents
- Publishes pipeline health metrics
"""

import asyncio
import logging
import sqlite3
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from .base import BaseAgent, AgentState
from .context import ContextLayer
from .events import Event, EventBus, EventType
from .knowledge import KnowledgeStore
from .registry import AgentRegistry

logger = logging.getLogger(__name__)


class Supervisor(BaseAgent):
    """
    Meta-agent that monitors pipeline health.

    Camillo's cognitive model requires self-awareness — knowing
    when the information pipeline is degraded, when conviction
    is stale, or when the market window is closing. The Supervisor
    provides that meta-cognition layer.
    """

    def __init__(
        self,
        event_bus: EventBus,
        db_path: str,
        registry: AgentRegistry,
        config: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            name="supervisor",
            layer="meta",
            event_bus=event_bus,
            db_path=db_path,
            config=config or {},
        )
        self.registry = registry
        self._tick_interval = self.config.get("health_check_interval", 120.0)

        # Research mode
        self.knowledge: Optional[KnowledgeStore] = None

        # Pipeline health state
        self._pipeline_health = {
            "status": "unknown",
            "last_check": None,
            "issues": [],
            "throughput": {},
        }

    def subscriptions(self) -> List[EventType]:
        return [EventType.PIPELINE_ERROR, EventType.AGENT_STATE_CHANGED]

    async def handle_event(self, event: Event):
        """React to pipeline errors and agent state changes."""
        if event.type == EventType.PIPELINE_ERROR:
            agent_name = event.payload.get("agent", "unknown")
            error = event.payload.get("error", "unknown error")
            logger.warning(
                f"Supervisor: pipeline error from [{agent_name}]: {error}"
            )

            self._pipeline_health["issues"].append({
                "type": "agent_error",
                "agent": agent_name,
                "error": error,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

            # Keep only last 50 issues
            self._pipeline_health["issues"] = self._pipeline_health["issues"][-50:]

            # Attempt recovery: restart the failed agent
            agent = self.registry.get_agent(agent_name)
            if agent and agent.state == AgentState.ERROR:
                logger.info(f"Supervisor: attempting to restart [{agent_name}]")
                try:
                    await agent.stop()
                    await agent.start()
                    logger.info(f"Supervisor: [{agent_name}] restarted successfully")
                except Exception as e:
                    logger.error(f"Supervisor: failed to restart [{agent_name}]: {e}")

    async def tick(self):
        """
        Periodic pipeline health check — now context-aware.

        Uses ContextLayer for bottleneck detection, pressure metrics,
        and adaptive health assessment instead of just counting rows.
        """
        issues = []

        # Check each agent's health
        all_status = self.registry.get_all_status()
        for agent_info in all_status.get("agents", []):
            name = agent_info["name"]
            state = agent_info["state"]
            metrics = agent_info["metrics"]

            # Detect stopped/errored agents
            if state == "error":
                issues.append({
                    "type": "agent_error",
                    "agent": name,
                    "message": f"Agent in error state: {metrics.get('last_error', 'unknown')}",
                })
            elif state == "stopped":
                issues.append({
                    "type": "agent_stopped",
                    "agent": name,
                    "message": f"Agent is stopped",
                })

            # Detect stuck agents (no action for too long)
            last_action = metrics.get("last_action_at")
            if last_action and state == "watching":
                try:
                    last_dt = datetime.fromisoformat(last_action)
                    stuck_threshold = timedelta(
                        hours=self.config.get("stuck_threshold_hours", 12)
                    )
                    if datetime.now(timezone.utc) - last_dt > stuck_threshold:
                        issues.append({
                            "type": "agent_stuck",
                            "agent": name,
                            "message": f"No activity for {stuck_threshold}",
                        })
                except (ValueError, TypeError):
                    pass

        # Use ContextLayer for intelligent health assessment
        context_data = {}
        if self.ctx:
            pipeline = self.ctx.get_context()
            context_data = pipeline.to_dict()

            # Bottleneck detection from context
            if pipeline.bottleneck_agent:
                issues.append({
                    "type": "pipeline_bottleneck",
                    "agent": pipeline.bottleneck_agent,
                    "severity": round(pipeline.bottleneck_severity, 3),
                    "message": f"Pipeline bottleneck at {pipeline.bottleneck_agent} "
                               f"(severity={pipeline.bottleneck_severity:.1%})",
                })

            # HITL backlog from context (already computed)
            if pipeline.hitl_backlog.value > 0.8:
                issues.append({
                    "type": "hitl_backlog",
                    "message": f"{pipeline.pending_review_count} pending reviews "
                               f"(pressure={pipeline.hitl_backlog.value:.1%})",
                })

            # Portfolio risk from context
            if pipeline.portfolio_heat.value > 0.8:
                issues.append({
                    "type": "portfolio_overheated",
                    "message": f"{pipeline.open_position_count} positions, "
                               f"{pipeline.total_allocation_pct:.1f}% allocated",
                })

            # Signal flow health
            if pipeline.signal_velocity.trend == "falling" and pipeline.signal_velocity.value < 0.2:
                issues.append({
                    "type": "signal_drought",
                    "message": f"Signal flow dropping: {pipeline.signal_velocity.label}",
                })

            # Adaptation summary: what are agents actually doing?
            adaptation_summary = {}
            for agent_info in all_status.get("agents", []):
                adapted = agent_info.get("metrics", {}).get("adapted_params")
                if adapted:
                    adaptation_summary[agent_info["name"]] = adapted

            self._pipeline_health["throughput"] = {
                "signals_24h": context_data.get("pipeline_throughput", {}).get("raw", 0),
                "conversion_rate": context_data.get("conversion_rate", 0),
                "pending_reviews": pipeline.pending_review_count,
            }
            self._pipeline_health["context"] = context_data
            self._pipeline_health["adaptations"] = adaptation_summary

        else:
            # Fallback: basic DB queries if no context layer
            try:
                conn = sqlite3.connect(self.db_path)
                conn.row_factory = sqlite3.Row

                row = conn.execute(
                    "SELECT COUNT(*) as cnt FROM reviews WHERE decision IS NULL OR decision = 'pending'"
                ).fetchone()
                pending_reviews = dict(row).get("cnt", 0) if row else 0

                if pending_reviews > self.config.get("max_hitl_backlog", 20):
                    issues.append({
                        "type": "hitl_backlog",
                        "message": f"{pending_reviews} pending reviews",
                    })

                now = datetime.now(timezone.utc)
                day_ago = (now - timedelta(days=1)).isoformat()

                signals_24h = conn.execute(
                    "SELECT COUNT(*) as cnt FROM signals WHERE timestamp > ?",
                    (day_ago,),
                ).fetchone()
                mosaics_24h = conn.execute(
                    "SELECT COUNT(*) as cnt FROM mosaics WHERE created_at > ?",
                    (day_ago,),
                ).fetchone()
                theses_24h = conn.execute(
                    "SELECT COUNT(*) as cnt FROM theses WHERE created_at > ?",
                    (day_ago,),
                ).fetchone()

                self._pipeline_health["throughput"] = {
                    "signals_24h": dict(signals_24h).get("cnt", 0) if signals_24h else 0,
                    "mosaics_24h": dict(mosaics_24h).get("cnt", 0) if mosaics_24h else 0,
                    "theses_24h": dict(theses_24h).get("cnt", 0) if theses_24h else 0,
                    "pending_reviews": pending_reviews,
                }

                conn.close()
            except Exception as e:
                logger.error(f"Supervisor: DB health check failed: {e}")

        # Update health status
        self._pipeline_health["last_check"] = datetime.now(timezone.utc).isoformat()
        self._pipeline_health["issues"] = issues
        self._pipeline_health["status"] = (
            "healthy" if not issues
            else "degraded" if len(issues) <= 2
            else "unhealthy"
        )

        if issues:
            logger.warning(
                f"Supervisor: pipeline {self._pipeline_health['status']} "
                f"({len(issues)} issue(s))"
            )

        # Knowledge maintenance: decay links, expire hypotheses
        if self.knowledge:
            try:
                self.knowledge.decay_links(decay_amount=0.005)
                self.knowledge.expire_stale_hypotheses()
                knowledge_summary = self.knowledge.get_knowledge_summary()
                self._pipeline_health["knowledge"] = knowledge_summary
                logger.debug(
                    f"Supervisor: knowledge store — "
                    f"{knowledge_summary['entity_links']['total']} links, "
                    f"{knowledge_summary['narrative_threads']['total']} threads, "
                    f"queue={knowledge_summary['research_queue']['total']}"
                )
            except Exception as e:
                logger.error(f"Supervisor: knowledge maintenance failed: {e}")

    def get_status(self) -> Dict[str, Any]:
        """Extended status with pipeline health."""
        base = super().get_status()
        base["pipeline_health"] = self._pipeline_health
        return base

    def get_pipeline_health(self) -> Dict[str, Any]:
        """Get full pipeline health report."""
        return {
            **self._pipeline_health,
            "agents": self.registry.get_all_status(),
            "pipeline_flow": self.registry.get_pipeline_flow(),
        }
