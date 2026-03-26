"""Tests for investment engines."""

import pytest
from social_arb.engine.sentiment_divergence import SentimentDivergenceCalculator
from social_arb.engine.kelly_sizer import KellyCriterionSizer
from social_arb.engine.irr_simulator import IRRMOICSim
from social_arb.engine.regulatory_moat import RegulatoryMoatScorer
from social_arb.engine.cross_domain_amplifier import CrossDomainAmplifier
from social_arb.core.protocols import ConvictionLevel


class TestSentimentDivergence:
    """Test sentiment divergence engine."""

    def test_strong_divergence(self):
        """Test strong divergence detection."""
        calc = SentimentDivergenceCalculator()
        result = calc.calculate(
            signal_data={"growth_pct": 60.0, "volume": 500},
            market_data={"institutional_growth_pct": 10.0},
        )

        assert result.classification == "strong"
        assert result.signal_strength > 30
        assert result.primary_metric == 60.0

    def test_weak_divergence(self):
        """Test weak divergence detection."""
        calc = SentimentDivergenceCalculator()
        result = calc.calculate(
            signal_data={"growth_pct": 15.0, "volume": 100},
            market_data={"institutional_growth_pct": 10.0},
        )

        assert result.classification == "pass"
        assert result.signal_strength < 15

    def test_monitor_divergence(self):
        """Test moderate divergence detection."""
        calc = SentimentDivergenceCalculator()
        result = calc.calculate(
            signal_data={"growth_pct": 25.0, "volume": 50},
            market_data={"institutional_growth_pct": 5.0},
        )

        assert result.classification == "monitor"
        assert 15 <= result.signal_strength < 30


class TestKellyCriterionSizer:
    """Test Kelly Criterion position sizer."""

    def test_kelly_sizing_high_conviction(self):
        """Test position sizing with high conviction."""
        sizer = KellyCriterionSizer(safety_factor=0.25)
        position = sizer.size(
            conviction=ConvictionLevel.HIGH,
            portfolio_value=100000,
            params={
                "roi_base": 0.20,
                "roi_bull": 0.50,
                "roi_bear": -0.15,
                "probability_base": 0.60,
                "probability_bull": 0.25,
                "probability_bear": 0.15,
            },
        )

        assert position.allocation > 0
        assert position.conviction == ConvictionLevel.HIGH
        assert position.take_profit > position.allocation
        assert position.stop_loss < position.allocation

    def test_kelly_sizing_low_conviction(self):
        """Test position sizing with low conviction."""
        sizer = KellyCriterionSizer(safety_factor=0.25)
        position = sizer.size(
            conviction=ConvictionLevel.LOW,
            portfolio_value=100000,
            params={
                "roi_base": 0.15,
                "roi_bull": 0.40,
                "roi_bear": -0.20,
            },
        )

        assert position.allocation > 0
        assert position.conviction == ConvictionLevel.LOW
        assert position.allocation < 5000  # Low conviction = small size

    def test_kelly_sizing_cap(self):
        """Test that Kelly sizing is capped at 5% of portfolio."""
        sizer = KellyCriterionSizer(safety_factor=0.25)
        position = sizer.size(
            conviction=ConvictionLevel.HIGH,
            portfolio_value=100000,
            params={
                "roi_base": 5.0,  # Extreme return
                "roi_bull": 10.0,
                "roi_bear": -0.5,
            },
        )

        assert position.allocation <= 5000  # Max 5% of 100k


class TestIRRMOICSim:
    """Test IRR/MOIC simulator."""

    def test_seed_stage_simulation(self):
        """Test seed-stage scenario simulation."""
        sim = IRRMOICSim(exit_year=7)
        output = sim.simulate(
            params={
                "initial_investment": 100000,
                "stage": "seed",
                "sector": "ai",
                "team_score": 8,
                "market_size_score": 8,
                "moat_score": 6,
            }
        )

        assert output.bear_case["moic"] > 0.3
        assert output.base_case["moic"] > output.bear_case["moic"]
        assert output.bull_case["moic"] > output.base_case["moic"]
        assert output.verdict in ["proceed", "proceed_with_caution", "monitor", "pass"]

    def test_growth_stage_simulation(self):
        """Test growth-stage scenario simulation."""
        sim = IRRMOICSim(exit_year=5)
        output = sim.simulate(
            params={
                "initial_investment": 1000000,
                "stage": "growth",
                "sector": "fintech",
                "team_score": 7,
                "market_size_score": 7,
                "moat_score": 5,
            }
        )

        # Growth stage has lower multiples
        assert output.base_case["moic"] < 3.0
        assert output.base_case["irr"] < 50

    def test_high_moat_seed(self):
        """Test seed with strong moat."""
        sim = IRRMOICSim(exit_year=7)
        output = sim.simulate(
            params={
                "stage": "seed",
                "team_score": 9,
                "market_size_score": 9,
                "moat_score": 9,  # Very strong moat
            }
        )

        # Strong moat = lower downside (but still reasonable for seed)
        assert output.bear_case["moic"] > 0.3  # Seed bear case is ~0.5-0.7x


class TestRegulatoryMoatScorer:
    """Test regulatory moat scorer."""

    def test_strong_moat(self):
        """Test company with strong regulatory moat."""
        scorer = RegulatoryMoatScorer()
        result = scorer.scan(
            "ESGExcellent Corp",
            {
                "esg_score": 85,
                "carbon_intensity": 2.0,
                "patent_count": 120,
                "regulatory_burden_score": 8,
                "institutional_ownership_pct": 75,
                "csrd_compliant": True,
                "carbon_reporting": True,
            },
        )

        assert result.moat_score >= 8
        assert result.vulnerability_type == "strong_moat"
        assert not result.is_exploitable

    def test_weak_moat(self):
        """Test company with weak regulatory moat."""
        scorer = RegulatoryMoatScorer()
        result = scorer.scan(
            "NonCompliant Inc",
            {
                "esg_score": 30,
                "carbon_intensity": 25.0,
                "patent_count": 2,
                "regulatory_burden_score": 8,
                "institutional_ownership_pct": 10,
                "csrd_compliant": False,
                "carbon_reporting": False,
            },
        )

        assert result.moat_score <= 5
        assert result.vulnerability_type == "weak_moat"
        assert result.is_exploitable

    def test_compliance_bonus(self):
        """Test CSRD compliance bonus."""
        scorer = RegulatoryMoatScorer()

        # Non-compliant baseline
        result1 = scorer.scan(
            "Baseline",
            {"esg_score": 50, "csrd_compliant": False, "carbon_reporting": False},
        )

        # Compliant version
        result2 = scorer.scan(
            "Compliant",
            {"esg_score": 50, "csrd_compliant": True, "carbon_reporting": True},
        )

        # Compliant should have higher moat
        assert result2.moat_score > result1.moat_score


class TestCrossDomainAmplifier:
    """Test cross-domain signal amplifier."""

    def test_single_domain_signal(self):
        """Test signal from single domain."""
        amp = CrossDomainAmplifier()
        result = amp.score(
            {
                "keyword": "AI Chips",
                "domain_signals": {
                    "github_activity": {"signal_strength": 80},
                },
            }
        )

        assert result.total_score <= 80  # No amplification
        assert result.breakdown["amplification_factor"] == 1.0

    def test_two_domain_convergence(self):
        """Test signal converging across 2 domains."""
        amp = CrossDomainAmplifier()
        result = amp.score(
            {
                "keyword": "AI Chips",
                "domain_signals": {
                    "github_activity": {"signal_strength": 70},
                    "patent_activity": {"signal_strength": 75},
                },
            }
        )

        assert result.breakdown["amplification_factor"] == 1.5
        assert result.breakdown["domain_count"] == 2
        assert result.classification in ["strong", "exceptional"]

    def test_three_domain_convergence(self):
        """Test strong signal converging across 3+ domains."""
        amp = CrossDomainAmplifier()
        result = amp.score(
            {
                "keyword": "Quantum Computing",
                "domain_signals": {
                    "github_activity": {"signal_strength": 85},
                    "patent_activity": {"signal_strength": 80},
                    "sec_edgar": {"signal_strength": 75},
                },
            }
        )

        assert result.breakdown["amplification_factor"] == 2.0
        assert result.breakdown["domain_count"] == 3
        assert result.classification == "exceptional"
        # Average 80, capped at 100 (max score)
        assert result.breakdown["amplified_strength"] == 100


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
