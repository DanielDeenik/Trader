"""Alert evaluation engine for monitoring signals, mosaics, and theses."""

import logging
from datetime import datetime
from uuid import uuid4
from typing import Optional

logger = logging.getLogger(__name__)


class AlertEngine:
    """Evaluates signals, mosaics, and theses against configured thresholds."""

    DEFAULT_THRESHOLDS = {
        "divergence_spike": 0.7,        # divergence_score above this
        "high_confidence_signal": 0.8,  # signal confidence above this
        "volume_spike": 0.9,            # unusual volume strength
        "thesis_approved": 0.0,         # any thesis approval (threshold ignored)
        "thesis_rejected": 0.0,         # any thesis rejection (threshold ignored)
        "thesis_status_change": 0.0,    # any status change (threshold ignored)
    }

    def __init__(self, thresholds: Optional[dict] = None):
        """Initialize with optional custom thresholds."""
        self.thresholds = {**self.DEFAULT_THRESHOLDS}
        if thresholds:
            self.thresholds.update(thresholds)
        self.recent_alerts = []  # In-memory store (max 100)

    def evaluate_signal(self, signal: dict) -> list[dict]:
        """
        Check a signal against thresholds. Return list of alert dicts.

        Signal expected to have:
        - symbol (str)
        - source (str)
        - direction (str: bullish/bearish/neutral)
        - confidence (float, 0-1)
        - strength (float, 0-1)
        - timestamp (str, ISO format)
        """
        alerts = []

        symbol = signal.get("symbol", "UNKNOWN")
        confidence = signal.get("confidence", 0)
        strength = signal.get("strength", 0)
        direction = signal.get("direction", "neutral")

        # High confidence signal alert
        if confidence >= self.thresholds["high_confidence_signal"]:
            alert = {
                "id": str(uuid4()),
                "type": "high_confidence_signal",
                "symbol": symbol,
                "message": f"High-confidence {direction} signal from {signal.get('source', '?')} (confidence: {confidence:.1%})",
                "severity": "warning",
                "timestamp": signal.get("timestamp", datetime.utcnow().isoformat()),
                "data": signal,
            }
            alerts.append(alert)
            self._store_alert(alert)

        # Volume/strength spike
        if strength >= self.thresholds["volume_spike"]:
            alert = {
                "id": str(uuid4()),
                "type": "volume_spike",
                "symbol": symbol,
                "message": f"Strong signal strength detected ({strength:.1%})",
                "severity": "info",
                "timestamp": signal.get("timestamp", datetime.utcnow().isoformat()),
                "data": signal,
            }
            alerts.append(alert)
            self._store_alert(alert)

        return alerts

    def evaluate_mosaic(self, mosaic: dict) -> list[dict]:
        """
        Check a mosaic against thresholds. Return list of alert dicts.

        Mosaic expected to have:
        - symbol (str)
        - domain (str)
        - divergence_strength (float, 0-1)
        - coherence_score (float, 0-1)
        """
        alerts = []

        symbol = mosaic.get("symbol", "UNKNOWN")
        divergence = mosaic.get("divergence_strength", 0)
        coherence = mosaic.get("coherence_score", 0)

        # Divergence spike alert
        if divergence >= self.thresholds["divergence_spike"]:
            alert = {
                "id": str(uuid4()),
                "type": "divergence_spike",
                "symbol": symbol,
                "message": f"Sentiment divergence spike in {mosaic.get('domain', '?')} domain (divergence: {divergence:.1%})",
                "severity": "critical",
                "timestamp": datetime.utcnow().isoformat(),
                "data": mosaic,
            }
            alerts.append(alert)
            self._store_alert(alert)

        return alerts

    def evaluate_thesis(self, thesis: dict, previous_status: Optional[str] = None) -> list[dict]:
        """
        Check a thesis for status changes. Return list of alert dicts.

        Thesis expected to have:
        - symbol (str)
        - domain (str)
        - status (str: pending_review/approved/rejected/deferred)
        - lifecycle_stage (str: emerging/validating/confirmed/saturated)
        """
        alerts = []

        symbol = thesis.get("symbol", "UNKNOWN")
        status = thesis.get("status", "unknown")
        lifecycle = thesis.get("lifecycle_stage", "unknown")

        # Status change alerts
        if previous_status and previous_status != status:
            if status == "approved":
                severity = "critical"
                msg_detail = "APPROVED"
            elif status == "rejected":
                severity = "warning"
                msg_detail = "REJECTED"
            else:
                severity = "info"
                msg_detail = f"Status changed to {status}"

            alert = {
                "id": str(uuid4()),
                "type": "thesis_status_change",
                "symbol": symbol,
                "message": f"Thesis {msg_detail} for {symbol} ({lifecycle})",
                "severity": severity,
                "timestamp": datetime.utcnow().isoformat(),
                "data": thesis,
            }
            alerts.append(alert)
            self._store_alert(alert)
        elif status == "approved" and not previous_status:
            # New approved thesis
            alert = {
                "id": str(uuid4()),
                "type": "thesis_approved",
                "symbol": symbol,
                "message": f"New thesis APPROVED for {symbol} ({lifecycle})",
                "severity": "critical",
                "timestamp": datetime.utcnow().isoformat(),
                "data": thesis,
            }
            alerts.append(alert)
            self._store_alert(alert)

        return alerts

    def _store_alert(self, alert: dict) -> None:
        """Store alert in memory (keep last 100)."""
        self.recent_alerts.insert(0, alert)
        if len(self.recent_alerts) > 100:
            self.recent_alerts = self.recent_alerts[:100]

    def get_recent_alerts(self, limit: int = 50) -> list[dict]:
        """Return recent alerts (most recent first)."""
        return self.recent_alerts[:limit]

    def clear_alerts(self) -> None:
        """Clear all stored alerts."""
        self.recent_alerts = []

    def update_thresholds(self, new_thresholds: dict) -> dict:
        """Update alert thresholds. Return updated config."""
        self.thresholds.update(new_thresholds)
        return self.thresholds

    def get_thresholds(self) -> dict:
        """Return current thresholds."""
        return dict(self.thresholds)
