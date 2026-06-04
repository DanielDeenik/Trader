"""
Research Orchestrator — Continuous hypothesis-driven research between batches.

After a batch completes:
  1. Agents generate research hypotheses based on what they found
  2. Hypotheses go into the research_queue ranked by information value
  3. Between batches, idle agents claim hypotheses and investigate
  4. Investigations produce entity_links and narrative_threads
  5. The knowledge store feeds back into the next pipeline cycle

Research Types (each agent generates and claims different types):

  gap_fill        — Sentinel: "Source X is silent on hot symbol Y, collect from X"
  correlation     — Assembler: "Signals A and B mention the same theme, are symbols linked?"
  narrative_ext   — Assembler: "Narrative thread Z is building, find more signals"
  contradiction   — Strategist: "Thesis says bullish but recent signals are bearish"
  entity_discovery — Strategist: "Symbol A's supplier/competitor might be affected"
  reinforcement   — Gatekeeper: "Pending review for X, find confirming/disconfirming evidence"

The orchestrator doesn't do AI reasoning — it generates hypotheses from
database patterns and dispatches them to collectors/engines for investigation.
"""

import json
import logging
import re
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from .knowledge import KnowledgeStore

logger = logging.getLogger(__name__)


class ResearchOrchestrator:
    """
    Generates and manages research hypotheses.

    Called by agents after they finish processing a batch event.
    Also called by the Supervisor during idle periods to keep
    the research queue populated.
    """

    def __init__(self, db_path: str, knowledge: KnowledgeStore):
        self.db_path = db_path
        self.knowledge = knowledge

    # ── Hypothesis Generation (called by agents) ──────────────

    def generate_gap_hypotheses(self, hot_symbols: List[Dict]) -> List[int]:
        """
        Sentinel calls this after collecting. Finds gaps:
        - Hot symbols that are missing coverage from key sources
        - Related symbols (from entity_links) that haven't been collected recently
        """
        generated = []

        with sqlite3.connect(self.db_path) as conn:
            for hot in hot_symbols[:10]:
                symbol = hot["symbol"]
                source_count = hot.get("source_count", 0)

                # Gap: hot symbol covered by few sources
                if source_count < 3:
                    # Which sources are we missing?
                    covered = conn.execute(
                        """SELECT DISTINCT source FROM signals
                           WHERE symbol = ? AND timestamp > ?""",
                        (symbol, (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()),
                    ).fetchall()
                    covered_sources = {r[0] for r in covered}

                    all_sources = {"yfinance", "reddit", "sec_edgar", "google_trends", "coingecko", "defillama"}
                    missing = all_sources - covered_sources

                    for source in missing:
                        hid = self.knowledge.enqueue_hypothesis(
                            hypothesis=f"Collect {source} data for {symbol} (hot symbol, {source_count} sources only)",
                            question_type="gap_fill",
                            target_symbols=[symbol],
                            suggested_source=source,
                            priority=min(1.0, hot.get("urgency_score", 0.5) / 5),
                            information_value=0.6,
                            generated_by="sentinel",
                            expires_hours=12.0,
                        )
                        generated.append(hid)

                # Related symbol discovery: check entity_links for peers
                related = self.knowledge.get_related_symbols(symbol, min_strength=0.3)
                for rel_symbol in related[:3]:
                    # Is the related symbol also being tracked?
                    has_recent = conn.execute(
                        "SELECT COUNT(*) FROM signals WHERE symbol = ? AND timestamp > ?",
                        (rel_symbol, (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()),
                    ).fetchone()[0]

                    if has_recent < 2:
                        hid = self.knowledge.enqueue_hypothesis(
                            hypothesis=f"Collect signals for {rel_symbol} (linked to hot symbol {symbol})",
                            question_type="gap_fill",
                            target_symbols=[rel_symbol],
                            priority=0.4,
                            information_value=0.5,
                            generated_by="sentinel",
                            expires_hours=12.0,
                        )
                        generated.append(hid)

        logger.info(f"ResearchOrchestrator: generated {len(generated)} gap hypotheses")
        return generated

    def generate_correlation_hypotheses(self, symbols_analyzed: List[str]) -> List[int]:
        """
        Assembler calls this after creating mosaics. Finds correlations:
        - Symbols that share narrative keywords across mosaics
        - Signals from different sources mentioning the same theme
        - Sector peers with diverging sentiment
        """
        generated = []

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            # Find mosaics that share narrative themes
            recent_mosaics = conn.execute(
                """SELECT id, symbol, narrative, coherence_score, domain
                   FROM mosaics
                   WHERE symbol IN ({})
                   AND created_at > ?
                   ORDER BY created_at DESC""".format(
                    ",".join(["?"] * len(symbols_analyzed))
                ),
                symbols_analyzed + [(datetime.now(timezone.utc) - timedelta(hours=48)).isoformat()],
            ).fetchall()

            # Extract key themes from narratives
            symbol_themes = {}
            for mosaic in recent_mosaics:
                m = dict(mosaic)
                narrative = (m.get("narrative") or "").lower()
                symbol = m["symbol"]

                # Simple theme extraction: significant words from narrative
                themes = self._extract_themes(narrative)
                symbol_themes[symbol] = themes

            # Find symbols sharing themes
            symbols_list = list(symbol_themes.keys())
            for i, sym_a in enumerate(symbols_list):
                for sym_b in symbols_list[i + 1:]:
                    shared = symbol_themes[sym_a] & symbol_themes[sym_b]
                    if len(shared) >= 2:
                        # These symbols share narrative themes → potential link
                        shared_str = ", ".join(list(shared)[:5])

                        # Create entity link
                        self.knowledge.upsert_entity_link(
                            source_symbol=sym_a,
                            target_symbol=sym_b,
                            link_type="narrative_overlap",
                            strength=min(1.0, len(shared) * 0.2),
                            discovered_by="assembler",
                        )

                        # Create/extend narrative thread
                        thread_key = "-".join(sorted(list(shared)[:3]))
                        self.knowledge.upsert_narrative_thread(
                            thread_key=thread_key,
                            title=f"Shared narrative: {shared_str}",
                            symbols=[sym_a, sym_b],
                            sources=[],
                        )

                        # Hypothesis: investigate the connection deeper
                        hid = self.knowledge.enqueue_hypothesis(
                            hypothesis=f"Investigate narrative overlap between {sym_a} and {sym_b}: {shared_str}",
                            question_type="correlation",
                            target_symbols=[sym_a, sym_b],
                            suggested_engine="cross_domain_amplifier",
                            priority=min(1.0, len(shared) * 0.15),
                            information_value=0.7,
                            generated_by="assembler",
                            expires_hours=24.0,
                        )
                        generated.append(hid)

            # Check for sector peers with diverging sentiment
            for symbol in symbols_analyzed[:10]:
                instrument = conn.execute(
                    "SELECT sector, vertical FROM instruments WHERE symbol = ?",
                    (symbol,),
                ).fetchone()

                if instrument and instrument["sector"]:
                    peers = conn.execute(
                        """SELECT i.symbol, m.coherence_score, m.divergence_strength
                           FROM instruments i
                           JOIN mosaics m ON m.symbol = i.symbol
                           WHERE i.sector = ? AND i.symbol != ?
                           AND m.created_at > ?
                           ORDER BY m.created_at DESC""",
                        (instrument["sector"], symbol,
                         (datetime.now(timezone.utc) - timedelta(hours=48)).isoformat()),
                    ).fetchall()

                    for peer in peers[:3]:
                        p = dict(peer)
                        # Create sector_peer link
                        self.knowledge.upsert_entity_link(
                            source_symbol=symbol,
                            target_symbol=p["symbol"],
                            link_type="sector_peer",
                            strength=0.6,
                            discovered_by="assembler",
                        )

        logger.info(f"ResearchOrchestrator: generated {len(generated)} correlation hypotheses")
        return generated

    def generate_thesis_hypotheses(self, theses: List[Dict]) -> List[int]:
        """
        Strategist calls this after forging theses. Finds:
        - Contradicting signals for existing theses
        - Supply chain / competitor links
        - Thesis freshness checks
        """
        generated = []

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            for thesis in theses[:10]:
                symbol = thesis.get("symbol", "")
                conviction = thesis.get("conviction_score", 0)
                lifecycle = thesis.get("lifecycle_stage", "validating")

                # High-conviction thesis → search for contradicting evidence
                if conviction > 0.5:
                    hid = self.knowledge.enqueue_hypothesis(
                        hypothesis=f"Search for contradicting signals for {symbol} thesis (conviction={conviction:.2f})",
                        question_type="contradiction",
                        target_symbols=[symbol],
                        suggested_source="reddit",
                        priority=min(1.0, conviction * 0.8),
                        information_value=0.8,  # Contradictions are very valuable
                        generated_by="strategist",
                        expires_hours=24.0,
                    )
                    generated.append(hid)

                # Entity discovery: find related companies
                # Check instruments for sector peers we haven't linked yet
                instrument = conn.execute(
                    "SELECT sector, vertical FROM instruments WHERE symbol = ?",
                    (symbol,),
                ).fetchone()

                if instrument and instrument["sector"]:
                    existing_links = self.knowledge.get_entity_links(symbol)
                    linked_symbols = {
                        l["target_symbol"] if l["source_symbol"] == symbol else l["source_symbol"]
                        for l in existing_links
                    }

                    unlinked_peers = conn.execute(
                        """SELECT symbol, name FROM instruments
                           WHERE sector = ? AND vertical = ?
                           AND symbol != ? AND symbol NOT IN ({})
                           LIMIT 5""".format(
                            ",".join(["?"] * max(1, len(linked_symbols)))
                        ),
                        [instrument["sector"], instrument["vertical"], symbol] +
                        list(linked_symbols or ["__none__"]),
                    ).fetchall()

                    for peer in unlinked_peers:
                        hid = self.knowledge.enqueue_hypothesis(
                            hypothesis=f"Discover entity relationship: {symbol} ↔ {peer['symbol']} ({peer['name']}) in {instrument['vertical']}",
                            question_type="entity_discovery",
                            target_symbols=[symbol, peer["symbol"]],
                            suggested_engine="cross_domain_amplifier",
                            priority=0.4,
                            information_value=0.5,
                            generated_by="strategist",
                            expires_hours=48.0,
                        )
                        generated.append(hid)

        logger.info(f"ResearchOrchestrator: generated {len(generated)} thesis hypotheses")
        return generated

    def generate_review_hypotheses(self, pending_reviews: List[Dict]) -> List[int]:
        """
        Gatekeeper calls this for pending reviews. Finds confirming/disconfirming evidence
        to help prioritize which reviews to fast-track.
        """
        generated = []

        for review in pending_reviews[:5]:
            symbol = review.get("symbol", "")
            total_score = review.get("total_score", 0)

            hid = self.knowledge.enqueue_hypothesis(
                hypothesis=f"Find confirming evidence for {symbol} review (score={total_score})",
                question_type="reinforcement",
                target_symbols=[symbol],
                priority=min(1.0, total_score / 20.0),
                information_value=0.6,
                generated_by="gatekeeper",
                expires_hours=12.0,
            )
            generated.append(hid)

        logger.info(f"ResearchOrchestrator: generated {len(generated)} review hypotheses")
        return generated

    # ── Investigation Execution ───────────────────────────────

    def investigate_hypothesis(self, hypothesis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a research hypothesis investigation.

        This is the actual research work — querying the DB, running engines,
        and producing entity_links / narrative_threads.

        Returns result dict to be stored in the hypothesis record.
        """
        q_type = hypothesis["question_type"]
        targets = (hypothesis.get("target_symbols") or "").split(",")
        targets = [t.strip() for t in targets if t.strip()]

        if q_type == "gap_fill":
            return self._investigate_gap(hypothesis, targets)
        elif q_type == "correlation":
            return self._investigate_correlation(hypothesis, targets)
        elif q_type == "contradiction":
            return self._investigate_contradiction(hypothesis, targets)
        elif q_type == "entity_discovery":
            return self._investigate_entity(hypothesis, targets)
        elif q_type == "reinforcement":
            return self._investigate_reinforcement(hypothesis, targets)
        elif q_type == "narrative_ext":
            return self._investigate_narrative(hypothesis, targets)
        else:
            return {"status": "unknown_type", "type": q_type}

    def _investigate_gap(self, hypothesis: Dict, targets: List[str]) -> Dict:
        """
        Gap fill: check what data exists for target symbols across sources.
        Identify specific gaps and flag them for the next collection cycle.
        """
        results = {"gaps_found": [], "already_covered": []}

        with sqlite3.connect(self.db_path) as conn:
            for symbol in targets:
                coverage = conn.execute(
                    """SELECT source, COUNT(*) as cnt, MAX(timestamp) as latest
                       FROM signals WHERE symbol = ?
                       GROUP BY source""",
                    (symbol,),
                ).fetchall()

                source_map = {r[0]: {"count": r[1], "latest": r[2]} for r in coverage}
                suggested = hypothesis.get("suggested_source")

                if suggested and suggested not in source_map:
                    results["gaps_found"].append({
                        "symbol": symbol,
                        "missing_source": suggested,
                        "existing_sources": list(source_map.keys()),
                    })
                else:
                    results["already_covered"].append(symbol)

        return results

    def _investigate_correlation(self, hypothesis: Dict, targets: List[str]) -> Dict:
        """
        Correlation check: compare signal patterns between target symbols.
        Look for co-occurring themes, synchronized timing, shared sources.
        """
        if len(targets) < 2:
            return {"status": "need_two_symbols"}

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            sym_a, sym_b = targets[0], targets[1]
            cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()

            # Compare signal timing patterns
            signals_a = conn.execute(
                "SELECT source, direction, timestamp FROM signals WHERE symbol = ? AND timestamp > ?",
                (sym_a, cutoff),
            ).fetchall()
            signals_b = conn.execute(
                "SELECT source, direction, timestamp FROM signals WHERE symbol = ? AND timestamp > ?",
                (sym_b, cutoff),
            ).fetchall()

            # Shared sources
            sources_a = {r["source"] for r in signals_a}
            sources_b = {r["source"] for r in signals_b}
            shared_sources = sources_a & sources_b

            # Direction alignment
            dir_a = [r["direction"] for r in signals_a]
            dir_b = [r["direction"] for r in signals_b]
            bullish_a = dir_a.count("bullish") / max(len(dir_a), 1)
            bullish_b = dir_b.count("bullish") / max(len(dir_b), 1)
            alignment = 1.0 - abs(bullish_a - bullish_b)

            # Strengthen or weaken the entity link based on findings
            if alignment > 0.7 and len(shared_sources) >= 2:
                self.knowledge.upsert_entity_link(
                    source_symbol=sym_a,
                    target_symbol=sym_b,
                    link_type="correlates",
                    strength=alignment * 0.8,
                    discovered_by="researcher",
                )

            return {
                "symbols": [sym_a, sym_b],
                "shared_sources": list(shared_sources),
                "signal_counts": [len(signals_a), len(signals_b)],
                "direction_alignment": round(alignment, 3),
                "correlation_strength": round(alignment * len(shared_sources) / 5, 3),
            }

    def _investigate_contradiction(self, hypothesis: Dict, targets: List[str]) -> Dict:
        """
        Contradiction search: look for signals that oppose the current thesis.
        """
        results = {"contradictions": [], "confirmations": 0}

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            for symbol in targets:
                # Get thesis direction
                thesis = conn.execute(
                    "SELECT * FROM theses WHERE symbol = ? ORDER BY created_at DESC LIMIT 1",
                    (symbol,),
                ).fetchone()

                if not thesis:
                    continue

                # Look for bearish signals if thesis implies bullish (or vice versa)
                recent_signals = conn.execute(
                    """SELECT id, source, direction, strength, timestamp
                       FROM signals WHERE symbol = ? AND timestamp > ?
                       ORDER BY timestamp DESC LIMIT 20""",
                    (symbol, (datetime.now(timezone.utc) - timedelta(hours=48)).isoformat()),
                ).fetchall()

                for sig in recent_signals:
                    s = dict(sig)
                    if s["direction"] == "bearish":
                        results["contradictions"].append({
                            "signal_id": s["id"],
                            "source": s["source"],
                            "direction": s["direction"],
                            "strength": s["strength"],
                        })
                    else:
                        results["confirmations"] += 1

        return results

    def _investigate_entity(self, hypothesis: Dict, targets: List[str]) -> Dict:
        """
        Entity discovery: determine relationship between symbols.
        Uses instrument metadata + signal patterns.
        """
        if len(targets) < 2:
            return {"status": "need_two_symbols"}

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            sym_a, sym_b = targets[0], targets[1]

            inst_a = conn.execute("SELECT * FROM instruments WHERE symbol = ?", (sym_a,)).fetchone()
            inst_b = conn.execute("SELECT * FROM instruments WHERE symbol = ?", (sym_b,)).fetchone()

            if not inst_a or not inst_b:
                return {"status": "instruments_not_found"}

            a, b = dict(inst_a), dict(inst_b)

            # Determine relationship type
            link_type = "sector_peer"  # default
            strength = 0.3

            if a.get("sector") == b.get("sector"):
                strength = 0.5
                if a.get("vertical") == b.get("vertical"):
                    link_type = "competes"
                    strength = 0.7

            # Check for supply chain hints (very rough — based on sector combinations)
            supply_chain_pairs = {
                ("Semiconductors", "Software"): "supplies",
                ("Semiconductors", "Cloud"): "supplies",
                ("Cloud", "SaaS"): "supplies",
            }
            pair = (a.get("vertical", ""), b.get("vertical", ""))
            reverse_pair = (b.get("vertical", ""), a.get("vertical", ""))

            if pair in supply_chain_pairs:
                link_type = supply_chain_pairs[pair]
                strength = 0.6
            elif reverse_pair in supply_chain_pairs:
                link_type = supply_chain_pairs[reverse_pair]
                strength = 0.6

            self.knowledge.upsert_entity_link(
                source_symbol=sym_a,
                target_symbol=sym_b,
                link_type=link_type,
                strength=strength,
                discovered_by="researcher",
            )

            return {
                "symbols": [sym_a, sym_b],
                "link_type": link_type,
                "strength": strength,
                "sectors": [a.get("sector"), b.get("sector")],
                "verticals": [a.get("vertical"), b.get("vertical")],
            }

    def _investigate_reinforcement(self, hypothesis: Dict, targets: List[str]) -> Dict:
        """Find confirming evidence for a pending review."""
        results = {"confirming_signals": 0, "sources": [], "latest_direction": None}

        with sqlite3.connect(self.db_path) as conn:
            for symbol in targets:
                signals = conn.execute(
                    """SELECT source, direction, COUNT(*) as cnt
                       FROM signals WHERE symbol = ? AND timestamp > ?
                       GROUP BY source, direction""",
                    (symbol, (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()),
                ).fetchall()

                for s in signals:
                    results["confirming_signals"] += s[2]
                    if s[0] not in results["sources"]:
                        results["sources"].append(s[0])

                # Get overall sentiment direction
                dir_row = conn.execute(
                    """SELECT direction, COUNT(*) as cnt FROM signals
                       WHERE symbol = ? AND timestamp > ?
                       GROUP BY direction ORDER BY cnt DESC LIMIT 1""",
                    (symbol, (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()),
                ).fetchone()
                if dir_row:
                    results["latest_direction"] = dir_row[0]

        return results

    def _investigate_narrative(self, hypothesis: Dict, targets: List[str]) -> Dict:
        """Extend a narrative thread with new signals."""
        return {"status": "narrative_extension_pending", "targets": targets}

    # ── Theme Extraction ──────────────────────────────────────

    @staticmethod
    def _extract_themes(text: str) -> set:
        """
        Extract significant theme words from narrative text.
        Filters out common words and returns a set of themes.
        """
        if not text:
            return set()

        # Common stop words to filter out
        stop_words = {
            "the", "a", "an", "is", "are", "was", "were", "be", "been",
            "being", "have", "has", "had", "do", "does", "did", "will",
            "would", "could", "should", "may", "might", "shall", "can",
            "and", "or", "but", "if", "then", "else", "when", "while",
            "for", "of", "to", "from", "by", "with", "at", "in", "on",
            "into", "through", "during", "before", "after", "above",
            "below", "between", "out", "off", "over", "under", "again",
            "further", "than", "once", "not", "no", "nor", "only", "own",
            "same", "so", "too", "very", "just", "about", "up", "down",
            "all", "each", "every", "both", "few", "more", "most",
            "other", "some", "such", "this", "that", "these", "those",
            "it", "its", "signals", "signal", "sources", "source",
            "direction", "bullish", "bearish", "neutral", "coherence",
            "divergence", "pass", "score", "data", "market", "price",
        }

        words = re.findall(r'\b[a-z]{3,}\b', text.lower())
        themes = {w for w in words if w not in stop_words and len(w) > 3}
        return themes
