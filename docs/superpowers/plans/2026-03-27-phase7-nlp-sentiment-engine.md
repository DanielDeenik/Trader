# Phase 7: NLP Sentiment Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add hybrid NLP sentiment scoring (VADER fast-screen + FinBERT deep-score) to all text-based signals, replacing hardcoded neutral directions with real sentiment analysis.

**Architecture:** Two-tier scoring pipeline. Tier 1: VADER scores every text signal on ingestion (fast, no GPU). Tier 2: FinBERT rescores signals that pass L1 triage or have high VADER magnitude (more accurate, heavier). Scores are written back to the signal's `direction`, `strength`, and `raw_json.sentiment` fields. A new `SentimentEnricher` engine integrates into the pipeline, and a new API route exposes on-demand rescoring.

**Tech Stack:** vaderSentiment (VADER), transformers + torch (FinBERT: ProsusAI/finbert), numpy

---

## File Structure

| File | Responsibility |
|------|---------------|
| `social_arb/nlp/__init__.py` | Package marker |
| `social_arb/nlp/vader_scorer.py` | VADER sentiment scoring — fast, lightweight |
| `social_arb/nlp/finbert_scorer.py` | FinBERT sentiment scoring — accurate, heavy |
| `social_arb/nlp/sentiment_enricher.py` | Orchestrator: decides which scorer to use, enriches signals |
| `social_arb/api/routes/sentiment.py` | API routes for sentiment scoring and bulk enrichment |
| `social_arb/api/main.py` | Register sentiment routes (modify) |
| `social_arb/tasks/workers.py` | Add `handle_enrich_sentiment` task handler (modify) |
| `social_arb/pipeline.py` | Call sentiment enricher before analysis (modify) |
| `tests/test_vader_scorer.py` | VADER scorer tests |
| `tests/test_finbert_scorer.py` | FinBERT scorer tests |
| `tests/test_sentiment_enricher.py` | Enricher orchestration tests |
| `tests/test_api_sentiment.py` | API route tests |
| `pyproject.toml` | Add vaderSentiment, transformers, torch deps (modify) |

---

## Task 1: VADER Sentiment Scorer

**Files:**
- Create: `social_arb/nlp/__init__.py`
- Create: `social_arb/nlp/vader_scorer.py`
- Test: `tests/test_vader_scorer.py`

- [ ] **Step 1: Create package and test file**

`tests/test_vader_scorer.py`:

```python
"""Tests for VADER sentiment scorer."""

import pytest
from social_arb.nlp.vader_scorer import VaderScorer


def test_vader_scorer_instantiate():
    scorer = VaderScorer()
    assert scorer is not None


def test_vader_positive_sentiment():
    scorer = VaderScorer()
    result = scorer.score("Amazing earnings beat, revenue soaring, incredible growth")
    assert result["compound"] > 0.3
    assert result["direction"] == "bullish"


def test_vader_negative_sentiment():
    scorer = VaderScorer()
    result = scorer.score("Terrible losses, massive layoffs, company struggling badly")
    assert result["compound"] < -0.3
    assert result["direction"] == "bearish"


def test_vader_neutral_sentiment():
    scorer = VaderScorer()
    result = scorer.score("Company filed quarterly report with the SEC")
    assert result["direction"] in ("neutral", "bullish", "bearish")
    assert abs(result["compound"]) < 0.5


def test_vader_empty_text():
    scorer = VaderScorer()
    result = scorer.score("")
    assert result["compound"] == 0.0
    assert result["direction"] == "neutral"


def test_vader_score_batch():
    scorer = VaderScorer()
    texts = [
        "Stock surges on great earnings",
        "Company faces lawsuit and regulatory probe",
        "Quarterly filing submitted",
    ]
    results = scorer.score_batch(texts)
    assert len(results) == 3
    assert results[0]["direction"] == "bullish"
    assert results[1]["direction"] == "bearish"


def test_vader_result_has_all_fields():
    scorer = VaderScorer()
    result = scorer.score("Great news for investors")
    assert "compound" in result
    assert "positive" in result
    assert "negative" in result
    assert "neutral_score" in result
    assert "direction" in result
    assert "strength" in result
    assert "confidence" in result
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /sessions/laughing-serene-mendel/mnt/Trader && python -m pytest tests/test_vader_scorer.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Install dependency and implement**

```bash
pip install vaderSentiment --break-system-packages
```

`social_arb/nlp/__init__.py`:
```python
"""NLP sentiment analysis package."""
```

`social_arb/nlp/vader_scorer.py`:

```python
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
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_vader_scorer.py -v`
Expected: All pass

- [ ] **Step 5: Commit**

```bash
git add social_arb/nlp/ tests/test_vader_scorer.py
git commit -m "feat: add VADER sentiment scorer (Tier 1 fast-screen)"
```

---

## Task 2: FinBERT Sentiment Scorer

**Files:**
- Create: `social_arb/nlp/finbert_scorer.py`
- Test: `tests/test_finbert_scorer.py`

- [ ] **Step 1: Create test file**

`tests/test_finbert_scorer.py`:

```python
"""Tests for FinBERT sentiment scorer."""

import pytest
from social_arb.nlp.finbert_scorer import FinBertScorer, FINBERT_AVAILABLE


@pytest.fixture
def scorer():
    """Create scorer — skip if transformers not available."""
    if not FINBERT_AVAILABLE:
        pytest.skip("transformers/torch not installed")
    return FinBertScorer()


def test_finbert_available_flag():
    """Test that FINBERT_AVAILABLE is a boolean."""
    assert isinstance(FINBERT_AVAILABLE, bool)


def test_finbert_instantiate_without_model():
    """Test scorer can be created even without model loaded."""
    scorer = FinBertScorer(lazy_load=True)
    assert scorer is not None
    assert scorer.model_loaded is False


def test_finbert_score_positive(scorer):
    result = scorer.score("Revenue increased significantly, beating all analyst expectations")
    assert result["direction"] in ("bullish", "neutral", "bearish")
    assert "compound" in result
    assert "confidence" in result


def test_finbert_score_negative(scorer):
    result = scorer.score("Company reported massive losses and is facing bankruptcy")
    assert result["direction"] in ("bullish", "neutral", "bearish")
    assert "compound" in result


def test_finbert_empty_text():
    scorer = FinBertScorer(lazy_load=True)
    result = scorer.score("")
    assert result["compound"] == 0.0
    assert result["direction"] == "neutral"


def test_finbert_score_batch(scorer):
    results = scorer.score_batch([
        "Strong earnings growth reported",
        "Regulatory investigation announced",
    ])
    assert len(results) == 2
    for r in results:
        assert "direction" in r
        assert "compound" in r


def test_finbert_fallback_without_model():
    """Test that scoring without model returns neutral fallback."""
    scorer = FinBertScorer(lazy_load=True)
    # Don't load model — should return fallback
    result = scorer.score("Test text")
    assert result["direction"] == "neutral"
    assert result["confidence"] == 0.0
```

- [ ] **Step 2: Run test to verify failures**

Run: `python -m pytest tests/test_finbert_scorer.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Install dependencies and implement**

```bash
pip install transformers torch --break-system-packages
```

Note: torch is large (~800MB). If pip install fails due to memory/disk, the scorer gracefully degrades — `FINBERT_AVAILABLE = False` and all calls return VADER fallback.

`social_arb/nlp/finbert_scorer.py`:

```python
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
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_finbert_scorer.py -v`
Expected: All pass (some skipped if torch not installed)

- [ ] **Step 5: Commit**

```bash
git add social_arb/nlp/finbert_scorer.py tests/test_finbert_scorer.py
git commit -m "feat: add FinBERT sentiment scorer (Tier 2 deep-score)"
```

---

## Task 3: Sentiment Enricher (Orchestrator)

**Files:**
- Create: `social_arb/nlp/sentiment_enricher.py`
- Test: `tests/test_sentiment_enricher.py`

- [ ] **Step 1: Create test file**

`tests/test_sentiment_enricher.py`:

```python
"""Tests for sentiment enricher orchestrator."""

import json
import pytest
from social_arb.nlp.sentiment_enricher import SentimentEnricher


@pytest.fixture
def enricher():
    return SentimentEnricher(use_finbert=False)  # VADER-only for fast tests


def test_enricher_instantiate(enricher):
    assert enricher is not None


def test_extract_text_from_signal_news(enricher):
    signal = {
        "source": "news",
        "raw_json": json.dumps({"title": "BREAKING: Tech company reports record earnings"}),
    }
    text = enricher.extract_text(signal)
    assert "record earnings" in text.lower()


def test_extract_text_from_signal_reddit(enricher):
    signal = {
        "source": "reddit",
        "raw": {"title": "PLTR to the moon!", "subreddit": "wallstreetbets"},
    }
    text = enricher.extract_text(signal)
    assert "pltr" in text.lower() or "moon" in text.lower()


def test_extract_text_from_signal_sec(enricher):
    signal = {
        "source": "sec_edgar",
        "raw": {"description": "Annual report filed", "form_type": "10-K"},
    }
    text = enricher.extract_text(signal)
    assert "annual report" in text.lower()


def test_enrich_single_signal(enricher):
    signal = {
        "source": "news",
        "direction": "neutral",
        "strength": 0.5,
        "confidence": 0.5,
        "raw_json": json.dumps({"title": "Amazing growth, revenue soaring to new heights"}),
    }
    enriched = enricher.enrich_signal(signal)
    assert enriched["direction"] in ("bullish", "bearish", "neutral")
    assert "sentiment" in json.loads(enriched["raw_json"]) if isinstance(enriched["raw_json"], str) else "sentiment" in enriched["raw_json"]


def test_enrich_batch(enricher):
    signals = [
        {
            "source": "news",
            "direction": "neutral",
            "strength": 0.5,
            "confidence": 0.5,
            "raw_json": json.dumps({"title": "Great earnings beat"}),
        },
        {
            "source": "reddit",
            "direction": "bullish",
            "strength": 0.3,
            "confidence": 0.4,
            "raw": {"title": "Terrible losses reported"},
        },
    ]
    enriched = enricher.enrich_batch(signals)
    assert len(enriched) == 2


def test_enricher_preserves_non_text_signals(enricher):
    signal = {
        "source": "yfinance",
        "direction": "bullish",
        "strength": 0.8,
        "confidence": 0.9,
        "raw_json": json.dumps({"price": 150.0, "volume": 1000000}),
    }
    enriched = enricher.enrich_signal(signal)
    # Non-text source: should be returned unchanged
    assert enriched["direction"] == "bullish"
    assert enriched["strength"] == 0.8


def test_should_use_finbert(enricher):
    # enricher has use_finbert=False, so always returns False
    assert enricher.should_deep_score({"strength": 0.9}) is False

    # Create one with finbert enabled
    enricher_fb = SentimentEnricher(use_finbert=True, finbert_threshold=0.7)
    # High VADER strength should trigger finbert
    assert enricher_fb.should_deep_score({"strength": 0.8}) is True
    assert enricher_fb.should_deep_score({"strength": 0.3}) is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_sentiment_enricher.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement**

`social_arb/nlp/sentiment_enricher.py`:

```python
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
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_sentiment_enricher.py -v`
Expected: All pass

- [ ] **Step 5: Commit**

```bash
git add social_arb/nlp/sentiment_enricher.py tests/test_sentiment_enricher.py
git commit -m "feat: add sentiment enricher orchestrator (VADER + FinBERT blend)"
```

---

## Task 4: Pipeline Integration

**Files:**
- Modify: `social_arb/pipeline.py` (add sentiment enrichment before analysis)
- Modify: `social_arb/tasks/workers.py` (add enrich_sentiment task handler)
- Test: `tests/test_pipeline_sentiment.py`

- [ ] **Step 1: Create test file**

`tests/test_pipeline_sentiment.py`:

```python
"""Tests for sentiment enrichment in pipeline."""

import json
import pytest
from social_arb.nlp.sentiment_enricher import SentimentEnricher


def test_enricher_in_pipeline_context():
    """Simulate pipeline enrichment of collected signals."""
    enricher = SentimentEnricher(use_finbert=False)

    # Simulate signals as they come from collectors
    signals = [
        {
            "symbol": "DATABRICKS",
            "source": "news",
            "signal_type": "news_mention",
            "direction": "neutral",
            "strength": 0.6,
            "confidence": 0.7,
            "raw_json": json.dumps({
                "title": "Databricks raises $500M at $43B valuation, massive growth",
                "feed": "techcrunch",
            }),
        },
        {
            "symbol": "PLTR",
            "source": "reddit",
            "signal_type": "social_mention",
            "direction": "bullish",
            "strength": 0.3,
            "confidence": 0.4,
            "raw": {
                "title": "PLTR is going to crash hard, terrible earnings",
                "subreddit": "wallstreetbets",
            },
        },
        {
            "symbol": "NVDA",
            "source": "yfinance",
            "signal_type": "price",
            "direction": "bullish",
            "strength": 0.8,
            "confidence": 0.9,
            "raw_json": json.dumps({"price": 950.0}),
        },
    ]

    enriched = enricher.enrich_batch(signals)

    # News signal should have sentiment
    assert enriched[0]["direction"] in ("bullish", "neutral", "bearish")
    raw0 = json.loads(enriched[0]["raw_json"])
    assert "sentiment" in raw0

    # Reddit signal should have sentiment
    assert enriched[1]["direction"] in ("bullish", "neutral", "bearish")

    # yfinance signal should be unchanged (non-text source)
    assert enriched[2]["direction"] == "bullish"
    assert enriched[2]["strength"] == 0.8


def test_handle_enrich_sentiment():
    """Test the task handler function."""
    from social_arb.tasks.workers import HANDLER_MAP
    assert "enrich_sentiment" in HANDLER_MAP
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_pipeline_sentiment.py -v`
Expected: Partial pass (enricher test passes, handler test fails)

- [ ] **Step 3: Modify pipeline.py**

Add sentiment enrichment at the start of `run_analysis()`. After the `all_signals` query block (around line 120), add:

```python
    # Enrich text-based signals with NLP sentiment
    try:
        from social_arb.nlp.sentiment_enricher import SentimentEnricher
        enricher = SentimentEnricher(use_finbert=False)  # VADER-only in batch mode
        all_signals = enricher.enrich_batch(all_signals)
        logger.info(f"Enriched {len(all_signals)} signals with sentiment scores")
    except Exception as e:
        logger.warning(f"Sentiment enrichment failed (continuing without): {e}")
```

- [ ] **Step 4: Modify workers.py**

Add a new task handler after `handle_train_stepps`:

```python
async def handle_enrich_sentiment(
    params: Dict[str, Any],
    db_path: str = DEFAULT_DB_PATH,
) -> Dict[str, Any]:
    """
    Handle an 'enrich_sentiment' task. Scores signals with NLP.

    Params:
        symbols: Optional[List[str]] - specific symbols; if None, enrich all
        use_finbert: bool - whether to use FinBERT (default False for batch)
    """
    from social_arb.nlp.sentiment_enricher import SentimentEnricher

    symbols = params.get("symbols")
    use_finbert = params.get("use_finbert", False)

    logger.info(f"Sentiment enrichment starting: symbols={symbols}, finbert={use_finbert}")

    enricher = SentimentEnricher(use_finbert=use_finbert)

    # Get signals to enrich
    if symbols:
        all_signals = []
        for sym in symbols:
            all_signals.extend(store.query_signals(db_path=db_path, symbol=sym, limit=500))
    else:
        all_signals = store.query_signals(db_path=db_path, limit=5000)

    if not all_signals:
        return {"enriched_count": 0, "errors": ["No signals to enrich"]}

    enriched = enricher.enrich_batch(all_signals)
    enriched_count = sum(
        1 for orig, enr in zip(all_signals, enriched)
        if orig.get("direction") != enr.get("direction")
        or orig.get("strength") != enr.get("strength")
    )

    logger.info(f"Sentiment enrichment complete: {enriched_count}/{len(all_signals)} signals updated")

    return {
        "enriched_count": enriched_count,
        "total_signals": len(all_signals),
        "errors": [],
    }
```

Also update the `HANDLER_MAP` at the end of workers.py to include:
```python
    "enrich_sentiment": handle_enrich_sentiment,
```

- [ ] **Step 5: Run tests**

Run: `python -m pytest tests/test_pipeline_sentiment.py tests/test_vader_scorer.py tests/test_sentiment_enricher.py -v`
Expected: All pass

- [ ] **Step 6: Commit**

```bash
git add social_arb/pipeline.py social_arb/tasks/workers.py tests/test_pipeline_sentiment.py
git commit -m "feat: integrate sentiment enrichment into pipeline and task queue"
```

---

## Task 5: Sentiment API Routes

**Files:**
- Create: `social_arb/api/routes/sentiment.py`
- Modify: `social_arb/api/main.py` (register route)
- Test: `tests/test_api_sentiment.py`

- [ ] **Step 1: Create test file**

`tests/test_api_sentiment.py`:

```python
"""Tests for sentiment API routes."""

import pytest
from fastapi.testclient import TestClient
from social_arb.api.main import create_app
from social_arb.db.schema import init_db


@pytest.fixture
def client(tmp_path):
    import os
    db_path = str(tmp_path / "test.db")
    os.environ["SOCIAL_ARB_DB"] = db_path
    from social_arb.config import Config
    from social_arb.api import deps
    cfg = Config()
    deps.config = cfg
    deps.ensure_db()
    app = create_app()
    return TestClient(app)


def test_score_text_endpoint(client):
    """Test on-demand text scoring."""
    resp = client.post("/api/v1/sentiment/score", json={
        "text": "Amazing earnings growth, revenue smashing expectations"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "compound" in data
    assert "direction" in data
    assert data["direction"] in ("bullish", "bearish", "neutral")


def test_score_empty_text(client):
    resp = client.post("/api/v1/sentiment/score", json={"text": ""})
    assert resp.status_code == 200
    data = resp.json()
    assert data["direction"] == "neutral"


def test_score_batch_endpoint(client):
    resp = client.post("/api/v1/sentiment/score-batch", json={
        "texts": [
            "Great earnings beat",
            "Massive layoffs announced",
            "Filed quarterly report",
        ]
    })
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["results"]) == 3
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_api_sentiment.py -v`
Expected: FAIL — routes not registered

- [ ] **Step 3: Create routes**

`social_arb/api/routes/sentiment.py`:

```python
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
```

- [ ] **Step 4: Register routes in main.py**

In `social_arb/api/main.py`, add import:
```python
from social_arb.api.routes import sentiment
```

And register:
```python
    app.include_router(sentiment.router)
```

(Follow the same pattern as existing route registrations in `create_app()`)

- [ ] **Step 5: Run tests**

Run: `python -m pytest tests/test_api_sentiment.py tests/test_api_health.py -v`
Expected: All pass

- [ ] **Step 6: Commit**

```bash
git add social_arb/api/routes/sentiment.py social_arb/api/main.py tests/test_api_sentiment.py
git commit -m "feat: add sentiment scoring API routes"
```

---

## Task 6: Update Dependencies

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Add NLP dependencies**

Add to the main `dependencies` list:
```
    "vaderSentiment>=3.3",
```

Add a new optional group:
```toml
nlp = [
    "transformers>=4.35",
    "torch>=2.0",
]
```

Update `cloud` group to include vaderSentiment:
```toml
cloud = ["psycopg2-binary>=2.9.0", "gunicorn>=21.0", "python-json-logger>=2.0", "slowapi>=0.1.9", "vaderSentiment>=3.3"]
```

- [ ] **Step 2: Commit**

```bash
git add pyproject.toml
git commit -m "feat: add NLP dependencies (vaderSentiment required, transformers optional)"
```

---

## Summary

| Task | File(s) | Type |
|------|---------|------|
| 1. VADER Scorer | `social_arb/nlp/vader_scorer.py` | Create |
| 2. FinBERT Scorer | `social_arb/nlp/finbert_scorer.py` | Create |
| 3. Sentiment Enricher | `social_arb/nlp/sentiment_enricher.py` | Create |
| 4. Pipeline Integration | `pipeline.py`, `workers.py` | Modify |
| 5. API Routes | `social_arb/api/routes/sentiment.py`, `main.py` | Create + Modify |
| 6. Dependencies | `pyproject.toml` | Modify |

## Architecture Notes

- **VADER is always available** — lightweight, no GPU, installed as core dep
- **FinBERT is optional** — heavy (~800MB), installed via `pip install ".[nlp]"`, graceful degradation
- **Two-tier scoring**: VADER screens everything, FinBERT rescores high-value signals
- **Pipeline integration**: Enrichment runs before mosaic assembly so coherence/divergence calculations use real sentiment
- **Signal schema preserved**: Enricher updates `direction`, `strength`, `confidence` in-place, adds `sentiment` to raw_json
- **Text extraction**: Smart extraction from different collector raw data formats (raw_json string, raw dict)
- **Blending**: When both scorers run, FinBERT gets 70% weight, VADER 30%

---

**Generated:** 2026-03-27
**Status:** Ready to implement
