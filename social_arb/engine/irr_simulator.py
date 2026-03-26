"""
IRR/MOIC Simulator for Private Markets

Simulates bear/base/bull scenarios for private market investments using
IRR (Internal Rate of Return) and MOIC (Multiple on Invested Capital).

Typical expectations:
    - Early stage (seed/Series A): 3-10x MOIC over 7-10 years
    - Growth stage (Series C+): 2-5x MOIC over 5-7 years
    - Bear case: 0.5-1.0x (loss or flat)
    - Base case: 2-3x
    - Bull case: 5-10x+

Reference: Paul Graham's "How to Succeed as an Angel Investor"
"""

import math
from dataclasses import dataclass
from typing import Optional
from social_arb.core.protocols import DomainSimulator, SimulationOutput


@dataclass
class IRRMOICSim:
    """Simulate IRR/MOIC for private market investments."""

    exit_year: int = 7  # Assumed exit in 7 years

    @property
    def domain_name(self) -> str:
        return "irr_moic"

    def simulate(self, params: dict) -> SimulationOutput:
        """
        Simulate bear/base/bull scenarios.

        Args:
            params: {
                "initial_investment": float,  # Entry investment amount
                "stage": str,  # "seed", "series_a", "series_b", "series_c", "growth"
                "sector": str,  # "ai", "biotech", "fintech", etc.
                "team_score": int,  # 1-10
                "market_size_score": int,  # 1-10
                "moat_score": int,  # 1-10 (from vulnerability engine)
            }

        Returns:
            SimulationOutput with bear/base/bull scenarios.
        """
        initial = params.get("initial_investment", 100000)
        stage = params.get("stage", "series_a").lower()
        sector = params.get("sector", "general").lower()
        team_score = params.get("team_score", 7)
        market_size_score = params.get("market_size_score", 7)
        moat_score = params.get("moat_score", 5)

        # Stage-based MOIC ranges
        stage_ranges = {
            "seed": {"bear": 0.5, "base": 2.5, "bull": 8.0},
            "series_a": {"bear": 0.6, "base": 3.0, "bull": 7.0},
            "series_b": {"bear": 0.8, "base": 2.5, "bull": 5.0},
            "series_c": {"bear": 0.9, "base": 2.0, "bull": 4.0},
            "growth": {"bear": 0.95, "base": 1.8, "bull": 3.0},
        }
        ranges = stage_ranges.get(stage, stage_ranges["series_a"])

        # Adjust by team quality (higher team = higher upside, lower downside risk)
        team_factor = 0.9 + (team_score / 50)  # 0.9 to 1.1x

        # Adjust by market size (larger = better bull case, but lower moat risk)
        market_factor = 0.95 + (market_size_score / 100)  # 0.95 to 1.05x

        # Adjust by moat (stronger moat = higher base, lower bear downside)
        moat_factor = 0.8 + (moat_score / 50)  # 0.8 to 1.0x (capped at 1.0)
        moat_factor = min(1.0, moat_factor)

        # Sector boosts (AI is hot, biotech is risky)
        sector_boosts = {
            "ai": 1.15,
            "biotech": 0.95,
            "fintech": 1.05,
            "enterprise": 0.95,
            "consumer": 1.0,
            "general": 1.0,
        }
        sector_boost = sector_boosts.get(sector, 1.0)

        # Calculate MOIC scenarios
        base_moic = ranges["base"] * team_factor * market_factor * moat_factor * sector_boost
        bear_moic = max(0.3, ranges["bear"] * moat_factor * 0.8)  # Moat helps in downside
        bull_moic = ranges["bull"] * team_factor * market_factor * sector_boost

        # Convert MOIC to IRR
        def moic_to_irr(moic: float, years: int) -> float:
            """Convert MOIC to IRR: IRR = (MOIC ^ (1/years)) - 1"""
            if moic <= 0:
                return -1.0
            return (moic ** (1 / years)) - 1

        bear_irr = moic_to_irr(bear_moic, self.exit_year)
        base_irr = moic_to_irr(base_moic, self.exit_year)
        bull_irr = moic_to_irr(bull_moic, self.exit_year)

        # Scenario narratives
        bear_case = {
            "name": "Bear Case",
            "moic": round(bear_moic, 2),
            "irr": round(bear_irr * 100, 1),
            "description": (
                f"Market adoption slower than expected. "
                f"{bear_moic:.1f}x MOIC ({bear_irr*100:.0f}% IRR over {self.exit_year}y)."
            ),
        }

        base_case = {
            "name": "Base Case",
            "moic": round(base_moic, 2),
            "irr": round(base_irr * 100, 1),
            "description": (
                f"Execution on plan. {base_moic:.1f}x MOIC ({base_irr*100:.0f}% IRR over {self.exit_year}y). "
                f"Stage: {stage.upper()}, Team: {team_score}/10, Market: {market_size_score}/10."
            ),
        }

        bull_case = {
            "name": "Bull Case",
            "moic": round(bull_moic, 2),
            "irr": round(bull_irr * 100, 1),
            "description": (
                f"Explosive growth + market expansion. "
                f"{bull_moic:.1f}x MOIC ({bull_irr*100:.0f}% IRR over {self.exit_year}y). "
                f"{sector.upper()} sector tailwinds."
            ),
        }

        # Verdict logic
        if base_irr >= 0.35:  # 35% IRR threshold
            verdict = "proceed"
            risk_assessment = "Attractive risk/reward. Base case IRR exceeds 35% hurdle."
        elif base_irr >= 0.20:  # 20% IRR threshold
            verdict = "proceed_with_caution"
            risk_assessment = "Moderate risk/reward. Base case meets minimum hurdle."
        elif bear_irr >= 0.0:
            verdict = "monitor"
            risk_assessment = "Marginal. Bear case is breakeven; requires strong execution."
        else:
            verdict = "pass"
            risk_assessment = "Poor risk/reward. Bear case is a significant loss."

        return SimulationOutput(
            bear_case=bear_case,
            base_case=base_case,
            bull_case=bull_case,
            verdict=verdict,
            roi_base=base_irr,
            roi_bull=bull_irr,
            risk_assessment=risk_assessment,
        )
