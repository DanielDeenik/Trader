"""
Cross-Domain Signal Amplifier

When a signal theme appears across multiple independent domains
(e.g., "AI regulatory risk" appears in GitHub activity, SEC filings, and social media),
it constitutes a stronger mosaic. This engine detects cross-domain convergence
and amplifies confidence accordingly.

Amplification logic:
    - Single domain signal: 1.0x
    - Two independent domains: 1.5x
    - Three+ domains: 2.0x

This implements Chris Camillo's "mosaic tile convergence" principle.
"""

from dataclasses import dataclass
from typing import Dict, List
from social_arb.core.protocols import ScorerResult


@dataclass
class CrossDomainAmplifier:
    """Detect and amplify cross-domain signal convergence."""

    @property
    def domain_name(self) -> str:
        return "cross_domain"

    def score(self, data: dict) -> ScorerResult:
        """
        Score opportunity quality based on cross-domain convergence.

        Args:
            data: {
                "keyword": str,
                "domain_signals": {
                    "public_markets": {
                        "signal_strength": float,  # 0-100
                        "count": int,  # Number of signals
                    },
                    "private_markets": {...},
                    "social_sentiment": {...},
                    "research_agents": {...},  # From research orchestrator
                }
            }

        Returns:
            ScorerResult with amplification bonus applied.
        """
        keyword = data.get("keyword", "unknown")
        domain_signals = data.get("domain_signals", {})

        # Count domains with signals
        domains_with_signals = [
            d for d, signals in domain_signals.items()
            if signals and signals.get("signal_strength", 0) > 0
        ]
        domain_count = len(domains_with_signals)

        # Base amplification factor
        if domain_count >= 3:
            amplification = 2.0
            convergence_label = "highly_converged"
            convergence_detail = (
                f"Signal converges across {domain_count} domains: {', '.join(domains_with_signals)}. "
                "Strong confirmation via independent sources."
            )
        elif domain_count == 2:
            amplification = 1.5
            convergence_label = "converged"
            convergence_detail = (
                f"Signal converges across 2 domains: {', '.join(domains_with_signals)}. "
                "Good cross-domain confirmation."
            )
        elif domain_count == 1:
            amplification = 1.0
            convergence_label = "single_domain"
            convergence_detail = (
                f"Signal isolated to {domains_with_signals[0]}. "
                "Watch for cross-domain confirmation."
            )
        else:
            amplification = 0.5
            convergence_label = "no_signals"
            convergence_detail = "No signals detected across domains."

        # Aggregate signal strength across domains
        total_strength = 0
        signal_breakdown = {}
        for domain, signals in domain_signals.items():
            strength = signals.get("signal_strength", 0)
            signal_breakdown[domain] = strength
            total_strength += strength

        avg_strength = total_strength / max(1, domain_count)
        amplified_strength = avg_strength * amplification
        amplified_strength = min(100, max(0, amplified_strength))

        # Classification
        if amplified_strength >= 75:
            classification = "exceptional"
            recommendation = (
                f"Strong buy signal. Multi-domain convergence confirms thesis. "
                f"Proceed to Layer 3 (asymmetry filter)."
            )
        elif amplified_strength >= 60:
            classification = "strong"
            recommendation = f"Investigate further. Good signal quality. Move to Layer 3."
        elif amplified_strength >= 45:
            classification = "moderate"
            recommendation = (
                f"Monitor. Moderate signal quality. Watch for cross-domain confirmation."
            )
        elif amplified_strength >= 30:
            classification = "weak"
            recommendation = (
                f"Low conviction. Weak signal. Requires significant additional evidence."
            )
        else:
            classification = "negligible"
            recommendation = f"Pass. Insufficient signal strength. {convergence_detail}"

        breakdown = {
            "domain_count": domain_count,
            "domains": domains_with_signals,
            "average_strength": round(avg_strength, 1),
            "amplification_factor": amplification,
            "amplified_strength": round(amplified_strength, 1),
            "convergence_label": convergence_label,
            "signal_breakdown": signal_breakdown,
        }

        return ScorerResult(
            total_score=amplified_strength,
            classification=classification,
            breakdown=breakdown,
            recommendation=(
                f"{recommendation}\n{convergence_detail}"
            ),
        )
