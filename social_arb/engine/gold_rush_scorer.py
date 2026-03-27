"""
Gold Rush Lifecycle Scorer

Camillo's Gold Rush model: trends go through Emerging → Validating → Confirmed → Saturated.
This engine computes lifecycle stage from signal patterns rather than manual assignment.

Lifecycle Stages:
- Emerging: <10 signals, 1-2 sources, recent cluster → novelty score
- Validating: 10-30 signals, 3+ sources, growing velocity → confirmation score
- Confirmed: 30+ signals, 4+ sources, high coherence mosaics → market noticing
- Saturated: Signal velocity declining, media saturation, mosaic coherence dropping

Logic:
The score method analyzes signal velocity, breadth (source diversity), recency, and
acceleration to assign the appropriate stage and compute stage-specific scores.
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


@dataclass
class GoldRushScorer:
    """Score which lifecycle stage a symbol's trend is in based on signal patterns."""

    def score(self, signals: List[Dict[str, Any]], mosaics: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Score lifecycle stage from signal patterns.

        Args:
            signals: List of signal dicts with keys: timestamp, source, strength, confidence, direction
            mosaics: List of mosaic card dicts with coherence_score

        Returns:
            {
                "stage": "emerging"|"validating"|"confirmed"|"saturated",
                "stage_score": float,  # 0-1, confidence in stage assignment
                "velocity": float,     # signal growth rate
                "breadth": float,      # source diversity (0-1)
                "recency": float,      # how recent the bulk of signals are (0-1)
                "signal_acceleration": float,  # is velocity increasing or decreasing (-1 to +1)
                "days_in_stage": int,
                "recommendation": str  # "enter"|"hold"|"monitor"|"exit"
            }
        """
        if not signals:
            return {
                "stage": "emerging",
                "stage_score": 0.0,
                "velocity": 0.0,
                "breadth": 0.0,
                "recency": 0.0,
                "signal_acceleration": 0.0,
                "days_in_stage": 0,
                "recommendation": "insufficient_data",
            }

        # Calculate metrics
        signal_count = len(signals)
        breadth = self._calculate_breadth(signals)
        velocity = self._calculate_velocity(signals)
        recency = self._calculate_recency(signals)
        acceleration = self._calculate_acceleration(signals)
        days_in_stage = self._calculate_days_in_stage(signals)
        avg_coherence = self._calculate_avg_coherence(mosaics)

        # Determine stage based on signal count, breadth, and coherence
        if signal_count < 10:
            stage = "emerging"
            stage_score = self._score_emerging(
                signal_count, breadth, velocity, recency
            )
            recommendation = "monitor" if stage_score > 0.5 else "watch"

        elif 10 <= signal_count < 30:
            stage = "validating"
            stage_score = self._score_validating(
                signal_count, breadth, velocity, acceleration, recency
            )
            recommendation = "enter" if stage_score > 0.65 else "monitor"

        elif 30 <= signal_count < 100:
            stage = "confirmed"
            stage_score = self._score_confirmed(
                signal_count, breadth, avg_coherence, velocity, acceleration
            )
            recommendation = "hold" if stage_score > 0.6 else "monitor"

        else:  # signal_count >= 100
            stage = "saturated"
            stage_score = self._score_saturated(velocity, acceleration, avg_coherence)
            recommendation = "exit" if acceleration < -0.3 else "monitor"

        return {
            "stage": stage,
            "stage_score": round(stage_score, 2),
            "velocity": round(velocity, 2),
            "breadth": round(breadth, 2),
            "recency": round(recency, 2),
            "signal_acceleration": round(acceleration, 2),
            "days_in_stage": days_in_stage,
            "recommendation": recommendation,
        }

    def _calculate_breadth(self, signals: List[Dict[str, Any]]) -> float:
        """Calculate source diversity (0-1). Max 1.0 at 4+ sources."""
        sources = set(s.get("source") for s in signals if s.get("source"))
        breadth = min(1.0, len(sources) / 4.0)  # Normalize to 4 sources max
        return breadth

    def _calculate_velocity(self, signals: List[Dict[str, Any]]) -> float:
        """Calculate signal growth rate as signals per day."""
        if len(signals) < 2:
            return 0.0

        timestamps = []
        for s in signals:
            ts = s.get("timestamp")
            if isinstance(ts, str):
                try:
                    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                    timestamps.append(dt)
                except:
                    continue
            elif isinstance(ts, datetime):
                timestamps.append(ts)

        if len(timestamps) < 2:
            return 0.0

        timestamps.sort()
        time_span = (timestamps[-1] - timestamps[0]).total_seconds() / 86400  # days
        if time_span == 0:
            return float(len(signals))  # All signals in one day
        velocity = len(signals) / time_span
        return min(100.0, velocity)  # Cap at 100 signals/day

    def _calculate_recency(self, signals: List[Dict[str, Any]]) -> float:
        """Calculate how recent the bulk of signals are (0-1)."""
        if not signals:
            return 0.0

        # Get most recent timestamp
        now = datetime.utcnow()
        recent_timestamps = []

        for s in signals:
            ts = s.get("timestamp")
            if isinstance(ts, str):
                try:
                    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                    recent_timestamps.append(dt)
                except:
                    continue
            elif isinstance(ts, datetime):
                recent_timestamps.append(ts)

        if not recent_timestamps:
            return 0.0

        recent_timestamps.sort(reverse=True)
        most_recent = recent_timestamps[0]

        # Decay: full score at < 1 day old, decays over 30 days
        days_old = (now - most_recent).total_seconds() / 86400
        if days_old < 1:
            recency = 1.0
        elif days_old > 30:
            recency = 0.0
        else:
            recency = 1.0 - (days_old / 30)

        return recency

    def _calculate_acceleration(self, signals: List[Dict[str, Any]]) -> float:
        """Calculate if velocity is increasing or decreasing (-1 to +1)."""
        if len(signals) < 6:
            return 0.0  # Not enough data

        # Split signals into two halves, compare velocity
        mid = len(signals) // 2
        first_half = signals[:mid]
        second_half = signals[mid:]

        vel_first = self._calculate_velocity(first_half)
        vel_second = self._calculate_velocity(second_half)

        if vel_first == 0:
            return 0.0

        acceleration = (vel_second - vel_first) / vel_first
        return max(-1.0, min(1.0, acceleration))  # Clamp to -1..+1

    def _calculate_days_in_stage(self, signals: List[Dict[str, Any]]) -> int:
        """Estimate days the trend has been in its current stage."""
        if len(signals) < 2:
            return 0

        timestamps = []
        for s in signals:
            ts = s.get("timestamp")
            if isinstance(ts, str):
                try:
                    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                    timestamps.append(dt)
                except:
                    continue
            elif isinstance(ts, datetime):
                timestamps.append(ts)

        if len(timestamps) < 2:
            return 0

        timestamps.sort()
        days = (timestamps[-1] - timestamps[0]).total_seconds() / 86400
        return int(days)

    def _calculate_avg_coherence(self, mosaics: List[Dict[str, Any]]) -> float:
        """Calculate average mosaic coherence score."""
        if not mosaics:
            return 0.5  # Neutral default

        coherence_scores = []
        for m in mosaics:
            cs = m.get("coherence_score")
            if cs is not None:
                coherence_scores.append(float(cs))

        if not coherence_scores:
            return 0.5

        avg = sum(coherence_scores) / len(coherence_scores)
        return min(1.0, avg / 100.0)  # Normalize to 0-1 if 0-100 scale

    def _score_emerging(
        self, count: int, breadth: float, velocity: float, recency: float
    ) -> float:
        """Score emerging stage: novelty matters most."""
        # High recency + low breadth (not yet discovered) = good emerging signal
        score = (recency * 0.5) + (breadth * 0.3) + (min(velocity, 5) / 5 * 0.2)
        return min(1.0, score)

    def _score_validating(
        self, count: int, breadth: float, velocity: float, accel: float, recency: float
    ) -> float:
        """Score validating stage: confirmation + acceleration."""
        # Accelerating velocity + growing breadth = strong validation signal
        accel_factor = (accel + 1.0) / 2.0  # Normalize -1..+1 to 0..1
        score = (breadth * 0.35) + (accel_factor * 0.35) + (recency * 0.2) + (min(velocity, 20) / 20 * 0.1)
        return min(1.0, score)

    def _score_confirmed(
        self, count: int, breadth: float, coherence: float, velocity: float, accel: float
    ) -> float:
        """Score confirmed stage: high breadth + coherence matters most."""
        # Multiple sources agreeing (high breadth + coherence) = confirmed
        score = (breadth * 0.4) + (coherence * 0.35) + (min(velocity, 30) / 30 * 0.15) + (max(0, accel) * 0.1)
        return min(1.0, score)

    def _score_saturated(self, velocity: float, accel: float, coherence: float) -> float:
        """Score saturated stage: declining velocity = exit signal."""
        # Negative acceleration + declining velocity = saturation
        decline_factor = max(0, -accel)  # Higher = more negative acceleration
        score = (decline_factor * 0.5) + ((1.0 - min(velocity, 50) / 50) * 0.3) + (coherence * 0.2)
        return min(1.0, score)
