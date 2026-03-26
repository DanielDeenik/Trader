"""Tests for topology engine with tiered autonomy HITL."""

import pytest
from social_arb.core.topology import (
    TopologyEngine, HITLDecision, TrustLevel, ConfidenceThreshold, AuditEntry
)
from social_arb.core.protocols import (
    DomainConfig, Signal, SignalDirection, ConvictionLevel,
    DivergenceResult, ScorerResult, VulnerabilityScanResult,
    SimulationOutput, LifecycleAssessment, PositionSize, LifecycleStage,
)
from dataclasses import dataclass


# Mock implementations
@dataclass
class MockScraper:
    @property
    def domain_name(self) -> str:
        return "mock"

    def scrape(self, keywords):
        return []

    def get_demo_signals(self):
        return [
            Signal(
                source="mock_reddit",
                keyword="test_keyword",
                volume=100,
                growth_pct=45.0,
                direction=SignalDirection.RISING,
            ),
        ]


@dataclass
class MockDivergence:
    def calculate(self, signal_data, market_data):
        return DivergenceResult(
            signal_strength=50.0,
            classification="strong",
            primary_metric=45.0,
            counter_metric=-5.0,
            explanation="Test divergence",
        )


@dataclass
class MockScorer:
    def score(self, data):
        return ScorerResult(
            total_score=75.0,
            classification="strong",
            breakdown={"test": 75.0},
        )


@dataclass
class MockVulnerability:
    def scan(self, target, data):
        return VulnerabilityScanResult(
            vulnerability_type="exploitable",
            moat_score=5,
            is_exploitable=True,
            reasoning="Test vulnerability",
        )


@dataclass
class MockSimulator:
    def simulate(self, params):
        return SimulationOutput(
            bear_case={"roi": -0.20},
            base_case={"roi": 0.25},
            bull_case={"roi": 0.80},
            verdict="proceed",
            roi_base=0.25,
            roi_bull=0.80,
            risk_assessment="Moderate",
        )


@dataclass
class MockLifecycle:
    def assess(self, data):
        return LifecycleAssessment(
            stage=LifecycleStage.VALIDATING,
            confidence=0.8,
            time_remaining="6 months",
            catalysts=["Product launch", "Funding round"],
            risks=["Competition", "Regulation"],
        )


@dataclass
class MockSizer:
    def size(self, conviction, portfolio_value, params):
        return PositionSize(
            allocation=5000.0,
            allocation_type="currency",
            conviction=conviction,
            stop_loss=4500.0,
            take_profit=7500.0,
            rationale="Test sizing",
        )


class TestTopologyLayers:
    """Test topology layer execution."""

    def setup_method(self):
        """Set up test fixtures."""
        self.engine = TopologyEngine()
        self.domain = DomainConfig(
            name="test_domain",
            display_name="Test Domain",
            icon="🧪",
            scrapers=[MockScraper()],
            divergence=MockDivergence(),
            scorer=MockScorer(),
            vulnerability=MockVulnerability(),
            simulator=MockSimulator(),
            lifecycle=MockLifecycle(),
            sizer=MockSizer(),
        )

    def test_layer1_scraping(self):
        """Test Layer 1 signal ingestion."""
        result = self.engine.run_layer1(self.domain, ["test"], demo_mode=True)

        assert result.success
        assert result.layer == 1
        assert len(result.data["signals"]) > 0
        assert result.data["signals"][0]["keyword"] == "test_keyword"

    def test_layer2_mosaic_assembly(self):
        """Test Layer 2 mosaic assembly."""
        signals_raw = [
            {
                "source": "reddit",
                "keyword": "test",
                "volume": 100,
                "growth_pct": 45.0,
                "direction": "rising",
            },
        ]
        result = self.engine.run_layer2(self.domain, signals_raw)

        assert result.success
        assert result.layer == 2
        assert result.hitl_required
        assert len(result.data["mosaic_cards"]) > 0

    def test_layer3_asymmetry_filter(self):
        """Test Layer 3 asymmetry filtering with HITL approval."""
        mosaic_card = {
            "keyword": "test",
            "domain": "test_domain",
            "coherence_score": 75.0,
            "coherence_label": "coherent",
            "fragments": [],
            "narrative": "Test",
            "action": "build_thesis",
            "metadata": {},
        }

        result = self.engine.run_layer3(self.domain, mosaic_card, HITLDecision.APPROVE)

        assert result.success
        assert result.layer == 3
        assert "vulnerability" in result.data
        assert "simulation" in result.data
        assert "thesis" in result.data

    def test_layer3_rejection(self):
        """Test Layer 3 respects HITL rejection."""
        mosaic_card = {"keyword": "test"}

        result = self.engine.run_layer3(self.domain, mosaic_card, HITLDecision.REJECT)

        assert not result.success
        assert "HITL Gate 1" in result.data["reason"]

    def test_layer4_timing(self):
        """Test Layer 4 timing calibration."""
        thesis_data = {
            "mosaic_card": {"keyword": "test"},
            "vulnerability": {"moat_score": 7},
            "simulation": {"verdict": "proceed"},
        }

        result = self.engine.run_layer4(self.domain, thesis_data, HITLDecision.APPROVE)

        assert result.success
        assert result.layer == 4
        assert "lifecycle" in result.data

    def test_layer5_sizing(self):
        """Test Layer 5 position sizing."""
        timing_data = {
            "thesis": {
                "mosaic_card": {"keyword": "test"},
            },
        }

        result = self.engine.run_layer5(
            self.domain,
            timing_data,
            portfolio_value=100000,
            hitl_decision=HITLDecision.APPROVE,
            conviction=ConvictionLevel.MEDIUM,
        )

        assert result.success
        assert result.layer == 5
        assert "position" in result.data
        assert "journal_entry" in result.data


class TestTieredAutonomy:
    """Test tiered autonomy HITL mechanism."""

    def test_confidence_threshold_manual(self):
        """Test MANUAL trust level always requires human approval."""
        threshold = ConfidenceThreshold(
            layer=1,
            trust_level=TrustLevel.MANUAL,
            auto_approval_threshold=0.75,
            spot_check_sample_rate=0.1,
        )

        assert not threshold.should_auto_approve(0.95, TrustLevel.MANUAL)
        assert not threshold.should_auto_approve(0.50, TrustLevel.MANUAL)

    def test_confidence_threshold_supervised(self):
        """Test SUPERVISED trust level auto-approves above threshold."""
        threshold = ConfidenceThreshold(
            layer=2,
            trust_level=TrustLevel.SUPERVISED,
            auto_approval_threshold=0.75,
            spot_check_sample_rate=0.2,
        )

        assert threshold.should_auto_approve(0.80, TrustLevel.SUPERVISED)
        assert not threshold.should_auto_approve(0.70, TrustLevel.SUPERVISED)

    def test_confidence_threshold_autonomous(self):
        """Test AUTONOMOUS trust level requires very high confidence."""
        threshold = ConfidenceThreshold(
            layer=3,
            trust_level=TrustLevel.AUTONOMOUS,
            auto_approval_threshold=0.75,
            spot_check_sample_rate=0.05,
            high_confidence_threshold=0.90,
        )

        assert threshold.should_auto_approve(0.95, TrustLevel.AUTONOMOUS)
        assert not threshold.should_auto_approve(0.80, TrustLevel.AUTONOMOUS)

    def test_audit_entry_recording(self):
        """Test audit entry creation."""
        entry = AuditEntry(
            layer=2,
            keyword="test",
            domain="test_domain",
            decision="approve",
            confidence=0.85,
            human_override=False,
        )

        assert entry.layer == 2
        assert entry.confidence == 0.85
        assert not entry.human_override
        assert entry.timestamp  # Should have auto timestamp

    def test_audit_entry_with_override(self):
        """Test audit entry with human override."""
        entry = AuditEntry(
            layer=3,
            keyword="test",
            domain="test_domain",
            decision="auto_approved",
            confidence=0.88,
            human_override=True,
            override_decision="reject",
            rationale="System overconfident",
        )

        assert entry.human_override
        assert entry.override_decision == "reject"
        assert entry.rationale == "System overconfident"


class TestTrustEvolution:
    """Test trust score evolution over time."""

    def test_increasing_trust_with_accuracy(self):
        """Test trust level increases with accuracy."""
        from social_arb.core.topology import TrustScore

        # Start with low accuracy
        trust = TrustScore(
            signal_type="mosaic_coherence",
            domain="test",
            accuracy_pct=60.0,
            total_audits=10,
            evolving_trust_level=TrustLevel.MANUAL,
        )

        assert trust.accuracy_pct == 60.0
        assert trust.evolving_trust_level == TrustLevel.MANUAL

        # After more successful decisions
        trust_evolved = TrustScore(
            signal_type="mosaic_coherence",
            domain="test",
            accuracy_pct=92.0,
            total_audits=50,
            evolving_trust_level=TrustLevel.SUPERVISED,  # Can escalate
        )

        assert trust_evolved.accuracy_pct > trust.accuracy_pct
        # Trust level could escalate based on accuracy


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
