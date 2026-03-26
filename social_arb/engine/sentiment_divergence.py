"""
Sentiment Divergence Engine (Data-Driven)

Measures divergence between crowd sentiment (social media, forums) and
institutional positioning (SEC filings, fund flows). A strong divergence
suggests information asymmetry — an exploitable opportunity.

Formula:
    Signal Strength = (Social Sentiment Growth % - Institutional Positioning Growth %)

Classification:
    - strong: >30% divergence
    - monitor: 15-30%
    - pass: <15%

This version is fully data-driven, accepting real signal data rather than hardcoded values.
"""

from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from social_arb.core.protocols import DomainDivergence, DivergenceResult


@dataclass
class SentimentDivergenceCalculator:
    """Calculate divergence between crowd and institutional positioning."""

    @property
    def domain_name(self) -> str:
        return "sentiment_divergence"

    def calculate(self, signal_data: dict, market_data: dict) -> DivergenceResult:
        """
        Calculate sentiment divergence from real data.

        Args:
            signal_data: {
                "growth_pct": float,      # Social sentiment growth %
                "volume": int,            # Number of mentions/signals
                "sources": List[str],     # Where signals come from
                "trend": str,             # "rising" | "falling" | "stable"
            }
            market_data: {
                "price_change_pct": float,        # Market price change %
                "institutional_growth_pct": float, # Institutional positioning change %
                "volume": int,                     # Trading volume or similar
                "days_lookback": int,              # Period analyzed
            }

        Returns:
            DivergenceResult with classification and strength (real data-driven).
        """
        # Extract social sentiment data (handle missing data gracefully)
        social_growth = signal_data.get("growth_pct", 0)
        social_volume = signal_data.get("volume", 0)
        social_sources = signal_data.get("sources", [])

        # Extract market/institutional data
        price_change = market_data.get("price_change_pct", 0)
        institutional_growth = market_data.get("institutional_growth_pct", 0)
        market_volume = market_data.get("volume", 0)
        lookback_days = market_data.get("days_lookback", 30)

        # Raw divergence: how much more is the crowd interested than institutions?
        # Use institutional growth as baseline, compare against social sentiment
        raw_divergence = social_growth - institutional_growth

        # Volume-weighted signal strength (higher volume = stronger signal)
        volume_factor = min(1.0, social_volume / max(1, 100))  # Normalize to 100 base
        signal_strength = raw_divergence * (0.7 + 0.3 * volume_factor)

        # Adjust for source diversity (multiple sources = more reliable)
        source_diversity = min(1.2, 1.0 + (len(social_sources) / 10))
        signal_strength = signal_strength * source_diversity

        # Classification thresholds
        abs_divergence = abs(signal_strength)

        if abs_divergence >= 30:
            classification = "strong"
            confidence = min(0.95, 0.6 + (abs_divergence / 100))
            explanation = (
                f"STRONG divergence detected: Social sentiment growth {social_growth:+.1f}% "
                f"vs institutional positioning {institutional_growth:+.1f}% "
                f"(price change: {price_change:+.1f}%). "
                f"Signal volume: {social_volume} mentions across {len(social_sources)} sources. "
                f"Potential information asymmetry with crowd {abs(raw_divergence):.1f}ppt ahead."
            )
        elif abs_divergence >= 15:
            classification = "monitor"
            confidence = min(0.75, 0.4 + (abs_divergence / 100))
            explanation = (
                f"MODERATE divergence: Social sentiment {social_growth:+.1f}% "
                f"vs institutional positioning {institutional_growth:+.1f}% "
                f"(price change: {price_change:+.1f}%). "
                f"Volume: {social_volume} signals. "
                f"Monitor for institutional catch-up or crowd reversal."
            )
        else:
            classification = "pass"
            confidence = max(0.2, (30 - abs_divergence) / 100)
            explanation = (
                f"WEAK divergence: Social sentiment {social_growth:+.1f}% "
                f"aligns with institutional positioning {institutional_growth:+.1f}% "
                f"(price change: {price_change:+.1f}%). "
                f"Limited information asymmetry. "
                f"Insufficient signal for independent trade thesis."
            )

        return DivergenceResult(
            signal_strength=round(signal_strength, 2),
            classification=classification,
            primary_metric=social_growth,
            counter_metric=institutional_growth,
            explanation=explanation,
        )
