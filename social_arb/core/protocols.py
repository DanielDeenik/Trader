"""
Domain Interface Contracts (Enhanced)

Every asset domain (public markets, private markets) must implement
these Protocol classes to plug into the core topology engine.

The topology doesn't care what domain it's running — it calls these interfaces.
Each domain provides its own scrapers, divergence formula, scorer, vulnerability
scanner, simulator, lifecycle tracker, and position sizer.

Enhanced with data provider interfaces and ML/feature output dataclasses
to support data-driven engines that read from real data sources.

Usage:
    from social_arb.core.protocols import DomainScraper, DomainDivergence, ...

    class MyCustomScraper:
        '''Implements DomainScraper protocol — no inheritance needed.'''
        def scrape(self, keywords): ...
        def get_demo_signals(self): ...
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable, Any, Optional
from dataclasses import dataclass, field, asdict
from enum import Enum
from datetime import datetime


# ─── Technical Data Models ──────────────────────────────────────────────────

@dataclass
class OHLCVBar:
    """Single OHLCV candlestick bar with technical indicators."""
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: int
    indicators: dict = field(default_factory=dict)  # SMA, EMA, RSI, etc.


@dataclass
class FeatureSnapshot:
    """Feature vector snapshot for ML models."""
    symbol: str
    timestamp: str
    features: dict  # Feature name -> value
    metadata: dict = field(default_factory=dict)


@dataclass
class MLPrediction:
    """Output from ML models / engines."""
    symbol: str
    engine: str  # "sentiment_divergence", "kelly_sizer", "irr_simulator", etc.
    prediction_type: str  # "signal", "size", "return", "moat"
    value: float  # The prediction
    confidence: float  # 0-1
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    details: dict = field(default_factory=dict)
    audit_id: Optional[str] = None


# ─── Data Provider Protocol ──────────────────────────────────────────────────

@runtime_checkable
class DataProvider(Protocol):
    """Interface for real-time market and signal data access."""

    def get_instrument(self, symbol: str) -> dict:
        """Get instrument metadata (name, sector, exchange, etc.)."""
        ...

    def get_ohlcv(self, symbol: str, days: int = 100) -> list[dict]:
        """Get OHLCV historical price data. Returns list of dicts with keys:
        date, open, high, low, close, volume."""
        ...

    def get_signals(self, symbol: str, sources: Optional[list[str]] = None) -> list[dict]:
        """Get raw signals for symbol from various sources.
        Returns list of Signal dicts."""
        ...

    def get_features(self, symbol: str) -> dict:
        """Get pre-computed features from database."""
        ...


# ─── Shared Data Models ─────────────────────────────────────────────────────

class SignalDirection(Enum):
    RISING = "rising"
    FALLING = "falling"
    STABLE = "stable"
    VOLATILE = "volatile"


class LifecycleStage(Enum):
    EMERGING = "emerging"
    VALIDATING = "validating"
    CONFIRMED = "confirmed"
    SATURATED = "saturated"


class ConvictionLevel(Enum):
    HIGH = "high"         # >70% probability
    MEDIUM = "medium"     # 40-70%
    LOW = "low"           # <40%
    WATCH = "watch"       # Interesting but not actionable yet


@dataclass
class Signal:
    """Universal signal container — works for any domain."""
    source: str                       # e.g., "reddit", "github", "sec_edgar"
    keyword: str                      # The search term / ticker / company name
    volume: float                     # Raw volume metric (mentions, stars, filings)
    growth_pct: float                 # Growth rate over lookback period
    direction: SignalDirection
    raw_data: dict = field(default_factory=dict)
    scraped_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    domain: str = ""                  # Set by the domain plugin
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        result = asdict(self)
        result["direction"] = self.direction.value
        return result


@dataclass
class DivergenceResult:
    """Output of any domain's divergence calculation."""
    signal_strength: float            # Raw divergence score
    classification: str               # "strong" | "monitor" | "pass"
    primary_metric: float             # The main growth metric
    counter_metric: float             # The market/competitor metric
    explanation: str                  # Human-readable why

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ScorerResult:
    """Output of any domain's quality/opportunity scorer."""
    total_score: float                # Normalized 0-100
    classification: str               # Domain-specific label
    breakdown: dict = field(default_factory=dict)  # Dimension scores
    recommendation: str = ""          # Actionable next step

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class VulnerabilityScanResult:
    """Output of any domain's vulnerability scanner."""
    vulnerability_type: str           # Domain-specific enum value
    moat_score: int                   # 1-10 (universal scale)
    is_exploitable: bool
    reasoning: str
    specific_weakness: Optional[str] = None
    fix_or_exploit: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class SimulationOutput:
    """Output of any domain's asymmetric payoff simulator."""
    bear_case: dict                   # Domain-specific scenario metrics
    base_case: dict
    bull_case: dict
    verdict: str                      # "proceed" | "high_risk" | "pass"
    roi_base: float                   # Expected return, base case
    roi_bull: float                   # Expected return, bull case
    risk_assessment: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class LifecycleAssessment:
    """Output of any domain's timing/lifecycle tracker."""
    stage: LifecycleStage
    confidence: float                 # 0-1
    time_remaining: Optional[str]     # Estimated window remaining
    catalysts: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        result = asdict(self)
        result["stage"] = self.stage.value
        return result


@dataclass
class PositionSize:
    """Output of any domain's position sizer."""
    allocation: float                 # Currency amount or % of portfolio
    allocation_type: str              # "currency" | "percentage"
    conviction: ConvictionLevel
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    rationale: str = ""

    def to_dict(self) -> dict:
        result = asdict(self)
        result["conviction"] = self.conviction.value
        return result


@dataclass
class MosaicFragment:
    """Single signal fragment contributing to a mosaic card."""
    source: str
    direction: SignalDirection
    strength: float                   # 0-100
    change_pct: float
    note: str = ""
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> dict:
        result = asdict(self)
        result["direction"] = self.direction.value
        return result


@dataclass
class MosaicCard:
    """Assembled mosaic card — universal across domains."""
    keyword: str
    domain: str
    coherence_score: float            # 0-100
    coherence_label: str              # "highly_coherent" | "coherent" | "neutral" | "conflicted"
    fragments: list[dict]
    narrative: str
    action: str                       # "investigate" | "build_thesis" | "pass"
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


# ─── Domain Protocol Interfaces ─────────────────────────────────────────────
# Domains implement these via structural subtyping (duck typing).
# No inheritance required — just implement the method signatures.


@runtime_checkable
class DomainScraper(Protocol):
    """L1: What signals does this domain ingest?"""

    @property
    def domain_name(self) -> str:
        """Return the domain identifier (e.g., 'public_markets', 'private_markets')."""
        ...

    def scrape(self, keywords: list[str]) -> list[Signal]:
        """Scrape live signals for the given keywords."""
        ...

    def get_demo_signals(self) -> list[Signal]:
        """Return pre-built demo signals for demo mode."""
        ...


@runtime_checkable
class DomainDivergence(Protocol):
    """L2: How does this domain measure divergence between crowd and market?"""

    def calculate(self, signal_data: dict, market_data: dict) -> DivergenceResult:
        """Calculate divergence between signal momentum and market awareness."""
        ...


@runtime_checkable
class DomainScorer(Protocol):
    """L2: How does this domain score opportunity quality?"""

    def score(self, data: dict) -> ScorerResult:
        """Score the opportunity quality using domain-specific criteria."""
        ...


@runtime_checkable
class DomainVulnerability(Protocol):
    """L3: What makes a target vulnerable/exploitable in this domain?"""

    def scan(self, target: str, data: dict) -> VulnerabilityScanResult:
        """Scan target for exploitable weaknesses."""
        ...


@runtime_checkable
class DomainSimulator(Protocol):
    """L3: How does this domain model asymmetric payoff?"""

    def simulate(self, params: dict) -> SimulationOutput:
        """Run bear/base/bull scenario simulation."""
        ...


@runtime_checkable
class DomainLifecycle(Protocol):
    """L4: How does this domain track opportunity timing?"""

    def assess(self, data: dict) -> LifecycleAssessment:
        """Assess current lifecycle stage and timing window."""
        ...


@runtime_checkable
class DomainSizer(Protocol):
    """L5: How does this domain size positions?"""

    def size(self, conviction: ConvictionLevel, portfolio_value: float, params: dict) -> PositionSize:
        """Calculate position size based on conviction and portfolio."""
        ...


# ─── Domain Registry Entry ──────────────────────────────────────────────────

@dataclass
class DomainConfig:
    """Configuration for a registered domain plugin."""
    name: str                         # e.g., "public_markets"
    display_name: str                 # e.g., "Public Markets"
    icon: str                         # e.g., "🛒"
    scrapers: list[DomainScraper] = field(default_factory=list)
    divergence: Optional[DomainDivergence] = None
    scorer: Optional[DomainScorer] = None
    vulnerability: Optional[DomainVulnerability] = None
    simulator: Optional[DomainSimulator] = None
    lifecycle: Optional[DomainLifecycle] = None
    sizer: Optional[DomainSizer] = None
    db_path: str = ""                 # Domain-specific database path
    enabled: bool = True
