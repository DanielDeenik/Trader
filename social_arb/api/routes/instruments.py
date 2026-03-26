"""Instrument CRUD — manage the ticker universe dynamically."""

from fastapi import APIRouter, HTTPException, Response
from social_arb.api.deps import get_db_path
from social_arb.api.schemas import InstrumentCreate, InstrumentUpdate, InstrumentResponse
from social_arb.db.store import (
    insert_instrument, query_instruments, update_instrument, delete_instrument,
)

router = APIRouter()


@router.get("/instruments", response_model=list[InstrumentResponse])
def list_instruments(
    type: str | None = None,
    data_class: str | None = None,
    symbol: str | None = None,
):
    """List all instruments with optional filters."""
    return query_instruments(
        db_path=get_db_path(), type=type,
        data_class=data_class, symbol=symbol,
    )


@router.post("/instruments", response_model=InstrumentResponse, status_code=201)
def create_instrument(body: InstrumentCreate):
    """Add a new instrument to the universe."""
    db_path = get_db_path()
    try:
        row_id = insert_instrument(
            db_path=db_path,
            symbol=body.symbol.upper(),
            name=body.name,
            type=body.type.value,
            sector=body.sector,
            vertical=body.vertical,
            exchange=body.exchange,
            market_cap_b=body.market_cap_b,
            data_class=body.data_class.value,
            metadata_json=body.metadata_json,
        )
    except Exception as e:
        if "UNIQUE" in str(e).upper():
            raise HTTPException(409, f"Symbol '{body.symbol}' already exists")
        raise HTTPException(500, str(e))

    results = query_instruments(db_path=db_path, symbol=body.symbol.upper())
    if not results:
        raise HTTPException(500, "Insert succeeded but query failed")
    return results[0]


@router.patch("/instruments/{instrument_id}", response_model=InstrumentResponse)
def patch_instrument(instrument_id: int, body: InstrumentUpdate):
    """Update mutable fields on an instrument."""
    db_path = get_db_path()
    update_instrument(
        db_path=db_path, instrument_id=instrument_id,
        sector=body.sector, vertical=body.vertical,
        exchange=body.exchange, market_cap_b=body.market_cap_b,
        metadata_json=body.metadata_json,
    )
    from social_arb.db.schema import get_connection
    from social_arb.db.adapter import get_placeholder
    with get_connection(db_path) as conn:
        ph = get_placeholder()
        row = conn.execute(
            f"SELECT * FROM instruments WHERE id = {ph}", (instrument_id,)
        ).fetchone()
    if not row:
        raise HTTPException(404, "Instrument not found")
    return dict(row)


@router.delete("/instruments/{instrument_id}", status_code=204)
def remove_instrument(instrument_id: int):
    """Remove an instrument from the universe."""
    delete_instrument(db_path=get_db_path(), instrument_id=instrument_id)
    return Response(status_code=204)
