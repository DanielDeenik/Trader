"""Sentiment enricher — orchestrates VADER and FinBERT scoring on signals.

Two-tier approach:
  Tier 1 (VADER): Fast-screen every text-based signal
  Tier 2 (FinBERT): Deep-score high-value signals (above threshold)

Text-bearing sources: news, reddit, sec_edgar, google_trends
Non-text sources (skip): yfinance, coingecko, defillama, github, hiring,
                          patents, appstore, web_presence
"""

import json
import logging
from typing import Dict, Any, List, Optional

from social_arb.nlp.vader_scorer import VaderScorer

logger = logging.getLogger(__name__)

# Sources that contain scoreable text
TEXT_SOURCES = {"news", "reddit", "sec_edgar", "google_trends"}


class SentimentEnricher:
    """Orchestrates sentiment scoring across signal pipeline."""

    def __init__(
        self,
        use_finbert: bool = True,
        finbert_threshold: float = 0.6,
    ):
        """
        Args:
            use_finbert: Whether to use FinBERT for deep scoring
            finbert_threshold: VADER strength above which FinBERT is triggered
        """
        self._vader = VaderScorer()
        self._finbert = None
        self._use_finbert = use_finbert
        self._finbert_threshold = finbert_threshold

        if use_finbert:
            try:
                from social_arb.nlp.finbert_scorer import FinBertScorer, FINBERT_AVAILABLE
                if FINBERT_AVAILABLE:
                    self._finbert = FinBertScorer(lazy_load=True)
                    logger.info("FinBERT scorer available (lazy-loaded)")
                else:
                    logger.info("FinBERT not available — VADER-only mode")
                    self._use_finbert = False
            except ImportError:
                logger.info("FinBERT not available — VADER-only mode")
                self._use_finbert = False

    def extract_text(self, signal: Dict[str, Any]) -> str:
        """
        Extract scoreable text from a signal's raw data.

        Handles both raw_json (string) and raw (dict) patterns used
        by different collectors.
        """
        raw = signal.get("raw_json") or signal.get("raw")
        if raw is None:
            return ""

        if isinstance(raw, str):
            try:
                raw = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                return raw  # Treat as plain text

        if not isinstance(raw, dict):
            return str(raw)

        # Extract text fields based on source
        parts = []
        for key in ("title", "description", "summary", "selftext", "text", "narrative"):
            val = raw.get(key)
            if val and isinstance(val, str):
                parts.append(val)

        # For SEC filings, include form type context
        if "form_type" in raw:
            parts.append(f"SEC filing: {raw['form_type']}")

        return " ".join(parts)

    def enrich_signal(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enrich a single signal with sentiment scores.

        Non-text sources are returned unchanged.
        Text sources get VADER score, and optionally FinBERT.
        """
        source = signal.get("source", "")

        if source not in TEXT_SOURCES:
            return signal

        text = self.extract_text(signal)
        if not text.strip():
            return signal

        # Tier 1: VADER
        vader_result = self._vader.score(text)

        # Tier 2: FinBERT (if enabled and threshold met)
        final_result = vader_result
        if self.should_deep_score(vader_result) and self._finbert is not None:
            finbert_result = self._finbert.score(text)
            if finbert_result.get("model") != "finbert_fallback":
                # Blend: FinBERT takes priority but VADER contributes
                final_result = self._blend_scores(vader_result, finbert_result)

        # Update signal fields
        enriched = dict(signal)
        enriched["direction"] = final_result["direction"]
        enriched["strength"] = final_result["strength"]
        enriched["confidence"] = max(signal.get("confidence", 0), final_result["confidence"])

        # Add sentiment details to raw_json
        raw = enriched.get("raw_json") or enriched.get("raw") or "{}"
        if isinstance(raw, str):
            try:
                raw_dict = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                raw_dict = {}
        else:
            raw_dict = dict(raw)

        raw_dict["sentiment"] = {
            "compound": final_result["compound"],
            "direction": final_result["direction"],
            "strength": final_result["strength"],
            "confidence": final_result["confidence"],
            "model": final_result.get("model", "vader"),
        }

        # Write back as string if original was string
        if "raw_json" in enriched:
            enriched["raw_json"] = json.dumps(raw_dict)
        else:
            enriched["raw"] = raw_dict

        return enriched

    def enrich_batch(self, signals: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Enrich a batch of signals."""
        return [self.enrich_signal(s) for s in signals]

    def should_deep_score(self, vader_result: Dict[str, Any]) -> bool:
        """Decide if a signal should get FinBERT deep scoring."""
        if not self._use_finbert:
            return False
        return vader_result.get("strength", 0) >= self._finbert_threshold

    @staticmethod
    def _blend_scores(
        vader: Dict[str, Any],
        finbert: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Blend VADER and FinBERT scores.
        FinBERT gets 70% weight, VADER 30%.
        """
        weight_finbert = 0.7
        weight_vader = 0.3

        compound = (
            finbert["compound"] * weight_finbert
            + vader["compound"] * weight_vader
        )

        strength = (
            finbert["strength"] * weight_finbert
            + vader["strength"] * weight_vader
        )

        # Direction from blended compound
        if compound >= 0.15:
            direction = "bullish"
        elif compound <= -0.15:
            direction = "bearish"
        else:
            direction = "neutral"

        confidence = max(finbert["confidence"], vader["confidence"])

        return {
            "compound": round(compound, 4),
            "positive": round(finbert.get("positive", 0), 4),
            "negative": round(finbert.get("negative", 0), 4),
            "neutral_score": round(finbert.get("neutral_score", 0), 4),
            "direction": direction,
            "strength": round(strength, 4),
            "confidence": round(confidence, 4),
            "model": "finbert+vader",
        }
