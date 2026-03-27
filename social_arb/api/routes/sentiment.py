"""Sentiment analysis API routes."""

from typing import List, Optional
from fastapi import APIRouter
from pydantic import BaseModel

from social_arb.nlp.vader_scorer import VaderScorer

router = APIRouter(prefix="/api/v1/sentiment", tags=["sentiment"])

# Singleton scorer
_vader = VaderScorer()


class ScoreRequest(BaseModel):
    text: str
    model: str = "vader"  # "vader" or "finbert"


class ScoreBatchRequest(BaseModel):
    texts: List[str]
    model: str = "vader"


class ScoreResponse(BaseModel):
    compound: float
    positive: float
    negative: float
    neutral_score: float
    direction: str
    strength: float
    confidence: float
    model: str = "vader"


class ScoreBatchResponse(BaseModel):
    results: List[ScoreResponse]
    count: int


@router.post("/score", response_model=ScoreResponse)
async def score_text(req: ScoreRequest):
    """Score a single text for sentiment."""
    if req.model == "finbert":
        try:
            from social_arb.nlp.finbert_scorer import FinBertScorer, FINBERT_AVAILABLE
            if FINBERT_AVAILABLE:
                scorer = FinBertScorer(lazy_load=True)
                result = scorer.score(req.text)
                return ScoreResponse(**result)
        except ImportError:
            pass

    result = _vader.score(req.text)
    return ScoreResponse(**result)


@router.post("/score-batch", response_model=ScoreBatchResponse)
async def score_batch(req: ScoreBatchRequest):
    """Score multiple texts for sentiment."""
    results = _vader.score_batch(req.texts)
    return ScoreBatchResponse(
        results=[ScoreResponse(**r) for r in results],
        count=len(results),
    )
