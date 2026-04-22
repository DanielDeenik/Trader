"""Analysis endpoints — batch pipeline and per-symbol engine runs."""

from fastapi import APIRouter
from social_arb.api.deps import get_db_path
from social_arb.api.schemas import AnalyzeRequest, AnalyzeResponse, EngineResultResponse
from social_arb.api.orchestrator import EngineOrchestrator
from social_arb.pipeline import run_analysis
from social_arb.engine.technical_analyzer import calculate_all_indicators

router = APIRouter()


@router.post("/analyze", response_model=AnalyzeResponse)
def run_batch_analysis(body: AnalyzeRequest):
    """Run batch analysis pipeline on collected signals."""
    result = run_analysis(db_path=get_db_path(), symbols=body.symbols)
    return AnalyzeResponse(
        symbols_analyzed=result.get("symbols_analyzed", 0),
        mosaics_created=result.get("mosaics_created", 0),
        theses_created=result.get("theses_created", 0),
        errors=result.get("errors", []),
    )


@router.get("/engine/{symbol}", response_model=EngineResultResponse)
def run_engines(symbol: str, portfolio_value: float = 100000):
    """Run all 6 engines for a specific symbol and return combined results."""
    orch = EngineOrchestrator(db_path=get_db_path())
    results = orch.run_all(symbol.upper(), portfolio_value=portfolio_value)
    return EngineResultResponse(symbol=symbol.upper(), engines=results)
