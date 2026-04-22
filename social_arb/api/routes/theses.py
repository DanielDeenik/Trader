"""Thesis queries and creation."""

from fastapi import APIRouter
from pydantic import BaseModel
from social_arb.api.deps import get_db_path
from social_arb.api.schemas import ThesisResponse
from social_arb.db.store import query_theses, insert_thesis

router = APIRouter()


class ThesisCreate(BaseModel):
    """Request to create a thesis manually."""
    symbol: str
    domain: str  # public, private, crypto
    thesis_type: str
    lifecycle_stage: str  # emerging, validating, confirmed, saturated
    roi_bear: float
    roi_base: float
    roi_bull: float
    risk_assessment: str  # stored as vulnerability_json


@router.get("/theses", response_model=list[ThesisResponse])
def list_theses(symbol: str | None = None, status: str | None = None):
    """List theses with optional filters."""
    return query_theses(db_path=get_db_path(), symbol=symbol, status=status)


@router.post("/theses", response_model=dict, status_code=201)
def create_thesis(body: ThesisCreate):
    """Create a new thesis manually."""
    thesis_id = insert_thesis(
        mosaic_id=None,
        symbol=body.symbol,
        domain=body.domain,
        roi_bear=body.roi_bear,
        roi_base=body.roi_base,
        roi_bull=body.roi_bull,
        kelly_fraction=0.0,
        lifecycle_stage=body.lifecycle_stage,
        status="active",
        vulnerability_json=body.risk_assessment,
        simulation_json="{}",
        thesis_type=body.thesis_type,
        db_path=get_db_path(),
    )
    return {"id": thesis_id, "symbol": body.symbol, "status": "active"}
