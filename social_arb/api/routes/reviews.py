"""HITL review submission and query."""

from fastapi import APIRouter
from social_arb.api.deps import get_db_path
from social_arb.api.schemas import ReviewCreate, ReviewResponse
from social_arb.db.store import insert_review, query_reviews
import json

router = APIRouter()


@router.get("/reviews", response_model=list[ReviewResponse])
def list_reviews(gate: str | None = None, symbol: str | None = None):
    """List HITL reviews with optional filters."""
    return query_reviews(db_path=get_db_path(), gate=gate, symbol=symbol)


@router.post("/reviews", response_model=dict, status_code=201)
def submit_review(body: ReviewCreate):
    """Submit a HITL gate review."""
    insert_review(
        db_path=get_db_path(),
        gate=body.gate.value,
        symbol=body.symbol,
        entity_id=body.entity_id,
        entity_type=body.entity_type.value,
        scores_json=json.dumps(body.scores),
        total_score=body.total_score,
        threshold=body.threshold,
        narrative=None,
        dominant_narrative=body.dominant_narrative,
        market_pricing=body.market_pricing,
        invalidation=body.invalidation,
        decision=body.decision.value,
        position_size=body.position_size,
        risk_note=body.risk_note,
    )
    return {
        "status": "saved",
        "gate": body.gate.value,
        "symbol": body.symbol,
        "decision": body.decision.value,
        "total_score": body.total_score,
        "threshold": body.threshold,
    }
