"""
Knowledge Store — Persistent storage for inferred connections and research state.

This is the long-term memory that agents build up between batches.
Three tables:

1. entity_links — Inferred relationships between symbols/entities
   "NVDA supplies TSLA" | "BTC correlates ETH" | "PLTR competes SNOW"
   These are NOT explicit in any single signal — agents discover them
   by cross-referencing signals, mosaics, and external data.

2. narrative_threads — Storylines tracked across time and sources
   A narrative starts when 2+ signals share a theme keyword.
   Each new signal that matches gets appended. The thread tracks
   how a story evolves: which sources picked it up, when, strength.

3. research_queue — Hypotheses to investigate between batches
   Agents generate these after processing. Each hypothesis has:
   - A question ("Does PLTR's SEC filing mention government contracts?")
   - Expected information value (how much would the answer change our conviction?)
   - Suggested method (which collector/engine to run)
   - Priority (urgency × information_value × freshness)

The Knowledge Store integrates with the ContextLayer:
- ContextLayer reads entity_links to understand symbol relationships
- ContextLayer reads narrative_threads to detect accelerating stories
- Agents query the store to avoid redundant research
"""

import json
import logging
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ── Schema Creation ───────────────────────────────────────────

KNOWLEDGE_SCHEMA = """
-- Inferred relationships between entities/symbols.
-- Agents discover these by cross-referencing signals.
CREATE TABLE IF NOT EXISTS entity_links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_symbol TEXT NOT NULL,       -- e.g., "NVDA"
    target_symbol TEXT NOT NULL,       -- e.g., "TSLA"
    link_type TEXT NOT NULL,           -- "supplies", "competes", "correlates", "sector_peer", "narrative_overlap"
    strength REAL DEFAULT 0.5,         -- 0.0 to 1.0
    evidence_count INTEGER DEFAULT 1,  -- how many signals support this link
    evidence_json TEXT,                -- JSON array of signal/mosaic IDs that support it
    discovered_by TEXT,                -- agent name that found it
    first_seen TEXT NOT NULL,          -- when first discovered
    last_updated TEXT NOT NULL,        -- when last reinforced
    decay_rate REAL DEFAULT 0.05       -- strength decays if not reinforced
);

-- Evolving storylines tracked across time and sources.
-- A thread is a cluster of signals sharing a narrative theme.
CREATE TABLE IF NOT EXISTS narrative_threads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    thread_key TEXT NOT NULL UNIQUE,    -- normalized theme slug: "ai-regulatory-risk"
    title TEXT NOT NULL,                -- human-readable: "AI Regulatory Risk"
    symbols TEXT NOT NULL,              -- comma-separated symbols involved
    sources TEXT NOT NULL,              -- comma-separated sources that reported
    signal_count INTEGER DEFAULT 1,    -- total signals in thread
    first_signal_at TEXT NOT NULL,
    last_signal_at TEXT NOT NULL,
    velocity REAL DEFAULT 0.0,         -- signals per day (recent)
    acceleration REAL DEFAULT 0.0,     -- change in velocity
    lifecycle_stage TEXT DEFAULT 'emerging',  -- emerging → building → peaking → fading
    summary TEXT,                       -- latest narrative summary
    signal_ids_json TEXT,               -- JSON array of signal IDs in this thread
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- Research hypotheses for agents to investigate between batches.
CREATE TABLE IF NOT EXISTS research_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hypothesis TEXT NOT NULL,            -- "Check if PLTR SEC 8-K mentions government contracts"
    question_type TEXT NOT NULL,         -- "gap_fill", "correlation_check", "narrative_extension", "contradiction_search", "entity_discovery"
    target_symbols TEXT,                 -- comma-separated
    suggested_source TEXT,               -- which collector to use
    suggested_engine TEXT,               -- which engine to run
    priority REAL DEFAULT 0.5,           -- 0.0 to 1.0 (urgency × info_value)
    information_value REAL DEFAULT 0.5,  -- expected info gain if investigated
    status TEXT DEFAULT 'pending',       -- "pending", "investigating", "completed", "expired", "failed"
    generated_by TEXT,                   -- agent that created this hypothesis
    assigned_to TEXT,                    -- agent currently investigating (NULL if unassigned)
    result_json TEXT,                    -- what was found
    parent_id INTEGER,                   -- if this hypothesis spawned from another
    created_at TEXT NOT NULL,
    expires_at TEXT,                     -- hypotheses go stale
    started_at TEXT,
    completed_at TEXT,
    FOREIGN KEY (parent_id) REFERENCES research_queue(id)
);

-- Indexes for fast lookups
CREATE INDEX IF NOT EXISTS idx_entity_links_source ON entity_links(source_symbol);
CREATE INDEX IF NOT EXISTS idx_entity_links_target ON entity_links(target_symbol);
CREATE INDEX IF NOT EXISTS idx_entity_links_type ON entity_links(link_type);
CREATE INDEX IF NOT EXISTS idx_narrative_threads_key ON narrative_threads(thread_key);
CREATE INDEX IF NOT EXISTS idx_narrative_threads_stage ON narrative_threads(lifecycle_stage);
CREATE INDEX IF NOT EXISTS idx_research_queue_status ON research_queue(status);
CREATE INDEX IF NOT EXISTS idx_research_queue_priority ON research_queue(priority DESC);
"""


class KnowledgeStore:
    """
    Persistent knowledge accumulator for the agent pipeline.

    Agents write to this between batches as they research.
    The ContextLayer and other agents read from it to make smarter decisions.
    """

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._ensure_schema()

    def _ensure_schema(self):
        """Create knowledge tables if they don't exist."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.executescript(KNOWLEDGE_SCHEMA)
                conn.commit()
            logger.info("KnowledgeStore: schema verified")
        except Exception as e:
            logger.error(f"KnowledgeStore: schema error: {e}")

    # ── Entity Links ──────────────────────────────────────────

    def upsert_entity_link(
        self,
        source_symbol: str,
        target_symbol: str,
        link_type: str,
        strength: float = 0.5,
        evidence: Optional[List[int]] = None,
        discovered_by: str = "system",
    ) -> int:
        """
        Create or reinforce an entity link.
        If the link exists, increment evidence_count and update strength.
        """
        now = datetime.now(timezone.utc).isoformat()
        evidence_json = json.dumps(evidence or [])

        with sqlite3.connect(self.db_path) as conn:
            # Check if link exists
            existing = conn.execute(
                """SELECT id, strength, evidence_count, evidence_json
                   FROM entity_links
                   WHERE source_symbol = ? AND target_symbol = ? AND link_type = ?""",
                (source_symbol, target_symbol, link_type),
            ).fetchone()

            if existing:
                link_id, old_strength, old_count, old_evidence_str = existing
                # Reinforce: weighted average of old and new strength
                new_strength = (old_strength * old_count + strength) / (old_count + 1)
                new_count = old_count + 1

                # Merge evidence lists
                try:
                    old_evidence = json.loads(old_evidence_str or "[]")
                except json.JSONDecodeError:
                    old_evidence = []
                merged = list(set(old_evidence + (evidence or [])))

                conn.execute(
                    """UPDATE entity_links
                       SET strength = ?, evidence_count = ?, evidence_json = ?,
                           last_updated = ?
                       WHERE id = ?""",
                    (new_strength, new_count, json.dumps(merged), now, link_id),
                )
                conn.commit()
                return link_id
            else:
                cursor = conn.execute(
                    """INSERT INTO entity_links
                       (source_symbol, target_symbol, link_type, strength,
                        evidence_count, evidence_json, discovered_by,
                        first_seen, last_updated)
                       VALUES (?, ?, ?, ?, 1, ?, ?, ?, ?)""",
                    (source_symbol, target_symbol, link_type, strength,
                     evidence_json, discovered_by, now, now),
                )
                conn.commit()
                return cursor.lastrowid

    def get_entity_links(
        self,
        symbol: str,
        link_type: Optional[str] = None,
        min_strength: float = 0.2,
    ) -> List[Dict[str, Any]]:
        """Get all links involving a symbol (as source or target)."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            query = """
                SELECT * FROM entity_links
                WHERE (source_symbol = ? OR target_symbol = ?)
                  AND strength >= ?
            """
            params = [symbol, symbol, min_strength]

            if link_type:
                query += " AND link_type = ?"
                params.append(link_type)

            query += " ORDER BY strength DESC"
            rows = conn.execute(query, params).fetchall()
            return [dict(r) for r in rows]

    def get_related_symbols(self, symbol: str, min_strength: float = 0.3) -> List[str]:
        """Get symbols connected to a given symbol via any link type."""
        links = self.get_entity_links(symbol, min_strength=min_strength)
        related = set()
        for link in links:
            if link["source_symbol"] == symbol:
                related.add(link["target_symbol"])
            else:
                related.add(link["source_symbol"])
        return list(related)

    def decay_links(self, decay_amount: float = 0.01):
        """
        Decay all link strengths over time. Links that haven't been reinforced
        gradually weaken. Called periodically by Supervisor.
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """UPDATE entity_links
                   SET strength = MAX(0.0, strength - decay_rate * ?)
                   WHERE strength > 0""",
                (decay_amount,),
            )
            # Remove dead links
            conn.execute("DELETE FROM entity_links WHERE strength <= 0.0")
            conn.commit()

    # ── Narrative Threads ─────────────────────────────────────

    def upsert_narrative_thread(
        self,
        thread_key: str,
        title: str,
        symbols: List[str],
        sources: List[str],
        signal_ids: Optional[List[int]] = None,
        summary: Optional[str] = None,
    ) -> int:
        """
        Create or extend a narrative thread.
        If thread_key exists, merge new symbols/sources and update velocity.
        """
        now = datetime.now(timezone.utc).isoformat()

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            existing = conn.execute(
                "SELECT * FROM narrative_threads WHERE thread_key = ?",
                (thread_key,),
            ).fetchone()

            if existing:
                row = dict(existing)
                # Merge symbols and sources
                old_symbols = set(row["symbols"].split(","))
                old_sources = set(row["sources"].split(","))
                old_signal_ids = json.loads(row["signal_ids_json"] or "[]")

                merged_symbols = sorted(old_symbols | set(symbols))
                merged_sources = sorted(old_sources | set(sources))
                merged_signal_ids = list(set(old_signal_ids + (signal_ids or [])))
                new_count = len(merged_signal_ids)

                # Compute velocity: signals in last 24h / 1 day
                # Acceleration: compare to previous velocity
                old_velocity = row["velocity"]
                # Simple estimate: (new_count - old_count) represents recent addition rate
                new_velocity = max(0, new_count - row["signal_count"])
                acceleration = new_velocity - old_velocity

                # Lifecycle stage based on velocity and count
                if new_count < 5:
                    stage = "emerging"
                elif acceleration > 0:
                    stage = "building"
                elif new_velocity > old_velocity * 0.5:
                    stage = "peaking"
                else:
                    stage = "fading"

                conn.execute(
                    """UPDATE narrative_threads
                       SET symbols = ?, sources = ?, signal_count = ?,
                           last_signal_at = ?, velocity = ?, acceleration = ?,
                           lifecycle_stage = ?, summary = COALESCE(?, summary),
                           signal_ids_json = ?, updated_at = ?
                       WHERE id = ?""",
                    (",".join(merged_symbols), ",".join(merged_sources),
                     new_count, now, new_velocity, acceleration,
                     stage, summary, json.dumps(merged_signal_ids), now,
                     row["id"]),
                )
                conn.commit()
                return row["id"]
            else:
                cursor = conn.execute(
                    """INSERT INTO narrative_threads
                       (thread_key, title, symbols, sources, signal_count,
                        first_signal_at, last_signal_at, velocity, acceleration,
                        lifecycle_stage, summary, signal_ids_json,
                        created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, 1.0, 0.0, 'emerging', ?, ?, ?, ?)""",
                    (thread_key, title, ",".join(symbols), ",".join(sources),
                     len(signal_ids or []), now, now, summary,
                     json.dumps(signal_ids or []), now, now),
                )
                conn.commit()
                return cursor.lastrowid

    def get_active_threads(
        self,
        min_signals: int = 2,
        stages: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Get narrative threads that are still active."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            query = "SELECT * FROM narrative_threads WHERE signal_count >= ?"
            params = [min_signals]

            if stages:
                placeholders = ",".join(["?"] * len(stages))
                query += f" AND lifecycle_stage IN ({placeholders})"
                params.extend(stages)

            query += " ORDER BY velocity DESC, signal_count DESC"
            rows = conn.execute(query, params).fetchall()
            return [dict(r) for r in rows]

    def get_threads_for_symbol(self, symbol: str) -> List[Dict[str, Any]]:
        """Get all narrative threads mentioning a symbol."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM narrative_threads WHERE symbols LIKE ? ORDER BY velocity DESC",
                (f"%{symbol}%",),
            ).fetchall()
            return [dict(r) for r in rows]

    # ── Research Queue ────────────────────────────────────────

    def enqueue_hypothesis(
        self,
        hypothesis: str,
        question_type: str,
        target_symbols: Optional[List[str]] = None,
        suggested_source: Optional[str] = None,
        suggested_engine: Optional[str] = None,
        priority: float = 0.5,
        information_value: float = 0.5,
        generated_by: str = "system",
        parent_id: Optional[int] = None,
        expires_hours: float = 24.0,
    ) -> int:
        """
        Add a research hypothesis to the queue.
        Returns the hypothesis ID.
        """
        now = datetime.now(timezone.utc)
        expires = (now + __import__("datetime").timedelta(hours=expires_hours)).isoformat()

        with sqlite3.connect(self.db_path) as conn:
            # Check for duplicate hypothesis (same question, same targets, still pending)
            existing = conn.execute(
                """SELECT id FROM research_queue
                   WHERE hypothesis = ? AND status = 'pending'
                   AND (target_symbols = ? OR target_symbols IS NULL)""",
                (hypothesis, ",".join(target_symbols) if target_symbols else None),
            ).fetchone()

            if existing:
                # Boost priority of existing hypothesis instead of duplicating
                conn.execute(
                    "UPDATE research_queue SET priority = MIN(1.0, priority + 0.1) WHERE id = ?",
                    (existing[0],),
                )
                conn.commit()
                return existing[0]

            cursor = conn.execute(
                """INSERT INTO research_queue
                   (hypothesis, question_type, target_symbols, suggested_source,
                    suggested_engine, priority, information_value, status,
                    generated_by, parent_id, created_at, expires_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?, ?, ?)""",
                (hypothesis, question_type,
                 ",".join(target_symbols) if target_symbols else None,
                 suggested_source, suggested_engine,
                 priority, information_value,
                 generated_by, parent_id,
                 now.isoformat(), expires),
            )
            conn.commit()
            return cursor.lastrowid

    def claim_hypothesis(self, agent_name: str, question_types: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
        """
        Claim the highest-priority pending hypothesis for investigation.
        Returns the hypothesis or None if queue is empty.
        Uses atomic UPDATE to prevent race conditions between agents.
        """
        now = datetime.now(timezone.utc).isoformat()

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            # Build type filter
            type_filter = ""
            params = [now]
            if question_types:
                placeholders = ",".join(["?"] * len(question_types))
                type_filter = f"AND question_type IN ({placeholders})"
                params.extend(question_types)

            # Atomically claim the highest-priority unexpired hypothesis
            row = conn.execute(
                f"""SELECT id FROM research_queue
                   WHERE status = 'pending'
                     AND (expires_at IS NULL OR expires_at > ?)
                     {type_filter}
                   ORDER BY priority DESC
                   LIMIT 1""",
                params,
            ).fetchone()

            if not row:
                return None

            hypothesis_id = row["id"]

            # Claim it
            conn.execute(
                """UPDATE research_queue
                   SET status = 'investigating', assigned_to = ?, started_at = ?
                   WHERE id = ? AND status = 'pending'""",
                (agent_name, now, hypothesis_id),
            )
            conn.commit()

            # Return the full hypothesis
            result = conn.execute(
                "SELECT * FROM research_queue WHERE id = ?",
                (hypothesis_id,),
            ).fetchone()
            return dict(result) if result else None

    def complete_hypothesis(
        self,
        hypothesis_id: int,
        result: Dict[str, Any],
        status: str = "completed",
    ):
        """Mark a hypothesis as investigated with results."""
        now = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """UPDATE research_queue
                   SET status = ?, result_json = ?, completed_at = ?
                   WHERE id = ?""",
                (status, json.dumps(result), now, hypothesis_id),
            )
            conn.commit()

    def expire_stale_hypotheses(self):
        """Mark expired or stuck hypotheses."""
        now = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            # Expire old pending hypotheses
            conn.execute(
                """UPDATE research_queue
                   SET status = 'expired'
                   WHERE status = 'pending' AND expires_at < ?""",
                (now,),
            )
            # Reset stuck investigations (assigned > 1 hour ago)
            one_hour_ago = (datetime.now(timezone.utc) - __import__("datetime").timedelta(hours=1)).isoformat()
            conn.execute(
                """UPDATE research_queue
                   SET status = 'pending', assigned_to = NULL, started_at = NULL
                   WHERE status = 'investigating' AND started_at < ?""",
                (one_hour_ago,),
            )
            conn.commit()

    def get_queue_stats(self) -> Dict[str, Any]:
        """Get research queue statistics."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT status, COUNT(*) as cnt FROM research_queue GROUP BY status"
            ).fetchall()
            stats = {r["status"]: r["cnt"] for r in rows}

            # Top pending by priority
            top = conn.execute(
                """SELECT hypothesis, question_type, priority, target_symbols
                   FROM research_queue WHERE status = 'pending'
                   ORDER BY priority DESC LIMIT 5"""
            ).fetchall()

            return {
                "counts": stats,
                "total": sum(stats.values()),
                "top_pending": [dict(r) for r in top],
            }

    # ── Knowledge Summary ─────────────────────────────────────

    def get_knowledge_summary(self) -> Dict[str, Any]:
        """Full knowledge store summary for API/dashboard."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            link_count = conn.execute("SELECT COUNT(*) as cnt FROM entity_links").fetchone()["cnt"]
            link_types = conn.execute(
                "SELECT link_type, COUNT(*) as cnt FROM entity_links GROUP BY link_type ORDER BY cnt DESC"
            ).fetchall()

            thread_count = conn.execute("SELECT COUNT(*) as cnt FROM narrative_threads").fetchone()["cnt"]
            thread_stages = conn.execute(
                "SELECT lifecycle_stage, COUNT(*) as cnt FROM narrative_threads GROUP BY lifecycle_stage"
            ).fetchall()

            queue_stats = self.get_queue_stats()

            return {
                "entity_links": {
                    "total": link_count,
                    "by_type": {r["link_type"]: r["cnt"] for r in link_types},
                },
                "narrative_threads": {
                    "total": thread_count,
                    "by_stage": {r["lifecycle_stage"]: r["cnt"] for r in thread_stages},
                },
                "research_queue": queue_stats,
            }
