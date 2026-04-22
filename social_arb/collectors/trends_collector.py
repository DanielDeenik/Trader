"""Google Trends collector via pytrends. No API key required."""

import logging
from datetime import datetime
from typing import List

from social_arb.collectors.base import BaseCollector, CollectorResult

logger = logging.getLogger(__name__)


class TrendsCollector(BaseCollector):

    @property
    def source_name(self) -> str:
        return "google_trends"

    def collect(self, symbols: List[str], timeframe: str = "today 3-m", **kwargs) -> CollectorResult:
        signals = []
        errors = []

        try:
            from pytrends.request import TrendReq
            pytrends = TrendReq(hl="en-US", tz=360)

            for i in range(0, len(symbols), 5):
                batch = symbols[i:i+5]
                try:
                    pytrends.build_payload(batch, timeframe=timeframe)
                    interest = pytrends.interest_over_time()

                    if interest.empty:
                        errors.append(f"No trend data for {batch}")
                        continue

                    for symbol in batch:
                        if symbol not in interest.columns:
                            continue

                        series = interest[symbol]
                        current = float(series.iloc[-1])
                        avg = float(series.mean())
                        trend_strength = (current - avg) / avg if avg > 0 else 0

                        signals.append({
                            "timestamp": datetime.utcnow().isoformat(),
                            "symbol": symbol,
                            "source": "google_trends",
                            "signal_type": "search_interest",
                            "direction": "bullish" if trend_strength > 0.2 else ("bearish" if trend_strength < -0.2 else "neutral"),
                            "strength": min(1.0, abs(trend_strength)),
                            "confidence": 0.6,
                            "data_class": "public",
                            "raw": {
                                "current_interest": current,
                                "avg_interest": avg,
                                "trend_strength": trend_strength,
                            },
                        })

                except Exception as e:
                    errors.append(f"Trends batch {batch}: {str(e)}")
                    logger.error(f"[trends] batch {batch} failed: {e}")

        except ImportError:
            errors.append("pytrends not installed: pip install pytrends")

        return CollectorResult(
            source="google_trends",
            signals=signals,
            errors=errors,
            symbols_scanned=symbols,
        )
