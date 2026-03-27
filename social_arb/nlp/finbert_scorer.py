"""FinBERT sentiment scorer — finance-specific transformer model.

Uses ProsusAI/finbert from HuggingFace for accurate financial text sentiment.
This is Tier 2: used for high-value signals that pass L1 triage.

Gracefully degrades if transformers/torch not installed.
"""

import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

# Try to import transformers — graceful degradation if not available
try:
    from transformers import AutoTokenizer, AutoModelForSequenceClassification
    import torch
    FINBERT_AVAILABLE = True
except ImportError:
    FINBERT_AVAILABLE = False
    logger.info("transformers/torch not available — FinBERT scorer disabled")


MODEL_NAME = "ProsusAI/finbert"
LABEL_MAP = {
    "positive": "bullish",
    "negative": "bearish",
    "neutral": "neutral",
}


class FinBertScorer:
    """Finance-specific sentiment scorer using FinBERT transformer."""

    def __init__(self, lazy_load: bool = False):
        """
        Args:
            lazy_load: If True, don't load model until first score() call.
        """
        self._tokenizer = None
        self._model = None
        self._model_loaded = False

        if not lazy_load and FINBERT_AVAILABLE:
            self._load_model()

    @property
    def model_loaded(self) -> bool:
        return self._model_loaded

    def _load_model(self) -> bool:
        """Load FinBERT model and tokenizer. Returns True if successful."""
        if not FINBERT_AVAILABLE:
            return False

        try:
            logger.info(f"Loading FinBERT model: {MODEL_NAME}")
            self._tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
            self._model = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME)
            self._model.eval()
            self._model_loaded = True
            logger.info("FinBERT model loaded successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to load FinBERT model: {e}")
            self._model_loaded = False
            return False

    def score(self, text: str) -> Dict[str, Any]:
        """
        Score a single text string with FinBERT.

        Returns same schema as VaderScorer for interchangeability.
        Falls back to neutral if model not loaded.
        """
        if not text or not text.strip():
            return self._empty_result()

        if not self._model_loaded:
            # Try lazy load
            if not self._load_model():
                return self._fallback_result()

        try:
            inputs = self._tokenizer(
                text[:512],  # FinBERT max 512 tokens
                return_tensors="pt",
                truncation=True,
                max_length=512,
                padding=True,
            )

            with torch.no_grad():
                outputs = self._model(**inputs)
                probs = torch.nn.functional.softmax(outputs.logits, dim=-1)

            # FinBERT labels: positive, negative, neutral
            prob_values = probs[0].tolist()
            labels = self._model.config.id2label

            scores = {}
            for idx, prob in enumerate(prob_values):
                label = labels[idx].lower()
                scores[label] = prob

            positive = scores.get("positive", 0)
            negative = scores.get("negative", 0)
            neutral = scores.get("neutral", 0)

            # Compound: positive - negative (range [-1, 1])
            compound = positive - negative

            # Direction from highest probability
            max_label = max(scores, key=scores.get)
            direction = LABEL_MAP.get(max_label, "neutral")

            # Confidence from probability spread
            max_prob = max(prob_values)
            confidence = min(1.0, max_prob)

            # Strength: magnitude of compound
            strength = min(1.0, abs(compound))

            return {
                "compound": round(compound, 4),
                "positive": round(positive, 4),
                "negative": round(negative, 4),
                "neutral_score": round(neutral, 4),
                "direction": direction,
                "strength": round(strength, 4),
                "confidence": round(confidence, 4),
                "model": "finbert",
            }

        except Exception as e:
            logger.error(f"FinBERT scoring error: {e}")
            return self._fallback_result()

    def score_batch(self, texts: List[str]) -> List[Dict[str, Any]]:
        """Score multiple texts. Processes one at a time for simplicity."""
        return [self.score(text) for text in texts]

    @staticmethod
    def _empty_result() -> Dict[str, Any]:
        return {
            "compound": 0.0,
            "positive": 0.0,
            "negative": 0.0,
            "neutral_score": 1.0,
            "direction": "neutral",
            "strength": 0.0,
            "confidence": 0.0,
            "model": "finbert",
        }

    @staticmethod
    def _fallback_result() -> Dict[str, Any]:
        return {
            "compound": 0.0,
            "positive": 0.0,
            "negative": 0.0,
            "neutral_score": 1.0,
            "direction": "neutral",
            "strength": 0.0,
            "confidence": 0.0,
            "model": "finbert_fallback",
        }
