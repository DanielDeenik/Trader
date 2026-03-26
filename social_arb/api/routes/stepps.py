"""STEPPS Classifier API routes."""

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
import logging

from social_arb.api.schemas import SteppsScoreCreate, SteppsScoreResponse, SteppsCorrectionCreate, SteppsTrainResponse
from social_arb.api import deps
from social_arb.db.schema import DEFAULT_DB_PATH
from social_arb.db import store
from social_arb.engine.stepps_classifier import SteppsClassifier

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/stepps", tags=["stepps"])


async def get_classifier(db_path: str = Depends(deps.get_db_path)) -> SteppsClassifier:
    """Dependency: get SteppsClassifier instance."""
    return SteppsClassifier(db_path=db_path)


@router.post("/score", response_model=SteppsScoreResponse)
async def score_signal(
    signal_id: int,
    classifier: SteppsClassifier = Depends(get_classifier),
) -> SteppsScoreResponse:
    """
    Score a signal across 6 STEPPS dimensions.

    Query params:
        signal_id: int - signal ID to score

    Returns:
        SteppsScoreResponse with all 6 dimensions + composite
    """
    try:
        # Fetch signal from DB
        signals = store.query_signals(db_path=classifier.db_path)
        matching = [s for s in signals if s.get("id") == signal_id]

        if not matching:
            raise HTTPException(status_code=404, detail=f"Signal {signal_id} not found")

        signal = matching[0]
        signal_dict = {
            "id": signal.get("id"),
            "strength": signal.get("strength", 0.5),
            "confidence": signal.get("confidence", 0.5),
            "direction": signal.get("direction", "neutral"),
            "source": signal.get("source", "unknown"),
            "signal_type": signal.get("signal_type", "general"),
        }

        # Score
        result = classifier.score(signal_dict)

        # Fetch from DB to return full row
        scores = store.query_stepps_scores(signal_id=signal_id, db_path=classifier.db_path)
        if scores:
            row = scores[0]
            return SteppsScoreResponse(
                id=row.get("id", 0),
                signal_id=signal_id,
                social_currency=row.get("social_currency", 0),
                triggers=row.get("triggers", 0),
                emotion=row.get("emotion", 0),
                public_visibility=row.get("public_visibility", 0),
                practical_value=row.get("practical_value", 0),
                stories=row.get("stories", 0),
                composite=row.get("composite", 0),
                scored_by=row.get("scored_by", "classifier"),
                model_version=row.get("model_version"),
                created_at=row.get("created_at", ""),
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to store score")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Scoring error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/scores", response_model=List[SteppsScoreResponse])
async def get_scores(
    symbol: Optional[str] = None,
    limit: int = 100,
    classifier: SteppsClassifier = Depends(get_classifier),
) -> List[SteppsScoreResponse]:
    """
    Get STEPPS scores for a symbol.

    Query params:
        symbol: str - get scores for all signals of this symbol
        limit: int - max results (default: 100)

    Returns:
        List of SteppsScoreResponse
    """
    try:
        if symbol:
            rows = store.query_stepps_scores_by_symbol(symbol=symbol, limit=limit, db_path=classifier.db_path)
        else:
            rows = store.query_stepps_scores(limit=limit, db_path=classifier.db_path)

        return [
            SteppsScoreResponse(
                id=row.get("id", 0),
                signal_id=row.get("signal_id", 0),
                social_currency=row.get("social_currency", 0),
                triggers=row.get("triggers", 0),
                emotion=row.get("emotion", 0),
                public_visibility=row.get("public_visibility", 0),
                practical_value=row.get("practical_value", 0),
                stories=row.get("stories", 0),
                composite=row.get("composite", 0),
                scored_by=row.get("scored_by", "classifier"),
                model_version=row.get("model_version"),
                created_at=row.get("created_at", ""),
            )
            for row in rows
        ]
    except Exception as e:
        logger.error(f"Get scores error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/correct", response_model=dict)
async def submit_correction(
    payload: SteppsCorrectionCreate,
    classifier: SteppsClassifier = Depends(get_classifier),
) -> dict:
    """
    Submit HITL correction for STEPPS scores.

    Body:
        signal_id: int
        social_currency, triggers, emotion, public_visibility, practical_value, stories: floats [0-1]

    Returns:
        {"success": bool, "training_id": int}
    """
    try:
        # Insert correction as training data
        train_id = store.insert_stepps_training(
            signal_id=payload.signal_id,
            social_currency=payload.social_currency,
            triggers=payload.triggers,
            emotion=payload.emotion,
            public_visibility=payload.public_visibility,
            practical_value=payload.practical_value,
            stories=payload.stories,
            source="human_correction",
            db_path=classifier.db_path,
        )

        logger.info(f"Stored HITL correction for signal {payload.signal_id}, training_id={train_id}")

        return {"success": True, "training_id": train_id}

    except Exception as e:
        logger.error(f"Correction error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/train", response_model=SteppsTrainResponse)
async def train_classifier(
    classifier: SteppsClassifier = Depends(get_classifier),
) -> SteppsTrainResponse:
    """
    Trigger retraining of STEPPS classifier on all labeled examples.

    Returns:
        SteppsTrainResponse with success flag, training count, model version
    """
    try:
        result = classifier.train(db_path=classifier.db_path)
        return SteppsTrainResponse(**result)

    except Exception as e:
        logger.error(f"Training error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
