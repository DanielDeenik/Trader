"""Pydantic v2 models for API request/response validation."""

from __future__ import annotations
from typing import Optional, Any, List
from datetime import datetime
from pydantic import BaseModel, Field, computed_field, model_validator
from enum import Enum


# ─── Enums ────────────────────────────────────────────────────────────────

class InstrumentType(str, Enum):
    stock = "stock"
    private = "private"
    etf = "etf"
    crypto = "crypto"


class DataClass(str, Enum):
    public = "public"
    private = "private"


class GateType(str, Enum):
    L1_triage = "L1_triage"
    L2_validation = "L2_validation"
    L3_conviction = "L3_conviction"


class ReviewDecision(str, Enum):
    promote = "promote"
    watch = "watch"
    discard = "discard"
    forge = "forge"
    hold = "hold"
    reject = "reject"
    execute = "execute"
    defer = "defer"


class EntityType(str, Enum):
    signal_cluster = "signal_cluster"
    mosaic = "mosaic"
    thesis = "thesis"
    position = "position"


# ─── Gate thresholds ──────────────────────────────────────────────────────

GATE_THRESHOLDS = {
    "L1_triage": 12.0,       # 4 criteria × 5 max = 20, threshold 12
    "L2_validation": 12.0,   # 4 criteria × 5 max = 20, threshold 12
    "L3_conviction": 15.0,   # 5 criteria × 5 max = 25, threshold 15
}


# ─── Instruments ──────────────────────────────────────────────────────────

class InstrumentCreate(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=20)
    name: str = Field(..., min_length=1)
    type: InstrumentType
    sector: Optional[str] = None
    vertical: Optional[str] = None
    exchange: Optional[str] = None
    market_cap_b: Optional[float] = None
    data_class: DataClass = DataClass.public
    metadata_json: Optional[str] = None


class InstrumentUpdate(BaseModel):
    sector: Optional[str] = None
    vertical: Optional[str] = None
    exchange: Optional[str] = None
    market_cap_b: Optional[float] = None
    metadata_json: Optional[str] = None


class InstrumentResponse(BaseModel):
    id: int
    symbol: str
    name: str
    type: str
    sector: Optional[str] = None
    vertical: Optional[str] = None
    exchange: Optional[str] = None
    market_cap_b: Optional[float] = None
    data_class: str
    metadata_json: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    model_config = {"from_attributes": True}


# ─── Signals ──────────────────────────────────────────────────────────────

class SignalResponse(BaseModel):
    id: int
    timestamp: str
    symbol: str
    source: str
    signal_type: Optional[str] = None
    direction: Optional[str] = None
    strength: Optional[float] = None
    confidence: Optional[float] = None
    raw_json: Optional[Any] = None
    data_class: Optional[str] = None
    created_at: Optional[str] = None

    model_config = {"from_attributes": True}


class CollectRequest(BaseModel):
    sources: list[str] = Field(
        default=["yfinance", "reddit", "sec_edgar"],
        description="Which collectors to run",
    )
    symbols: Optional[list[str]] = Field(
        default=None,
        description="Override symbols. None = use config defaults.",
    )
    domain: Optional[str] = Field(
        default="all",
        description="Domain filter: all, public, private, crypto",
    )


# ─── Mosaics ─────────────────────────────────────────────────────────────

class MosaicResponse(BaseModel):
    id: int
    symbol: str
    domain: str
    coherence_score: Optional[float] = None
    divergence_strength: Optional[float] = None
    fragments_json: Optional[Any] = None
    narrative: Optional[str] = None
    action: Optional[str] = None
    data_class: Optional[str] = None
    created_at: Optional[str] = None

    model_config = {"from_attributes": True}


# ─── Theses ───────────────────────────────────────────────────────────────

class ThesisResponse(BaseModel):
    id: int
    mosaic_id: Optional[int] = None
    symbol: str
    domain: str
    thesis_type: Optional[str] = None
    roi_bear: Optional[float] = None
    roi_base: Optional[float] = None
    roi_bull: Optional[float] = None
    kelly_fraction: Optional[float] = None
    lifecycle_stage: Optional[str] = None
    status: Optional[str] = None
    vulnerability_json: Optional[Any] = None
    simulation_json: Optional[Any] = None
    created_at: Optional[str] = None

    model_config = {"from_attributes": True}


# ─── Reviews (HITL) ──────────────────────────────────────────────────────

class ReviewCreate(BaseModel):
    gate: GateType
    symbol: str
    entity_id: int
    entity_type: EntityType
    scores: dict[str, int] = Field(
        ..., description="Criterion name → score (1-5)"
    )
    decision: ReviewDecision
    dominant_narrative: Optional[str] = None
    market_pricing: Optional[str] = None
    invalidation: Optional[str] = None
    position_size: Optional[str] = None
    risk_note: Optional[str] = None

    @computed_field
    @property
    def total_score(self) -> int:
        return sum(self.scores.values())

    @computed_field
    @property
    def threshold(self) -> float:
        return GATE_THRESHOLDS.get(self.gate.value, 12.0)


class ReviewResponse(BaseModel):
    id: int
    gate: str
    symbol: str
    entity_id: Optional[int] = None
    entity_type: Optional[str] = None
    scores_json: Optional[Any] = None
    total_score: Optional[float] = None
    threshold: Optional[float] = None
    decision: str
    dominant_narrative: Optional[str] = None
    market_pricing: Optional[str] = None
    invalidation: Optional[str] = None
    position_size: Optional[str] = None
    risk_note: Optional[str] = None
    created_at: Optional[str] = None

    model_config = {"from_attributes": True}


# ─── Positions ────────────────────────────────────────────────────────────

class PositionCreate(BaseModel):
    thesis_id: int
    symbol: str
    domain: str
    direction: str = "long"
    allocation_pct: float
    conviction: str = "medium"
    entry_price: float
    entry_date: str
    data_class: DataClass = DataClass.public


class PositionResponse(BaseModel):
    id: int
    thesis_id: int
    symbol: str
    domain: str
    direction: Optional[str] = None
    allocation_pct: Optional[float] = None
    conviction: Optional[str] = None
    entry_price: Optional[float] = None
    entry_date: Optional[str] = None
    exit_price: Optional[float] = None
    exit_date: Optional[str] = None
    pnl: Optional[float] = None
    pnl_pct: Optional[float] = None
    status: Optional[str] = None
    data_class: Optional[str] = None
    created_at: Optional[str] = None

    model_config = {"from_attributes": True}


# ─── Engine Results ───────────────────────────────────────────────────────

class EngineResultResponse(BaseModel):
    symbol: str
    engines: dict[str, Any] = Field(
        default_factory=dict,
        description="Engine name → result dict. Keys: sentiment_divergence, "
                    "kelly_sizer, irr_simulator, regulatory_moat, "
                    "technical_analyzer, cross_domain_amplifier",
    )
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


# ─── Health ───────────────────────────────────────────────────────────────

class SourceHealth(BaseModel):
    source: str
    status: str  # "fresh", "stale", "error"
    last_signal: Optional[str] = None
    signal_count: int = 0


class HealthResponse(BaseModel):
    status: str  # "healthy", "degraded", "unhealthy"
    db_backend: str
    table_counts: dict[str, int]
    source_health: list[SourceHealth] = []


# ─── Analysis ─────────────────────────────────────────────────────────────

class AnalyzeRequest(BaseModel):
    symbols: Optional[list[str]] = None


class AnalyzeResponse(BaseModel):
    symbols_analyzed: int
    mosaics_created: int
    theses_created: int
    errors: list[str] = []


# ===== TASK QUEUE SCHEMAS =====


class TaskParamsCollect(BaseModel):
    """Parameters for a 'collect' task."""
    sources: List[str] = Field(..., description="List of data sources: yfinance, reddit, sec_edgar, google_trends, github, coingecko, defillama")
    symbols: Optional[List[str]] = Field(None, description="Specific symbols to collect; if None, collects all tracked instruments")
    domain: str = Field("public", description="public or private")


class TaskParamsAnalyze(BaseModel):
    """Parameters for an 'analyze' task."""
    symbols: Optional[List[str]] = Field(None, description="Specific symbols to analyze; if None, analyzes all")


class TaskParamsBackfill(BaseModel):
    """Parameters for a 'backfill' task."""
    source: str = Field(..., description="Data source to backfill")
    symbol: str = Field(..., description="Symbol to backfill")
    start_date: str = Field(..., description="ISO date: 2026-01-01")
    end_date: str = Field(..., description="ISO date: 2026-03-26")


class TaskCreate(BaseModel):
    """Request to enqueue a new task."""
    task_type: str = Field(..., description="Task type: 'collect', 'analyze', 'backfill'")
    params: dict[str, Any] = Field(default_factory=dict, description="Task-specific parameters as dict")
    max_attempts: int = Field(3, ge=1, le=10, description="Max retry attempts")


class TaskResponse(BaseModel):
    """Task status response."""
    id: int
    task_type: str
    status: str  # pending, running, completed, failed, cancelled
    params_json: Optional[str] = None
    result_json: Optional[str] = None
    error: Optional[str] = None
    attempts: int
    max_attempts: int
    next_retry_at: Optional[str] = None
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None

    model_config = {"from_attributes": True}


class TaskListResponse(BaseModel):
    """List of tasks with pagination."""
    tasks: List[TaskResponse]
    total_count: int


class SourceHealthResponse(BaseModel):
    """Health status of all data sources."""
    sources: List[SourceHealth]
    as_of: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


# ─── STEPPS Classifier ────────────────────────────────────────────────────────


class SteppsScoreCreate(BaseModel):
    signal_id: int
    social_currency: float = Field(ge=0, le=1)
    triggers: float = Field(ge=0, le=1)
    emotion: float = Field(ge=0, le=1)
    public_visibility: float = Field(ge=0, le=1)
    practical_value: float = Field(ge=0, le=1)
    stories: float = Field(ge=0, le=1)


class SteppsScoreResponse(BaseModel):
    id: int
    signal_id: int
    social_currency: float
    triggers: float
    emotion: float
    public_visibility: float
    practical_value: float
    stories: float
    composite: float
    scored_by: str
    model_version: Optional[str]
    created_at: str


class SteppsCorrectionCreate(BaseModel):
    signal_id: int
    social_currency: float = Field(ge=0, le=1)
    triggers: float = Field(ge=0, le=1)
    emotion: float = Field(ge=0, le=1)
    public_visibility: float = Field(ge=0, le=1)
    practical_value: float = Field(ge=0, le=1)
    stories: float = Field(ge=0, le=1)


class SteppsTrainResponse(BaseModel):
    success: bool
    training_count: int
    model_version: Optional[str]
    error: Optional[str]


# ─── Lattice (HITL Graph Visualization) ───────────────────────────────────────


class LatticeNodeResponse(BaseModel):
    id: str
    type: str
    label: str
    data: Optional[Any] = None

    model_config = {"from_attributes": True}


class LatticeEdgeResponse(BaseModel):
    id: str
    source: str
    target: str
    label: Optional[str] = None

    model_config = {"from_attributes": True}


class LatticeGraphResponse(BaseModel):
    symbol: str
    nodes: List[LatticeNodeResponse]
    edges: List[LatticeEdgeResponse]
    stats: dict[str, int] = Field(
        default_factory=dict,
        description="Counts of each node type"
    )


class LatticeNodeCreate(BaseModel):
    type: str = Field(..., description="Node type: custom, or ref to existing type")
    label: str = Field(..., description="Display label for the node")
    data: Optional[dict[str, Any]] = None
    connect_to: Optional[List[str]] = Field(
        default=None,
        description="List of node IDs to connect to (source→target)"
    )


class LatticeEdgeCreate(BaseModel):
    source: str = Field(..., description="Source node ID")
    target: str = Field(..., description="Target node ID")
    label: Optional[str] = Field(None, description="Edge label (e.g., 'fragment', 'supports')")
