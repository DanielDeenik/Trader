"""
5-Layer Cognitive Topology Engine with Tiered Autonomy HITL

The domain-agnostic orchestration of Camillo's decision-making process.
Each layer receives domain-specific implementations via Protocol interfaces
and executes the universal topology logic.

HITL Philosophy: Creates a feedback loop where the system earns trust over time
through human validation. Start with full manual gates; increase automation as
accuracy improves.

Layers:
    L1 Peripheral Vision  → Ingest signals from domain scrapers
    L2 Mosaic Assembly    → Calculate divergence, score quality, build mosaic cards
    L3 Asymmetry Filter   → Scan vulnerability, simulate payoff, HITL thesis gate
    L4 Timing Calibration → Assess lifecycle stage, identify entry window
    L5 Conviction Sizing  → Size position, record decision in journal

HITL Gates with Tiered Autonomy:
    Gate 1 (L2→L3): Approval thresholds for automatic advancement
    Gate 2 (L3→L4): Thesis validation with confidence scoring
    Gate 3 (L4→L5): Entry confirmation with trust evolution

TrustLevels:
    MANUAL: Always require human approval
    SUPERVISED: Automatic if confidence > threshold; human spot-checks random sample
    AUTONOMOUS: Automatic if confidence > high threshold; audit trail maintained
"""

import logging
from typing import Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from .protocols import (
    Signal, MosaicCard, MosaicFragment, DivergenceResult, ScorerResult,
    VulnerabilityScanResult, SimulationOutput, LifecycleAssessment, PositionSize,
    DomainConfig, SignalDirection, ConvictionLevel,
)

logger = logging.getLogger(__name__)


class TrustLevel(Enum):
    """Autonomy level for HITL gates."""
    MANUAL = "manual"           # Always require human approval
    SUPERVISED = "supervised"   # Auto if confident; human spot-checks
    AUTONOMOUS = "autonomous"   # Auto if very confident; audit trail only


class HITLDecision(Enum):
    """Human-in-the-loop decision at each gate."""
    APPROVE = "approve"
    REJECT = "reject"
    DEFER = "defer"       # Come back to this later
    ESCALATE = "escalate" # Needs more data
    AUTO_APPROVED = "auto_approved"  # System approved without human input
    AUTO_REJECTED = "auto_rejected"  # System rejected without human input


@dataclass
class ConfidenceThreshold:
    """Confidence thresholds per layer for tiered autonomy."""
    layer: int
    trust_level: TrustLevel
    auto_approval_threshold: float  # 0-1: auto-approve if confidence >= this
    spot_check_sample_rate: float   # 0-1: in SUPERVISED mode, audit this % of autos
    high_confidence_threshold: float = 0.85  # For AUTONOMOUS mode

    def should_auto_approve(self, confidence: float, trust_level: Optional[TrustLevel] = None) -> bool:
        """Check if signal should be auto-approved based on trust level."""
        tl = trust_level or self.trust_level
        if tl == TrustLevel.MANUAL:
            return False
        if tl == TrustLevel.SUPERVISED:
            return confidence >= self.auto_approval_threshold
        if tl == TrustLevel.AUTONOMOUS:
            return confidence >= self.high_confidence_threshold
        return False


@dataclass
class AuditEntry:
    """Record of a decision (human or auto) for trust evolution."""
    layer: int
    keyword: str
    domain: str
    decision: str  # "approve" | "reject" | "auto_approved" | "auto_rejected"
    confidence: float
    human_override: bool  # Did human override system?
    override_decision: Optional[str] = None  # What human overrode to
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    rationale: str = ""


@dataclass
class TrustScore:
    """Track system trust per signal type / domain."""
    signal_type: str  # "mosaic_coherence" | "thesis_quality" | "timing_confidence"
    domain: str
    accuracy_pct: float  # % of auto-approvals that human agreed with
    total_audits: int  # How many decisions audited
    evolving_trust_level: TrustLevel  # Can change over time
    last_updated: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class LayerResult:
    """Output of any topology layer execution."""
    layer: int
    domain: str
    keyword: str
    success: bool
    data: dict = field(default_factory=dict)
    hitl_required: bool = False
    hitl_decision: Optional[HITLDecision] = None
    error: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    # Tiered autonomy fields
    confidence: float = 0.5  # System confidence in this result (0-1)
    trust_level: TrustLevel = TrustLevel.MANUAL  # Current autonomy level
    audit_entry: Optional[AuditEntry] = None  # Record for trust evolution


class TopologyEngine:
    """
    Executes the 5-layer cognitive topology for any registered domain.

    The engine is stateless — it receives domain implementations and data,
    processes them through the topology layers, and returns results.
    The dashboard handles HITL gate UI and state persistence.
    """

    def run_layer1(self, domain: DomainConfig, keywords: list[str],
                   demo_mode: bool = True) -> LayerResult:
        """
        Layer 1 — Peripheral Vision: Ingest signals.

        Calls domain scrapers to collect raw signals. In demo mode,
        uses pre-built demo data instead of live API calls.
        """
        all_signals = []

        for scraper in domain.scrapers:
            try:
                if demo_mode:
                    signals = scraper.get_demo_signals()
                else:
                    signals = scraper.scrape(keywords)

                # Tag signals with domain
                for sig in signals:
                    sig.domain = domain.name

                all_signals.extend(signals)
                logger.info(f"[L1] {domain.name}/{scraper.domain_name}: {len(signals)} signals")

            except Exception as e:
                logger.error(f"[L1] Scraper error {scraper.domain_name}: {e}")

        return LayerResult(
            layer=1,
            domain=domain.name,
            keyword=",".join(keywords),
            success=len(all_signals) > 0,
            data={"signals": [s.to_dict() for s in all_signals], "count": len(all_signals)},
        )

    def run_layer2(self, domain: DomainConfig, signals: list[dict],
                   market_data: Optional[dict] = None) -> LayerResult:
        """
        Layer 2 — Mosaic Assembly: Calculate divergence, score, build cards.

        For each signal cluster (grouped by keyword):
        1. Calculate divergence using domain's formula
        2. Score quality using domain's scorer
        3. Assemble mosaic card from fragments
        4. Assess coherence (do signals align?)

        Output: Mosaic cards awaiting HITL Gate 1 approval.
        """
        mosaic_cards = []
        market_data = market_data or {}

        # Group signals by keyword
        keyword_groups: dict[str, list[dict]] = {}
        for sig in signals:
            kw = sig.get("keyword", "unknown")
            keyword_groups.setdefault(kw, []).append(sig)

        for keyword, signal_group in keyword_groups.items():
            try:
                # Step 1: Divergence
                divergence = None
                if domain.divergence:
                    # Aggregate signal data for divergence calc
                    avg_growth = sum(s.get("growth_pct", 0) for s in signal_group) / len(signal_group)
                    signal_data = {"growth_pct": avg_growth, "volume": sum(s.get("volume", 0) for s in signal_group)}
                    kw_market = market_data.get(keyword, {})
                    divergence = domain.divergence.calculate(signal_data, kw_market)

                # Step 2: Quality scoring
                score_result = None
                if domain.scorer:
                    score_result = domain.scorer.score({"keyword": keyword, "signals": signal_group})

                # Step 3: Build mosaic card from fragments
                fragments = self._build_fragments(signal_group)
                coherence = self._assess_coherence(fragments)

                card = MosaicCard(
                    keyword=keyword,
                    domain=domain.name,
                    coherence_score=coherence["score"],
                    coherence_label=coherence["label"],
                    fragments=[f.to_dict() for f in fragments],
                    narrative=self._build_narrative(keyword, divergence, score_result, coherence),
                    action=self._recommend_action(coherence["score"], divergence),
                    metadata={
                        "divergence": divergence.to_dict() if divergence else None,
                        "quality_score": score_result.to_dict() if score_result else None,
                        "signal_count": len(signal_group),
                    },
                )
                mosaic_cards.append(card)

            except Exception as e:
                logger.error(f"[L2] Mosaic assembly error for '{keyword}': {e}")

        return LayerResult(
            layer=2,
            domain=domain.name,
            keyword=",".join(keyword_groups.keys()),
            success=len(mosaic_cards) > 0,
            data={"mosaic_cards": [c.to_dict() for c in mosaic_cards], "count": len(mosaic_cards)},
            hitl_required=True,  # Gate 1: human approves mosaic cards
        )

    def run_layer3(self, domain: DomainConfig, mosaic_card: dict,
                   hitl_decision: HITLDecision = HITLDecision.APPROVE) -> LayerResult:
        """
        Layer 3 — Asymmetry Filter: Vulnerability scan + payoff simulation.

        Only runs if HITL Gate 1 approved the mosaic card.
        1. Scan for vulnerability/weakness in the target
        2. Simulate bear/base/bull payoff scenarios
        3. Build thesis from combined analysis

        Output: Thesis awaiting HITL Gate 2 validation.
        """
        if hitl_decision != HITLDecision.APPROVE:
            return LayerResult(
                layer=3, domain=domain.name,
                keyword=mosaic_card.get("keyword", ""),
                success=False,
                data={"reason": f"HITL Gate 1: {hitl_decision.value}"},
            )

        keyword = mosaic_card.get("keyword", "unknown")
        thesis_data = {"mosaic_card": mosaic_card}

        # Step 1: Vulnerability scan
        if domain.vulnerability:
            try:
                vuln = domain.vulnerability.scan(keyword, mosaic_card.get("metadata", {}))
                thesis_data["vulnerability"] = vuln.to_dict()
            except Exception as e:
                logger.error(f"[L3] Vulnerability scan error: {e}")
                thesis_data["vulnerability"] = {"error": str(e)}

        # Step 2: Payoff simulation
        if domain.simulator:
            try:
                sim = domain.simulator.simulate(mosaic_card.get("metadata", {}))
                thesis_data["simulation"] = sim.to_dict()
            except Exception as e:
                logger.error(f"[L3] Simulation error: {e}")
                thesis_data["simulation"] = {"error": str(e)}

        # Step 3: Build thesis narrative
        thesis_data["thesis"] = self._build_thesis(keyword, thesis_data)

        return LayerResult(
            layer=3,
            domain=domain.name,
            keyword=keyword,
            success=True,
            data=thesis_data,
            hitl_required=True,  # Gate 2: human validates thesis
        )

    def run_layer4(self, domain: DomainConfig, thesis_data: dict,
                   hitl_decision: HITLDecision = HITLDecision.APPROVE) -> LayerResult:
        """
        Layer 4 — Timing Calibration: Lifecycle assessment + entry window.

        Only runs if HITL Gate 2 validated the thesis.
        """
        if hitl_decision != HITLDecision.APPROVE:
            return LayerResult(
                layer=4, domain=domain.name,
                keyword=thesis_data.get("mosaic_card", {}).get("keyword", ""),
                success=False,
                data={"reason": f"HITL Gate 2: {hitl_decision.value}"},
            )

        keyword = thesis_data.get("mosaic_card", {}).get("keyword", "unknown")
        timing_data = {"thesis": thesis_data}

        if domain.lifecycle:
            try:
                assessment = domain.lifecycle.assess(thesis_data)
                timing_data["lifecycle"] = assessment.to_dict()
            except Exception as e:
                logger.error(f"[L4] Lifecycle error: {e}")
                timing_data["lifecycle"] = {"error": str(e)}

        return LayerResult(
            layer=4,
            domain=domain.name,
            keyword=keyword,
            success=True,
            data=timing_data,
            hitl_required=True,  # Gate 3: human confirms entry timing
        )

    def run_layer5(self, domain: DomainConfig, timing_data: dict,
                   portfolio_value: float,
                   hitl_decision: HITLDecision = HITLDecision.APPROVE,
                   conviction: ConvictionLevel = ConvictionLevel.MEDIUM) -> LayerResult:
        """
        Layer 5 — Conviction Sizing: Position size + decision journal entry.

        Only runs if HITL Gate 3 confirmed entry timing.
        """
        if hitl_decision != HITLDecision.APPROVE:
            keyword = timing_data.get("thesis", {}).get("mosaic_card", {}).get("keyword", "")
            return LayerResult(
                layer=5, domain=domain.name, keyword=keyword,
                success=False,
                data={"reason": f"HITL Gate 3: {hitl_decision.value}"},
            )

        keyword = timing_data.get("thesis", {}).get("mosaic_card", {}).get("keyword", "unknown")
        position_data = {"timing": timing_data}

        if domain.sizer:
            try:
                size = domain.sizer.size(conviction, portfolio_value, timing_data)
                position_data["position"] = size.to_dict()
            except Exception as e:
                logger.error(f"[L5] Sizing error: {e}")
                position_data["position"] = {"error": str(e)}

        # Decision journal entry
        position_data["journal_entry"] = {
            "domain": domain.name,
            "keyword": keyword,
            "conviction": conviction.value,
            "portfolio_value": portfolio_value,
            "timestamp": datetime.utcnow().isoformat(),
            "layers_passed": [1, 2, 3, 4, 5],
            "gates_passed": ["L2→L3", "L3→L4", "L4→L5"],
        }

        return LayerResult(
            layer=5,
            domain=domain.name,
            keyword=keyword,
            success=True,
            data=position_data,
        )

    # ─── Private Helpers ─────────────────────────────────────────────────

    @staticmethod
    def _build_fragments(signals: list[dict]) -> list[MosaicFragment]:
        """Convert raw signal dicts into typed MosaicFragment objects."""
        fragments = []
        for sig in signals:
            growth = sig.get("growth_pct", 0)
            if growth > 50:
                direction = SignalDirection.RISING
            elif growth > 0:
                direction = SignalDirection.STABLE
            elif growth > -20:
                direction = SignalDirection.FALLING
            else:
                direction = SignalDirection.VOLATILE

            fragments.append(MosaicFragment(
                source=sig.get("source", "unknown"),
                direction=direction,
                strength=min(100, abs(growth)),
                change_pct=growth,
                note=sig.get("keyword", ""),
            ))
        return fragments

    @staticmethod
    def _assess_coherence(fragments: list[MosaicFragment]) -> dict:
        """
        Assess whether signal fragments align (all rising) or conflict.

        Coherence scoring:
        - All same direction → 80-100 (highly coherent)
        - Mostly aligned → 50-79 (coherent)
        - Mixed → 25-49 (neutral)
        - Conflicting → 0-24 (conflicted)
        """
        if not fragments:
            return {"score": 0, "label": "no_data"}

        directions = [f.direction for f in fragments]
        rising_count = sum(1 for d in directions if d == SignalDirection.RISING)
        total = len(directions)
        alignment_ratio = rising_count / total

        # Weight by signal strength
        avg_strength = sum(f.strength for f in fragments) / total

        score = alignment_ratio * 70 + (avg_strength / 100) * 30
        score = min(100, max(0, score))

        if score >= 75:
            label = "highly_coherent"
        elif score >= 50:
            label = "coherent"
        elif score >= 25:
            label = "neutral"
        else:
            label = "conflicted"

        return {"score": round(score, 1), "label": label}

    @staticmethod
    def _build_narrative(keyword: str, divergence: Optional[DivergenceResult],
                         score: Optional[ScorerResult], coherence: dict) -> str:
        """Build human-readable narrative for a mosaic card."""
        parts = [f"Mosaic for '{keyword}':"]

        if divergence:
            parts.append(f"Divergence: {divergence.classification} "
                        f"(strength {divergence.signal_strength:.1f}). {divergence.explanation}")

        if score:
            parts.append(f"Quality score: {score.total_score:.0f}/100 ({score.classification}). "
                        f"{score.recommendation}")

        parts.append(f"Coherence: {coherence['score']:.0f}/100 ({coherence['label']}).")

        return " ".join(parts)

    @staticmethod
    def _recommend_action(coherence_score: float,
                          divergence: Optional[DivergenceResult]) -> str:
        """Recommend next action based on mosaic quality."""
        if coherence_score >= 60 and divergence and divergence.classification == "strong":
            return "build_thesis"
        elif coherence_score >= 40:
            return "investigate"
        else:
            return "pass"

    @staticmethod
    def _build_thesis(keyword: str, thesis_data: dict) -> dict:
        """Assemble thesis from vulnerability + simulation data."""
        vuln = thesis_data.get("vulnerability", {})
        sim = thesis_data.get("simulation", {})

        return {
            "keyword": keyword,
            "vulnerability_exploitable": vuln.get("is_exploitable", False),
            "moat_score": vuln.get("moat_score", 5),
            "simulation_verdict": sim.get("verdict", "unknown"),
            "roi_base": sim.get("roi_base", 0),
            "roi_bull": sim.get("roi_bull", 0),
            "risk": sim.get("risk_assessment", "Unknown"),
            "summary": (
                f"Target '{keyword}': "
                f"Moat {vuln.get('moat_score', '?')}/10, "
                f"Exploitable: {vuln.get('is_exploitable', '?')}, "
                f"Simulation: {sim.get('verdict', '?')}, "
                f"ROI base: {sim.get('roi_base', 0):.1f}x, "
                f"ROI bull: {sim.get('roi_bull', 0):.1f}x"
            ),
        }
