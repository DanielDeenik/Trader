"""
Kelly Criterion Position Sizer (Data-Driven)

Implements the Kelly Criterion for optimal position sizing using real historical data.

Kelly Fraction = (bp - q) / b
where:
    b = odds offered (return multiplier)
    p = probability of winning
    q = 1 - p (probability of losing)

We apply a 0.25 Kelly safety factor to reduce volatility.

This version calculates win rate from real signal history rather than assuming parameters.

Reference: Ed Thorp's work on optimal f in portfolio management.
"""

from social_arb.core.protocols import (
    DomainSizer, PositionSize, ConvictionLevel
)
from dataclasses import dataclass
from typing import List, Dict, Optional


@dataclass
class KellyCriterionSizer:
    """Size positions using Kelly Criterion with real historical data."""

    safety_factor: float = 0.25  # Conservative 25% Kelly
    max_allocation_pct: float = 0.05  # Max 5% of portfolio per position

    @property
    def domain_name(self) -> str:
        return "kelly_criterion"

    def size(
        self,
        conviction: ConvictionLevel,
        portfolio_value: float,
        params: dict
    ) -> PositionSize:
        """
        Size position using Kelly Criterion with real data.

        Args:
            conviction: HIGH/MEDIUM/LOW/WATCH
            portfolio_value: Total portfolio value in currency
            params: {
                # Simulation scenarios
                "roi_base": float,          # Expected return in base case
                "roi_bull": float,          # Return in bull case
                "roi_bear": float,          # Return in bear case (often negative)
                "probability_base": float,  # Probability of base case (0-1) [optional, default 0.6]
                "probability_bull": float,  # Probability of bull case [optional, default 0.25]
                "probability_bear": float,  # Probability of bear case [optional, default 0.15]

                # OR historical win rate data
                "historical_wins": int,     # Number of winning trades
                "historical_total": int,    # Total number of trades
                "avg_win": float,           # Average win amount
                "avg_loss": float,          # Average loss amount

                # Position context
                "existing_positions": List[float],  # Current position sizes [optional]
                "symbol": str,              # Position identifier [optional]
            }

        Returns:
            PositionSize with Kelly-derived allocation using real data.
        """
        # Try to use historical win rate first
        historical_wins = params.get("historical_wins")
        historical_total = params.get("historical_total")

        if historical_wins is not None and historical_total and historical_total > 0:
            # Use real historical data
            p_win = historical_wins / historical_total
            avg_win = params.get("avg_win", 0.15)
            avg_loss = abs(params.get("avg_loss", -0.10))

            # Kelly from historical data: f* = (p * avg_win - (1-p) * avg_loss) / avg_win
            if avg_win > 0:
                kelly_fraction = (p_win * avg_win - (1 - p_win) * avg_loss) / avg_win
            else:
                kelly_fraction = 0

            expected_return = p_win * avg_win - (1 - p_win) * avg_loss
            roi_base = avg_win
            roi_bull = avg_win * 2
            roi_bear = -avg_loss

        else:
            # Fall back to scenario-based probabilities
            prob_base = params.get("probability_base", 0.60)
            prob_bull = params.get("probability_bull", 0.25)
            prob_bear = params.get("probability_bear", 0.15)

            # Normalize probabilities
            total_prob = prob_base + prob_bull + prob_bear
            if total_prob > 0:
                prob_base /= total_prob
                prob_bull /= total_prob
                prob_bear /= total_prob

            # Extract returns
            roi_base = params.get("roi_base", 0.15)
            roi_bull = params.get("roi_bull", 0.50)
            roi_bear = params.get("roi_bear", -0.20)

            expected_return = prob_base * roi_base + prob_bull * roi_bull + prob_bear * roi_bear

            # Win probability (base + bull cases)
            p_win = prob_base + prob_bull

            if p_win <= 0 or p_win >= 1.0:
                kelly_fraction = 0
            else:
                # Kelly Criterion: f* = (bp - q) / b
                b = max(0.1, abs(expected_return) / max(0.01, abs(roi_bear)))
                kelly_fraction = (b * p_win - (1 - p_win)) / max(0.1, b)

        # Apply safety factor (fractional Kelly)
        kelly_fraction = kelly_fraction * self.safety_factor

        # Cap Kelly fraction at max allocation
        kelly_fraction = max(0, min(self.max_allocation_pct, kelly_fraction))

        # Adjust by conviction level
        conviction_multiplier = {
            ConvictionLevel.HIGH: 1.0,
            ConvictionLevel.MEDIUM: 0.75,
            ConvictionLevel.LOW: 0.50,
            ConvictionLevel.WATCH: 0.25,
        }
        kelly_fraction *= conviction_multiplier.get(conviction, 0.5)

        # Consider existing positions (avoid over-concentration)
        existing_positions = params.get("existing_positions", [])
        total_existing = sum(existing_positions) if existing_positions else 0
        available_capacity = max(0, 0.3 - total_existing / portfolio_value)  # 30% max in growth
        kelly_fraction = min(kelly_fraction, available_capacity)

        # Allocation in currency
        allocation = portfolio_value * kelly_fraction

        # Stop loss: at bear case loss
        stop_loss = max(0, allocation * (1 + roi_bear))

        # Take profit: at bull case return
        take_profit = allocation * (1 + roi_bull)

        symbol = params.get("symbol", "unknown")
        hist_note = ""
        if historical_wins is not None and historical_total:
            hist_note = f" (from {historical_wins}/{historical_total} historical trades)"

        rationale = (
            f"Kelly sizing ({kelly_fraction*100:.2f}% of portfolio{hist_note}). "
            f"Win prob: {p_win*100:.0f}%, Expected ROI: {expected_return*100:+.1f}%. "
            f"Scenarios: Bull +{roi_bull*100:.0f}% | Base {roi_base*100:+.0f}% | Bear {roi_bear*100:.0f}%."
        )

        return PositionSize(
            allocation=allocation,
            allocation_type="currency",
            conviction=conviction,
            stop_loss=stop_loss,
            take_profit=take_profit,
            rationale=rationale,
        )
