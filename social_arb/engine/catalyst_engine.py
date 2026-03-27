"""
Catalyst Timeline Engine

Camillo emphasizes identifying catalysts — events that will force the market to reprice
based on the information asymmetry. This engine scans signal data for catalyst keywords
and clusters them into probable events.

Catalyst Types:
- earnings: "earnings", "EPS", "revenue", "quarterly", "guidance"
- product: "launch", "release", "announcement", "FDA", "approval"
- regulatory: "regulation", "SEC", "compliance", "ruling", "ban"
- partnership: "partnership", "acquisition", "merger", "deal"
- social_viral: signals from reddit/google_trends with high strength
- macro: "inflation", "fed", "interest rate", "recession"
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class CatalystEngine:
    """Identify potential catalysts from signal data and estimate timing."""

    # Keywords for each catalyst type
    EARNINGS_KEYWORDS = {"earnings", "eps", "revenue", "quarterly", "guidance", "report"}
    PRODUCT_KEYWORDS = {"launch", "release", "announcement", "fda", "approval", "product", "beta"}
    REGULATORY_KEYWORDS = {"regulation", "sec", "compliance", "ruling", "ban", "fine", "lawsuit"}
    PARTNERSHIP_KEYWORDS = {"partnership", "acquisition", "merger", "deal", "collaboration", "integration"}
    MACRO_KEYWORDS = {"inflation", "fed", "interest rate", "recession", "gdp", "unemployment", "fiscal"}

    def analyze(self, signals: List[Dict[str, Any]], symbol: str) -> Dict[str, Any]:
        """
        Identify and cluster catalysts from signals.

        Args:
            signals: List of signal dicts with raw_json field containing text
            symbol: Stock symbol for context

        Returns:
            {
                "catalysts": [
                    {
                        "type": "earnings"|"product_launch"|"regulatory"|"partnership"|"social_viral"|"macro",
                        "description": str,
                        "confidence": float,  # 0-1
                        "estimated_impact": "high"|"medium"|"low",
                        "signal_ids": list[int],  # which signals suggest this catalyst
                        "detected_at": str,
                    }
                ],
                "catalyst_count": int,
                "strongest_catalyst": dict|None,
                "catalyst_density": float,  # catalysts per signal, higher = more event-driven
            }
        """
        if not signals:
            return {
                "catalysts": [],
                "catalyst_count": 0,
                "strongest_catalyst": None,
                "catalyst_density": 0.0,
            }

        catalysts = []
        catalyst_map = {}  # Type -> list of (signal_ids, strength)

        # Scan signals for catalyst keywords
        for signal in signals:
            raw_json = signal.get("raw_json", {})
            if isinstance(raw_json, str):
                try:
                    import json
                    raw_json = json.loads(raw_json)
                except:
                    raw_json = {"text": raw_json}

            text = self._extract_text(raw_json, signal).lower()
            signal_id = signal.get("id")
            strength = float(signal.get("strength", 0.5))
            confidence = float(signal.get("confidence", 0.5))

            # Detect catalyst types
            detected_types = self._detect_catalyst_types(text)

            for cat_type in detected_types:
                if cat_type not in catalyst_map:
                    catalyst_map[cat_type] = []
                catalyst_map[cat_type].append((signal_id, strength, confidence))

            # Check for social viral catalyst
            if signal.get("source") in ("reddit", "google_trends") and strength > 0.7:
                if "social_viral" not in catalyst_map:
                    catalyst_map["social_viral"] = []
                catalyst_map["social_viral"].append((signal_id, strength, confidence))

        # Build catalyst objects from clusters
        for cat_type, signal_data in catalyst_map.items():
            signal_ids = [s[0] for s in signal_data if s[0]]
            avg_strength = sum(s[1] for s in signal_data) / len(signal_data) if signal_data else 0.5
            avg_confidence = sum(s[2] for s in signal_data) / len(signal_data) if signal_data else 0.5
            signal_count = len(signal_data)

            # Confidence increases with signal count and average confidence
            catalyst_confidence = min(1.0, (avg_confidence * 0.6) + (min(signal_count, 5) / 5 * 0.4))

            # Impact assessment based on type
            if cat_type in ("earnings", "product_launch", "regulatory"):
                impact = "high"
                base_impact = 0.9
            elif cat_type in ("partnership", "macro"):
                impact = "medium"
                base_impact = 0.6
            else:  # social_viral
                impact = "medium" if strength > 0.7 else "low"
                base_impact = 0.5

            # Description
            description = self._build_catalyst_description(cat_type, signal_count, avg_strength)

            catalyst = {
                "type": cat_type,
                "description": description,
                "confidence": round(catalyst_confidence, 2),
                "estimated_impact": impact,
                "signal_ids": signal_ids,
                "detected_at": datetime.utcnow().isoformat(),
            }
            catalysts.append(catalyst)

        # Sort by impact and confidence
        catalysts.sort(
            key=lambda x: (
                {"high": 3, "medium": 2, "low": 1}.get(x["estimated_impact"], 0),
                x["confidence"],
            ),
            reverse=True,
        )

        strongest = catalysts[0] if catalysts else None
        catalyst_density = len(catalysts) / len(signals) if signals else 0.0

        return {
            "catalysts": catalysts,
            "catalyst_count": len(catalysts),
            "strongest_catalyst": strongest,
            "catalyst_density": round(catalyst_density, 2),
        }

    def _extract_text(self, raw_json: Dict[str, Any], signal: Dict[str, Any]) -> str:
        """Extract text from raw_json in various formats."""
        text_parts = []

        # Try common fields
        for field in ["text", "title", "body", "content", "comment", "post"]:
            if field in raw_json:
                text_parts.append(str(raw_json[field]))

        # Also check signal fields
        if "raw_text" in signal:
            text_parts.append(str(signal["raw_text"]))

        return " ".join(text_parts)

    def _detect_catalyst_types(self, text: str) -> List[str]:
        """Detect which catalyst types are present in text."""
        detected = []

        if any(kw in text for kw in self.EARNINGS_KEYWORDS):
            detected.append("earnings")

        if any(kw in text for kw in self.PRODUCT_KEYWORDS):
            detected.append("product_launch")

        if any(kw in text for kw in self.REGULATORY_KEYWORDS):
            detected.append("regulatory")

        if any(kw in text for kw in self.PARTNERSHIP_KEYWORDS):
            detected.append("partnership")

        if any(kw in text for kw in self.MACRO_KEYWORDS):
            detected.append("macro")

        return detected

    def _build_catalyst_description(self, cat_type: str, signal_count: int, strength: float) -> str:
        """Build human-readable catalyst description."""
        type_names = {
            "earnings": "Earnings Event",
            "product_launch": "Product Launch/Announcement",
            "regulatory": "Regulatory Event",
            "partnership": "Partnership/M&A",
            "social_viral": "Social Viral Moment",
            "macro": "Macroeconomic Event",
        }

        base = type_names.get(cat_type, "Unknown Catalyst")
        strength_label = "high-strength" if strength > 0.7 else "moderate-strength" if strength > 0.4 else "low-strength"

        return f"{base} ({strength_label}, detected in {signal_count} signal(s))"
