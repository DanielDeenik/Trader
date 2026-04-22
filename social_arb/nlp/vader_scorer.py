"""VADER sentiment scorer — fast, rule-based, no GPU needed.

VADER (Valence Aware Dictionary and sEntiment Reasoner) is optimized for
social media text. We use it as Tier 1 fast-screen for all text signals.

Returns:
    compound: float [-1, 1] — overall sentiment
    direction: "bullish" | "bearish" | "neutral"
    strength: float [0, 1] — signal strength derived from compound magnitude
    confidence: float [0, 1] — how confident we are (based on text length + magnitude)
"""

import logging
from typing import Dict, Any, List

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

logger = logging.getLogger(__name__)

# Thresholds for direction classification
BULLISH_THRESHOLD = 0.15
BEARISH_THRESHOLD = -0.15


class VaderScorer:
    """Fast sentiment scorer using VADER."""

    def __init__(self):
        self._analyzer = SentimentIntensityAnalyzer()

    def score(self, text: str) -> Dict[str, Any]:
        """
        Score a single text string.

        Args:
            text: Raw text to analyze

        Returns:
            Dict with compound, positive, negative, neutral_score,
            direction, strength, confidence
        """
        if not text or not text.strip():
            return {
                "compound": 0.0,
                "positive": 0.0,
                "negative": 0.0,
                "neutral_score": 1.0,
                "direction": "neutral",
                "strength": 0.0,
                "confidence": 0.0,
            }

        scores = self._analyzer.polarity_scores(text)

        compound = scores["compound"]

        # Direction from compound score
        if compound >= BULLISH_THRESHOLD:
            direction = "bullish"
        elif compound <= BEARISH_THRESHOLD:
            direction = "bearish"
        else:
            direction = "neutral"

        # Strength: absolute compound mapped to [0, 1]
        strength = min(1.0, abs(compound))

        # Confidence: higher for longer text and stronger signal
        word_count = len(text.split())
        length_factor = min(1.0, word_count / 20)  # 20+ words = full confidence from length
        magnitude_factor = abs(compound)
        confidence = min(1.0, 0.3 + 0.4 * length_factor + 0.3 * magnitude_factor)

        return {
            "compound": round(compound, 4),
            "positive": round(scores["pos"], 4),
            "negative": round(scores["neg"], 4),
            "neutral_score": round(scores["neu"], 4),
            "direction": direction,
            "strength": round(strength, 4),
            "confidence": round(confidence, 4),
        }

    def score_batch(self, texts: List[str]) -> List[Dict[str, Any]]:
        """Score multiple texts."""
        return [self.score(text) for text in texts]
