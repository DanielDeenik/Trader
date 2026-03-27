"""
Information Asymmetry Scanner

Camillo's core insight: profit comes from information asymmetry — knowing something
before the market prices it in. This engine measures the gap between social/retail
signals and institutional/market signals.

Key insight: High social velocity + low price movement = high asymmetry = opportunity.

Sources:
- Social: reddit, google_trends
- Institutional: sec_edgar, yfinance (price/volume)
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


@dataclass
class AsymmetryScanner:
    """Measure information asymmetry between social/retail signals and institutional/market signals."""

    def scan(self, signals: List[Dict[str, Any]], ohlcv: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Measure information asymmetry.

        Args:
            signals: List of signal dicts with keys: timestamp, source, strength, confidence
            ohlcv: List of OHLCV dicts with keys: timestamp, open, high, low, close, volume

        Returns:
            {
                "asymmetry_score": float,  # 0-1, higher = more asymmetry = more opportunity
                "social_signal_strength": float,  # aggregate social signal strength
                "market_reaction": float,  # how much the market has moved
                "gap": float,  # social signals vs market movement delta
                "social_sources": list[str],  # which social sources are firing
                "institutional_sources": list[str],  # which institutional sources
                "social_velocity": float,  # rate of social signal growth
                "price_velocity": float,  # rate of price movement
                "thesis": str,  # "retail_ahead"|"institutional_ahead"|"aligned"|"no_signal"
                "window_hours": int  # time window analyzed
            }
        """
        if not signals and not ohlcv:
            return {
                "asymmetry_score": 0.0,
                "social_signal_strength": 0.0,
                "market_reaction": 0.0,
                "gap": 0.0,
                "social_sources": [],
                "institutional_sources": [],
                "social_velocity": 0.0,
                "price_velocity": 0.0,
                "thesis": "no_signal",
                "window_hours": 0,
            }

        # Split signals by source type
        social_signals = [s for s in signals if s.get("source") in ("reddit", "google_trends")]
        inst_signals = [s for s in signals if s.get("source") in ("sec_edgar", "yfinance", "coingecko")]

        # Calculate social metrics
        social_strength = self._aggregate_strength(social_signals)
        social_sources = list(set(s.get("source") for s in social_signals if s.get("source")))
        social_velocity = self._calculate_velocity(social_signals)

        # Calculate market/institutional metrics
        inst_sources = list(set(s.get("source") for s in inst_signals if s.get("source")))
        price_velocity = self._calculate_price_velocity(ohlcv)
        market_reaction = self._calculate_market_reaction(ohlcv)

        # Calculate gap: social velocity relative to price movement
        gap = social_velocity - price_velocity

        # Determine asymmetry thesis
        if social_velocity > price_velocity * 2.0 and social_strength > 0.6:
            thesis = "retail_ahead"  # Retail signals far ahead of market
            asymmetry_score = min(1.0, (gap / 10.0) * 0.8 + social_strength * 0.2)
        elif price_velocity > social_velocity * 2.0:
            thesis = "institutional_ahead"  # Market already moved, retail catching up
            asymmetry_score = max(0.0, 1.0 - (price_velocity / 10.0) * 0.5)
        elif abs(gap) < 2.0 and social_strength > 0.5:
            thesis = "aligned"  # Social and market aligned, might be too late
            asymmetry_score = 0.3 + (social_strength * 0.3)
        else:
            thesis = "no_signal"
            asymmetry_score = 0.2

        # Calculate time window
        window_hours = self._calculate_time_window(signals)

        return {
            "asymmetry_score": round(asymmetry_score, 2),
            "social_signal_strength": round(social_strength, 2),
            "market_reaction": round(market_reaction, 2),
            "gap": round(gap, 2),
            "social_sources": social_sources,
            "institutional_sources": inst_sources,
            "social_velocity": round(social_velocity, 2),
            "price_velocity": round(price_velocity, 2),
            "thesis": thesis,
            "window_hours": window_hours,
        }

    def _aggregate_strength(self, signals: List[Dict[str, Any]]) -> float:
        """Aggregate signal strength, weighted by confidence."""
        if not signals:
            return 0.0

        total_strength = 0.0
        total_weight = 0.0

        for s in signals:
            strength = float(s.get("strength", 0.5))
            confidence = float(s.get("confidence", 0.5))
            weight = confidence if confidence > 0 else 0.5
            total_strength += strength * weight
            total_weight += weight

        if total_weight == 0:
            return 0.0

        avg_strength = total_strength / total_weight
        return min(1.0, avg_strength)

    def _calculate_velocity(self, signals: List[Dict[str, Any]]) -> float:
        """Calculate signal growth rate (signals per hour)."""
        if len(signals) < 2:
            return 0.0

        timestamps = self._extract_timestamps(signals)
        if len(timestamps) < 2:
            return 0.0

        timestamps.sort()
        time_span_hours = (timestamps[-1] - timestamps[0]).total_seconds() / 3600
        if time_span_hours == 0:
            return float(len(signals))  # All signals in one hour

        velocity = len(signals) / time_span_hours
        return min(100.0, velocity)  # Cap at 100 signals/hour

    def _calculate_price_velocity(self, ohlcv: List[Dict[str, Any]]) -> float:
        """Calculate rate of price movement (% change per day)."""
        if len(ohlcv) < 2:
            return 0.0

        # Calculate daily returns
        prices = []
        timestamps = []

        for o in ohlcv:
            try:
                close = float(o.get("close", 0))
                if close > 0:
                    prices.append(close)
                    ts = o.get("timestamp")
                    if isinstance(ts, str):
                        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                        timestamps.append(dt)
                    elif isinstance(ts, datetime):
                        timestamps.append(ts)
            except:
                continue

        if len(prices) < 2:
            return 0.0

        # Calculate average daily return magnitude
        returns = []
        for i in range(1, len(prices)):
            ret = abs((prices[i] - prices[i - 1]) / prices[i - 1] * 100)
            returns.append(ret)

        if not returns:
            return 0.0

        avg_daily_return = sum(returns) / len(returns)
        return avg_daily_return

    def _calculate_market_reaction(self, ohlcv: List[Dict[str, Any]]) -> float:
        """Calculate total market movement over period."""
        if len(ohlcv) < 2:
            return 0.0

        try:
            start_close = float(ohlcv[0].get("close", 0))
            end_close = float(ohlcv[-1].get("close", 0))

            if start_close == 0:
                return 0.0

            return abs((end_close - start_close) / start_close * 100)
        except:
            return 0.0

    def _extract_timestamps(self, signals: List[Dict[str, Any]]) -> List[datetime]:
        """Extract and parse timestamps from signals."""
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
        return timestamps

    def _calculate_time_window(self, signals: List[Dict[str, Any]]) -> int:
        """Calculate time window in hours for analysis."""
        timestamps = self._extract_timestamps(signals)
        if len(timestamps) < 2:
            return 0

        timestamps.sort()
        hours = (timestamps[-1] - timestamps[0]).total_seconds() / 3600
        return int(hours)
