"""
Conviction Scorecard — HITL Decision Support

Camillo's final check before executing — a structured assessment combining all available data.
This is the HITL (Human in the Loop) decision support tool.

Scoring Dimensions (weighted):
- Information Edge (25%): asymmetry_score + source diversity
- Timing (20%): gold_rush stage (best at validating) + catalyst proximity
- Risk/Reward (20%): kelly_fraction + IRR scenarios
- Signal Quality (15%): avg confidence + mosaic coherence
- Virality (10%): STEPPS composite score
- Market Structure (10%): regulatory moat + technical indicators

This engine aggregates outputs from all other engines and generates a conviction score
plus go/no-go recommendation for human review.
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class ConvictionScorer:
    """Generate a structured conviction scorecard for HITL decision-making."""

    def score(
        self,
        signals: List[Dict[str, Any]],
        mosaics: List[Dict[str, Any]],
        theses: List[Dict[str, Any]],
        engine_results: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Generate conviction scorecard from engine results.

        Args:
            signals: List of signal dicts
            mosaics: List of mosaic dicts with coherence_score
            theses: List of thesis dicts
            engine_results: Output from orchestrator containing:
                - sentiment_divergence
                - technical_analyzer
                - kelly_sizer
                - irr_simulator
                - regulatory_moat
                - gold_rush_scorer
                - asymmetry_scanner
                - catalyst_engine
                - stepps_classifier
                - cross_domain_amplifier

        Returns:
            {
                "total_conviction": float,  # 0-100
                "grade": "A"|"B"|"C"|"D"|"F",
                "dimensions": {
                    "information_edge": {"score": float, "weight": 0.25, "rationale": str},
                    "timing": {"score": float, "weight": 0.20, "rationale": str},
                    "risk_reward": {"score": float, "weight": 0.20, "rationale": str},
                    "signal_quality": {"score": float, "weight": 0.15, "rationale": str},
                    "virality": {"score": float, "weight": 0.10, "rationale": str},
                    "market_structure": {"score": float, "weight": 0.10, "rationale": str},
                },
                "go_no_go": "go"|"no_go"|"wait",
                "key_risks": list[str],
                "key_strengths": list[str],
            }
        """
        dimensions = {}

        # 1. Information Edge (25%) — from asymmetry_scanner + sentiment_divergence
        info_edge_score, info_edge_rationale = self._score_information_edge(engine_results)
        dimensions["information_edge"] = {
            "score": info_edge_score,
            "weight": 0.25,
            "rationale": info_edge_rationale,
        }

        # 2. Timing (20%) — from gold_rush_scorer + catalyst_engine
        timing_score, timing_rationale = self._score_timing(engine_results)
        dimensions["timing"] = {
            "score": timing_score,
            "weight": 0.20,
            "rationale": timing_rationale,
        }

        # 3. Risk/Reward (20%) — from kelly_sizer + irr_simulator
        risk_reward_score, risk_reward_rationale = self._score_risk_reward(engine_results, theses)
        dimensions["risk_reward"] = {
            "score": risk_reward_score,
            "weight": 0.20,
            "rationale": risk_reward_rationale,
        }

        # 4. Signal Quality (15%) — from signal average confidence + mosaic coherence
        signal_quality_score, signal_quality_rationale = self._score_signal_quality(
            signals, mosaics, engine_results
        )
        dimensions["signal_quality"] = {
            "score": signal_quality_score,
            "weight": 0.15,
            "rationale": signal_quality_rationale,
        }

        # 5. Virality (10%) — from stepps_classifier
        virality_score, virality_rationale = self._score_virality(engine_results)
        dimensions["virality"] = {
            "score": virality_score,
            "weight": 0.10,
            "rationale": virality_rationale,
        }

        # 6. Market Structure (10%) — from regulatory_moat + technical_analyzer
        market_structure_score, market_structure_rationale = self._score_market_structure(
            engine_results
        )
        dimensions["market_structure"] = {
            "score": market_structure_score,
            "weight": 0.10,
            "rationale": market_structure_rationale,
        }

        # Calculate weighted total conviction (0-100 scale)
        total_conviction = (
            (dimensions["information_edge"]["score"] * 0.25)
            + (dimensions["timing"]["score"] * 0.20)
            + (dimensions["risk_reward"]["score"] * 0.20)
            + (dimensions["signal_quality"]["score"] * 0.15)
            + (dimensions["virality"]["score"] * 0.10)
            + (dimensions["market_structure"]["score"] * 0.10)
        )

        # Grade assignment
        grade = self._assign_grade(total_conviction)

        # Go/No-Go determination
        go_no_go = self._determine_go_no_go(total_conviction, dimensions)

        # Extract key risks and strengths
        key_risks = self._identify_key_risks(dimensions, engine_results)
        key_strengths = self._identify_key_strengths(dimensions, engine_results)

        return {
            "total_conviction": round(total_conviction, 1),
            "grade": grade,
            "dimensions": dimensions,
            "go_no_go": go_no_go,
            "key_risks": key_risks,
            "key_strengths": key_strengths,
        }

    def _score_information_edge(self, engine_results: Dict[str, Any]) -> tuple[float, str]:
        """Score information edge: asymmetry + sentiment divergence."""
        asymmetry = engine_results.get("asymmetry_scanner", {})
        divergence = engine_results.get("sentiment_divergence", {})

        asym_score = float(asymmetry.get("asymmetry_score", 0.0)) * 100
        div_strength = float(divergence.get("signal_strength", 0.0))
        div_class = divergence.get("classification", "pass")

        # Map classification to score
        div_map = {"strong": 80, "monitor": 50, "pass": 20}
        div_score = div_map.get(div_class, 20)

        # Thesis: "retail_ahead" is best for asymmetry
        thesis = asymmetry.get("thesis", "no_signal")
        thesis_boost = 30 if thesis == "retail_ahead" else 0 if thesis == "aligned" else 15

        final_score = (asym_score * 0.5) + (div_score * 0.35) + thesis_boost
        final_score = min(100, max(0, final_score))

        rationale = f"Asymmetry: {thesis} (score {asym_score:.0f}), Divergence: {div_class} (score {div_score:.0f})"

        return final_score, rationale

    def _score_timing(self, engine_results: Dict[str, Any]) -> tuple[float, str]:
        """Score timing: gold_rush stage + catalyst proximity."""
        gold_rush = engine_results.get("gold_rush_scorer", {})
        catalyst = engine_results.get("catalyst_engine", {})

        stage = gold_rush.get("stage", "emerging")
        stage_score = float(gold_rush.get("stage_score", 0.0)) * 100

        # Best timing is validating stage
        stage_boost = {"validating": 30, "confirmed": 15, "emerging": 20, "saturated": -20}
        stage_timing = stage_boost.get(stage, 0)

        # Catalyst proximity: more catalysts = better timing
        catalyst_count = len(catalyst.get("catalysts", []))
        catalyst_score = min(30, catalyst_count * 10)

        final_score = stage_score + stage_timing + (catalyst_score * 0.3)
        final_score = min(100, max(0, final_score))

        rationale = f"Stage: {stage} ({stage_score:.0f}), Catalysts: {catalyst_count} detected"

        return final_score, rationale

    def _score_risk_reward(
        self, engine_results: Dict[str, Any], theses: List[Dict[str, Any]]
    ) -> tuple[float, str]:
        """Score risk/reward: kelly_sizer + irr_simulator."""
        kelly = engine_results.get("kelly_sizer", {})
        irr = engine_results.get("irr_simulator", {})

        # Kelly fraction (0.0 to 0.05 range typically, up to 1.0 in extreme cases)
        kelly_fraction = float(kelly.get("kelly_fraction", 0.0))
        kelly_score = min(100, kelly_fraction * 500)  # Scale: 0.05 kelly = 25, 0.10 kelly = 50

        # IRR scenarios
        roi_bear = float(irr.get("roi_bear", -0.1))
        roi_base = float(irr.get("roi_base", 0.0))
        roi_bull = float(irr.get("roi_bull", 0.0))

        # Asymmetric payoff: upside >> downside
        upside = max(0, roi_bull * 100)
        downside = abs(min(0, roi_bear * 100))
        asymmetry = upside - downside if downside > 0 else upside

        irr_score = min(100, (roi_base * 100 + asymmetry * 0.5))

        final_score = (kelly_score * 0.4) + (irr_score * 0.6)
        final_score = min(100, max(0, final_score))

        rationale = f"Kelly: {kelly_fraction:.2%}, IRR: {roi_base:+.1%} base / {roi_bull:+.1%} bull"

        return final_score, rationale

    def _score_signal_quality(
        self, signals: List[Dict[str, Any]], mosaics: List[Dict[str, Any]], engine_results: Dict[str, Any]
    ) -> tuple[float, str]:
        """Score signal quality: avg confidence + mosaic coherence."""
        if not signals:
            return 20.0, "No signals"

        # Average signal confidence
        confidences = [float(s.get("confidence", 0.5)) for s in signals if s.get("confidence")]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.5
        confidence_score = avg_confidence * 100

        # Mosaic coherence
        coherence_scores = [float(m.get("coherence_score", 50)) for m in mosaics if m.get("coherence_score")]
        avg_coherence = sum(coherence_scores) / len(coherence_scores) if coherence_scores else 50
        coherence_score = min(100, avg_coherence)  # Already 0-100

        # Signal count quality
        signal_count = len(signals)
        count_score = min(30, signal_count / 2)  # 20 signals = 30 points max

        final_score = (confidence_score * 0.4) + (coherence_score * 0.4) + count_score
        final_score = min(100, final_score)

        rationale = f"Confidence: {avg_confidence:.0%}, Coherence: {avg_coherence:.0f}/100, Count: {signal_count}"

        return final_score, rationale

    def _score_virality(self, engine_results: Dict[str, Any]) -> tuple[float, str]:
        """Score virality: STEPPS classifier composite."""
        stepps = engine_results.get("stepps_classifier", {})

        avg_composite = float(stepps.get("avg_composite", 0.5))
        composite_score = avg_composite * 100

        signal_count = len(stepps.get("scores", []))
        count_boost = min(30, signal_count / 5)  # More signals scored = higher virality potential

        final_score = composite_score * 0.7 + count_boost * 0.3
        final_score = min(100, final_score)

        rationale = f"STEPPS avg: {avg_composite:.2f}, Signals scored: {signal_count}"

        return final_score, rationale

    def _score_market_structure(self, engine_results: Dict[str, Any]) -> tuple[float, str]:
        """Score market structure: regulatory moat + technical indicators."""
        moat = engine_results.get("regulatory_moat", {})
        technical = engine_results.get("technical_analyzer", {})

        # Moat score
        moat_score = float(moat.get("moat_score", 5)) / 10 * 100  # 1-10 scale -> 0-100

        # Technical indicators: check for bullish signals
        indicators = technical.get("indicators", {})
        technical_score = self._evaluate_technical_indicators(indicators)

        # Cross-domain amplifier
        amplifier = engine_results.get("cross_domain_amplifier", {})
        amplifier_score = float(amplifier.get("amplification_score", 0.5)) * 100

        final_score = (moat_score * 0.3) + (technical_score * 0.4) + (amplifier_score * 0.3)
        final_score = min(100, max(0, final_score))

        rationale = f"Moat: {moat_score:.0f}, Technical: {technical_score:.0f}, Amplifier: {amplifier_score:.0f}"

        return final_score, rationale

    def _evaluate_technical_indicators(self, indicators: Dict[str, Any]) -> float:
        """Score technical indicators for bullishness."""
        score = 50.0  # Neutral default

        # RSI: 40-60 is neutral, >60 is bullish, <40 is bearish
        rsi = float(indicators.get("rsi", 50))
        if 40 < rsi < 70:
            score += 10
        elif rsi >= 70:
            score += 5  # Overbought

        # MACD: positive histogram is bullish
        macd_histogram = float(indicators.get("macd_histogram", 0))
        if macd_histogram > 0:
            score += 10

        # Bollinger Bands: price near upper band is bullish
        bb_position = indicators.get("bb_position")
        if bb_position == "upper":
            score += 5
        elif bb_position == "lower":
            score -= 5

        # SMA/EMA crossover: price above EMA is bullish
        price = float(indicators.get("close", 0))
        ema = float(indicators.get("ema_12", 0))
        if ema > 0 and price > ema * 0.98:
            score += 10

        return min(100, max(0, score))

    def _assign_grade(self, conviction: float) -> str:
        """Assign letter grade based on conviction score."""
        if conviction >= 80:
            return "A"
        elif conviction >= 70:
            return "B"
        elif conviction >= 60:
            return "C"
        elif conviction >= 50:
            return "D"
        else:
            return "F"

    def _determine_go_no_go(self, conviction: float, dimensions: Dict[str, Any]) -> str:
        """Determine go/no-go/wait decision."""
        info_edge = dimensions["information_edge"]["score"]
        timing = dimensions["timing"]["score"]
        risk_reward = dimensions["risk_reward"]["score"]

        # All three pillars must be reasonable
        if conviction < 50:
            return "no_go"
        elif conviction < 60 or info_edge < 40:
            return "wait"
        elif conviction >= 70 and info_edge >= 60 and timing >= 60:
            return "go"
        else:
            return "wait"

    def _identify_key_risks(self, dimensions: Dict[str, Any], engine_results: Dict[str, Any]) -> List[str]:
        """Identify key risks from weak dimensions."""
        risks = []

        for dim_name, dim_data in dimensions.items():
            if dim_data["score"] < 40:
                risk_map = {
                    "information_edge": "Limited information asymmetry; market may already be pricing signals",
                    "timing": "Poor timing; stage may be too early or saturated",
                    "risk_reward": "Unfavorable risk/reward profile; downside risk exceeds upside",
                    "signal_quality": "Low signal quality; insufficient conviction",
                    "virality": "Low virality potential; limited spread",
                    "market_structure": "Weak moat; vulnerable to competition",
                }
                risks.append(risk_map.get(dim_name, f"Weak {dim_name}"))

        return risks[:3]  # Top 3 risks

    def _identify_key_strengths(self, dimensions: Dict[str, Any], engine_results: Dict[str, Any]) -> List[str]:
        """Identify key strengths from strong dimensions."""
        strengths = []

        for dim_name, dim_data in dimensions.items():
            if dim_data["score"] > 70:
                strength_map = {
                    "information_edge": "Strong information asymmetry; retail ahead of market",
                    "timing": "Excellent timing; validating stage with catalysts approaching",
                    "risk_reward": "Favorable risk/reward; asymmetric upside",
                    "signal_quality": "High-quality signals; high confidence and coherence",
                    "virality": "High virality potential; strong social signal",
                    "market_structure": "Strong moat; structural advantages",
                }
                strengths.append(strength_map.get(dim_name, f"Strong {dim_name}"))

        return strengths[:3]  # Top 3 strengths
