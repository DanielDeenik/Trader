"""
STEPPS Classifier Engine

Implements Jonah Berger's STEPPS framework (Social Currency, Triggers, Emotion,
Public, Practical Value, Stories) to predict viral spread potential of signals.

Pipeline:
1. LLM Seeding: Use Claude API to score first N signals (cold-start)
2. ML Training: Train RandomForest on labeled examples (>50)
3. HITL Correction: Humans adjust scores → retrain weekly

Feature engineering: signal strength, confidence, direction, source, signal_type
Model: Multi-output RandomForest (6 independent regressors for each STEPPS dimension)
Model persistence: joblib
"""

import logging
import json
import os
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from datetime import datetime
import tempfile
from pathlib import Path

import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import LabelEncoder
from sklearn.multioutput import MultiOutputRegressor
import joblib

from social_arb.db.schema import DEFAULT_DB_PATH
from social_arb.db import store

logger = logging.getLogger(__name__)

# Model storage directory
MODELS_DIR = Path(__file__).parent.parent / "models"
MODELS_DIR.mkdir(exist_ok=True)

STEPPS_DIMENSIONS = ["social_currency", "triggers", "emotion", "public_visibility", "practical_value", "stories"]


@dataclass
class SteppsResult:
    """Result from STEPPS scoring."""
    signal_id: int
    social_currency: float
    triggers: float
    emotion: float
    public_visibility: float
    practical_value: float
    stories: float
    composite: float
    scored_by: str  # 'llm', 'classifier', 'human'
    model_version: Optional[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "signal_id": self.signal_id,
            "social_currency": self.social_currency,
            "triggers": self.triggers,
            "emotion": self.emotion,
            "public_visibility": self.public_visibility,
            "practical_value": self.practical_value,
            "stories": self.stories,
            "composite": self.composite,
            "scored_by": self.scored_by,
            "model_version": self.model_version,
        }


class SteppsClassifier:
    """Multi-output STEPPS scorer: LLM → classifier → HITL loop."""

    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = db_path
        self.model = None
        self.feature_encoders = {}  # For categorical features
        self.model_version = None
        self._load_model()

    @property
    def domain_name(self) -> str:
        return "stepps_classifier"

    def _load_model(self) -> None:
        """Load trained classifier from disk if available."""
        model_path = MODELS_DIR / "stepps_classifier.joblib"
        encoder_path = MODELS_DIR / "stepps_encoders.joblib"

        if model_path.exists() and encoder_path.exists():
            try:
                self.model = joblib.load(model_path)
                self.feature_encoders = joblib.load(encoder_path)
                # Extract version from model_path metadata
                self.model_version = datetime.now().strftime("rf_v1_%Y-%m-%d")
                logger.info(f"Loaded STEPPS classifier from {model_path}")
            except Exception as e:
                logger.warning(f"Failed to load STEPPS classifier: {e}")
                self.model = None

    def score(self, signal_dict: Dict[str, Any]) -> SteppsResult:
        """
        Score a signal across 6 STEPPS dimensions.

        Args:
            signal_dict: {
                "id": int,
                "strength": float (0-1),
                "confidence": float (0-1),
                "direction": str ("bullish"/"bearish"/"neutral"),
                "source": str ("reddit"/"yfinance"/"sec_edgar"/etc),
                "signal_type": str ("general"/"regulatory"/etc),
            }

        Returns:
            SteppsResult with 6 dimension scores + composite
        """
        signal_id = signal_dict.get("id")
        if not signal_id:
            raise ValueError("signal_dict must contain 'id'")

        # Check if already scored
        existing = store.query_stepps_scores(signal_id=signal_id, db_path=self.db_path)
        if existing:
            return self._result_from_row(existing[0], signal_id)

        # Determine scoring method
        training_count = store.count_stepps_training(db_path=self.db_path)

        if training_count < 10:
            # Not enough labeled data: try LLM seeding
            return self._score_with_llm(signal_dict)
        elif training_count < 50:
            # Limited data: use classifier if available, else LLM
            if self.model is not None:
                return self._score_with_classifier(signal_dict)
            else:
                return self._score_with_llm(signal_dict)
        else:
            # Plenty of data: use classifier
            return self._score_with_classifier(signal_dict)

    def _score_with_llm(self, signal_dict: Dict[str, Any]) -> SteppsResult:
        """Score using Claude API for cold-start. Gracefully falls back to zeros."""
        signal_id = signal_dict.get("id")

        try:
            import anthropic
        except ImportError:
            logger.warning("anthropic SDK not installed, skipping LLM seeding")
            return self._zero_result(signal_id, "classifier")

        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            logger.warning("ANTHROPIC_API_KEY not set, skipping LLM seeding")
            return self._zero_result(signal_id, "classifier")

        try:
            client = anthropic.Anthropic(api_key=api_key)

            prompt = f"""
Score this signal across 6 STEPPS dimensions (Contagious by Jonah Berger).
Return JSON with keys: social_currency, triggers, emotion, public_visibility, practical_value, stories.
Each value must be 0.0-1.0.

Signal:
- Strength: {signal_dict.get('strength', 0)}
- Confidence: {signal_dict.get('confidence', 0)}
- Direction: {signal_dict.get('direction', 'neutral')}
- Source: {signal_dict.get('source', 'unknown')}
- Type: {signal_dict.get('signal_type', 'general')}

Consider:
- Social Currency: How much does sharing this make people look good/informed?
- Triggers: Are there environmental reminders? (e.g., news, seasonality)
- Emotion: Does it evoke strong emotions? (fear, surprise, excitement)
- Public: Is the behavior/signal visible to others?
- Practical Value: Is this useful/actionable information?
- Stories: Is it wrapped in a compelling narrative?

Return ONLY valid JSON, no extra text.
"""

            message = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}],
            )

            response_text = message.content[0].text
            scores_dict = json.loads(response_text)

            # Validate and clamp to [0, 1]
            scores = {}
            for dim in STEPPS_DIMENSIONS:
                val = float(scores_dict.get(dim, 0.5))
                scores[dim] = max(0.0, min(1.0, val))

            composite = np.mean(list(scores.values()))

            # Store the score
            score_id = store.insert_stepps_score(
                signal_id=signal_id,
                social_currency=scores["social_currency"],
                triggers=scores["triggers"],
                emotion=scores["emotion"],
                public_visibility=scores["public_visibility"],
                practical_value=scores["practical_value"],
                stories=scores["stories"],
                composite=composite,
                scored_by="llm",
                model_version="claude-3.5-sonnet",
                db_path=self.db_path,
            )

            # Also store as training data for future classifier training
            store.insert_stepps_training(
                signal_id=signal_id,
                social_currency=scores["social_currency"],
                triggers=scores["triggers"],
                emotion=scores["emotion"],
                public_visibility=scores["public_visibility"],
                practical_value=scores["practical_value"],
                stories=scores["stories"],
                source="llm_seed",
                db_path=self.db_path,
            )

            logger.info(f"LLM scored signal {signal_id}: composite={composite:.2f}")

            return SteppsResult(
                signal_id=signal_id,
                social_currency=scores["social_currency"],
                triggers=scores["triggers"],
                emotion=scores["emotion"],
                public_visibility=scores["public_visibility"],
                practical_value=scores["practical_value"],
                stories=scores["stories"],
                composite=composite,
                scored_by="llm",
                model_version="claude-3.5-sonnet",
            )

        except Exception as e:
            logger.error(f"LLM scoring error: {e}")
            return self._zero_result(signal_id, "classifier")

    def _score_with_classifier(self, signal_dict: Dict[str, Any]) -> SteppsResult:
        """Score using trained classifier."""
        if self.model is None:
            logger.warning("No trained classifier available")
            return self._zero_result(signal_dict.get("id"), "classifier")

        signal_id = signal_dict.get("id")

        try:
            # Feature engineering
            features = self._engineer_features(signal_dict)
            X = np.array(features).reshape(1, -1)

            # Predict 6 STEPPS dimensions
            predictions = self.model.predict(X)[0]

            # Clamp to [0, 1]
            scores = {
                dim: max(0.0, min(1.0, float(pred)))
                for dim, pred in zip(STEPPS_DIMENSIONS, predictions)
            }

            composite = np.mean(list(scores.values()))

            # Store the score
            store.insert_stepps_score(
                signal_id=signal_id,
                social_currency=scores["social_currency"],
                triggers=scores["triggers"],
                emotion=scores["emotion"],
                public_visibility=scores["public_visibility"],
                practical_value=scores["practical_value"],
                stories=scores["stories"],
                composite=composite,
                scored_by="classifier",
                model_version=self.model_version,
                db_path=self.db_path,
            )

            logger.info(f"Classifier scored signal {signal_id}: composite={composite:.2f}")

            return SteppsResult(
                signal_id=signal_id,
                social_currency=scores["social_currency"],
                triggers=scores["triggers"],
                emotion=scores["emotion"],
                public_visibility=scores["public_visibility"],
                practical_value=scores["practical_value"],
                stories=scores["stories"],
                composite=composite,
                scored_by="classifier",
                model_version=self.model_version,
            )

        except Exception as e:
            logger.error(f"Classifier scoring error: {e}")
            return self._zero_result(signal_id, "classifier")

    def _engineer_features(self, signal_dict: Dict[str, Any]) -> List[float]:
        """
        Convert signal fields to numeric features for the classifier.

        Feature order (MUST match training):
        0. strength (float, 0-1)
        1. confidence (float, 0-1)
        2. direction_encoded (int, from LabelEncoder)
        3. source_encoded (int, from LabelEncoder)
        4. signal_type_encoded (int, from LabelEncoder)
        """
        strength = float(signal_dict.get("strength", 0.5))
        confidence = float(signal_dict.get("confidence", 0.5))
        direction = signal_dict.get("direction", "neutral")
        source = signal_dict.get("source", "unknown")
        signal_type = signal_dict.get("signal_type", "general")

        # For inference, use stored encoders (built during training)
        direction_encoded = self._encode_categorical("direction", direction)
        source_encoded = self._encode_categorical("source", source)
        type_encoded = self._encode_categorical("signal_type", signal_type)

        return [strength, confidence, direction_encoded, source_encoded, type_encoded]

    def _encode_categorical(self, feature_name: str, value: str) -> int:
        """Encode categorical value using stored encoder. Default to 0 if unknown."""
        if feature_name not in self.feature_encoders:
            return 0
        encoder = self.feature_encoders[feature_name]
        try:
            return int(encoder.transform([value])[0])
        except Exception:
            return 0

    def train(self, db_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Train classifier on STEPPS training data.

        Returns:
            {
                "success": bool,
                "training_count": int,
                "model_version": str,
                "error": Optional[str],
            }
        """
        if db_path is None:
            db_path = self.db_path

        try:
            # Fetch training data + signal features
            training_data = store.query_stepps_training(limit=100000, db_path=db_path)
            logger.info(f"Training on {len(training_data)} examples")

            if len(training_data) < 10:
                return {
                    "success": False,
                    "training_count": len(training_data),
                    "model_version": None,
                    "error": f"Insufficient training data: {len(training_data)} < 10",
                }

            # Build feature matrix and target matrix
            X_list = []
            y_list = []

            for row in training_data:
                signal_id = row["signal_id"]
                signal = store.query_signals(db_path=db_path)
                # Find matching signal
                matching = [s for s in signal if s["id"] == signal_id]
                if not matching:
                    continue

                signal_dict = matching[0]
                features = self._engineer_features(signal_dict)
                targets = [
                    row.get("social_currency", 0.5),
                    row.get("triggers", 0.5),
                    row.get("emotion", 0.5),
                    row.get("public_visibility", 0.5),
                    row.get("practical_value", 0.5),
                    row.get("stories", 0.5),
                ]
                X_list.append(features)
                y_list.append(targets)

            if not X_list:
                return {
                    "success": False,
                    "training_count": 0,
                    "model_version": None,
                    "error": "No valid training examples after feature engineering",
                }

            X = np.array(X_list)
            y = np.array(y_list)

            # Train multi-output RandomForest
            base_rf = RandomForestRegressor(
                n_estimators=50,
                max_depth=10,
                min_samples_split=5,
                random_state=42,
                n_jobs=-1,
            )
            self.model = MultiOutputRegressor(base_rf)
            self.model.fit(X, y)

            # Store encoders for inference
            self.feature_encoders = self._build_encoders(training_data, db_path)

            # Persist to disk
            model_path = MODELS_DIR / "stepps_classifier.joblib"
            encoder_path = MODELS_DIR / "stepps_encoders.joblib"
            joblib.dump(self.model, model_path)
            joblib.dump(self.feature_encoders, encoder_path)

            self.model_version = datetime.now().strftime("rf_v1_%Y-%m-%d")

            logger.info(f"Trained STEPPS classifier: {len(X)} examples, saved to {model_path}")

            return {
                "success": True,
                "training_count": len(X),
                "model_version": self.model_version,
                "error": None,
            }

        except Exception as e:
            logger.error(f"Training error: {e}", exc_info=True)
            return {
                "success": False,
                "training_count": 0,
                "model_version": None,
                "error": str(e),
            }

    def _build_encoders(self, training_data: List[Dict], db_path: str) -> Dict:
        """Build LabelEncoders for categorical features from training data."""
        encoders = {}

        # Collect all unique values for each categorical feature
        directions = set()
        sources = set()
        signal_types = set()

        for row in training_data:
            signal_id = row["signal_id"]
            signals = store.query_signals(db_path=db_path)
            matching = [s for s in signals if s["id"] == signal_id]
            if matching:
                directions.add(matching[0].get("direction", "neutral"))
                sources.add(matching[0].get("source", "unknown"))
                signal_types.add(matching[0].get("signal_type", "general"))

        # Create and fit encoders
        for feature_name, values in [
            ("direction", directions),
            ("source", sources),
            ("signal_type", signal_types),
        ]:
            encoder = LabelEncoder()
            encoder.fit(list(values))
            encoders[feature_name] = encoder

        return encoders

    def _zero_result(self, signal_id: int, scored_by: str) -> SteppsResult:
        """Return neutral STEPPS scores (0.5 for all dimensions)."""
        store.insert_stepps_score(
            signal_id=signal_id,
            social_currency=0.5,
            triggers=0.5,
            emotion=0.5,
            public_visibility=0.5,
            practical_value=0.5,
            stories=0.5,
            composite=0.5,
            scored_by=scored_by,
            model_version=self.model_version,
            db_path=self.db_path,
        )
        return SteppsResult(
            signal_id=signal_id,
            social_currency=0.5,
            triggers=0.5,
            emotion=0.5,
            public_visibility=0.5,
            practical_value=0.5,
            stories=0.5,
            composite=0.5,
            scored_by=scored_by,
            model_version=self.model_version,
        )

    def _result_from_row(self, row: Dict[str, Any], signal_id: int) -> SteppsResult:
        """Convert DB row to SteppsResult."""
        return SteppsResult(
            signal_id=signal_id,
            social_currency=row.get("social_currency", 0.5),
            triggers=row.get("triggers", 0.5),
            emotion=row.get("emotion", 0.5),
            public_visibility=row.get("public_visibility", 0.5),
            practical_value=row.get("practical_value", 0.5),
            stories=row.get("stories", 0.5),
            composite=row.get("composite", 0.5),
            scored_by=row.get("scored_by", "classifier"),
            model_version=row.get("model_version"),
        )
