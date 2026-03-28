"""Position management."""

from fastapi import APIRouter
from pydantic import BaseModel
from social_arb.api.deps import get_db_path
from social_arb.api.schemas import PositionCreate, PositionResponse
from social_arb.db.store import insert_position, query_positions, update_position

router = APIRouter()


class PositionClose(BaseModel):
    """Request to close a position."""
    exit_price: float
    exit_date: str


@router.get("/positions", response_model=list[PositionResponse])
def list_positions(status: str = "open"):
    """List positions with optional status filter."""
    return query_positions(db_path=get_db_path(), status=status)


@router.post("/positions", response_model=dict, status_code=201)
def create_position(body: PositionCreate):
    """Create a new position."""
    row_id = insert_position(
        db_path=get_db_path(),
        thesis_id=body.thesis_id,
        symbol=body.symbol,
        domain=body.domain,
        direction=body.direction,
        allocation_pct=body.allocation_pct,
        conviction=body.conviction,
        entry_price=body.entry_price,
        entry_date=body.entry_date,
        data_class=body.data_class.value,
    )
    return {"id": row_id, "symbol": body.symbol, "status": "open"}


@router.patch("/positions/{position_id}", response_model=dict, status_code=200)
def close_position(position_id: int, body: PositionClose):
    """Close a position by setting exit price and date."""
    update_position(
        position_id=position_id,
        exit_price=body.exit_price,
        exit_date=body.exit_date,
        db_path=get_db_path(),
    )
    return {"id": position_id, "status": "closed"}
