"""Mosaic card queries."""

from fastapi import APIRouter
from social_arb.api.deps import get_db_path
from social_arb.api.schemas import MosaicResponse
from social_arb.db.store import query_mosaics

router = APIRouter()


@router.get("/mosaics", response_model=list[MosaicResponse])
def list_mosaics(symbol: str | None = None, action: str | None = None):
    """List mosaic cards with optional filters."""
    return query_mosaics(db_path=get_db_path(), symbol=symbol, action=action)
