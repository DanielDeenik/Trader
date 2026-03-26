"""Thesis queries."""

from fastapi import APIRouter
from social_arb.api.deps import get_db_path
from social_arb.api.schemas import ThesisResponse
from social_arb.db.store import query_theses

router = APIRouter()


@router.get("/theses", response_model=list[ThesisResponse])
def list_theses(symbol: str | None = None, status: str | None = None):
    """List theses with optional filters."""
    return query_theses(db_path=get_db_path(), symbol=symbol, status=status)
