"""Real market data collector via yfinance. No demo mode."""

import logging
from datetime import datetime
from typing import List

import yfinance as yf

from social_arb.collectors.base import BaseCollector, CollectorResult

logger = logging.getLogger(__name__)


class YFinanceCollector(BaseCollector):

    @property
    def source_name(self) -> str:
        return "yfinance"

    def collect(self, symbols: List[str], period: str = "1mo", **kwargs) -> CollectorResult:
        signals = []
        errors = []
        scanned = []

        for symbol in symbols:
            try:
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period=period)

                if hist.empty:
                    errors.append(f"{symbol}: no data returned")
                    continue

                scanned.append(symbol)

                # OHLCV bars
                for date, row in hist.iterrows():
                    signals.append({
                        "timestamp": date.strftime("%Y-%m-%d"),
                        "symbol": symbol,
                        "source": "yfinance",
                        "signal_type": "ohlcv",
                        "direction": "bullish" if row["Close"] > row["Open"] else "bearish",
                        "strength": abs(row["Close"] - row["Open"]) / row["Open"] if row["Open"] > 0 else 0,
                        "confidence": min(1.0, row["Volume"] / 1e7) if row["Volume"] > 0 else 0.1,
                        "open": float(row["Open"]),
                        "high": float(row["High"]),
                        "low": float(row["Low"]),
                        "close": float(row["Close"]),
                        "volume": int(row["Volume"]),
                        "data_class": "public",
                    })

                # Latest price momentum signal
                if len(hist) > 1:
                    latest = hist.iloc[-1]
                    prev = hist.iloc[-2]
                    change_pct = (latest["Close"] - prev["Close"]) / prev["Close"] if prev["Close"] > 0 else 0

                    signals.append({
                        "timestamp": datetime.utcnow().isoformat(),
                        "symbol": symbol,
                        "source": "yfinance",
                        "signal_type": "price_momentum",
                        "direction": "bullish" if change_pct > 0.01 else ("bearish" if change_pct < -0.01 else "neutral"),
                        "strength": min(1.0, abs(change_pct) * 10),
                        "confidence": 0.9,
                        "data_class": "public",
                        "raw": {"change_pct": change_pct, "close": float(latest["Close"]), "volume": int(latest["Volume"])},
                    })

                logger.info(f"[yfinance] {symbol}: {len(hist)} bars collected")

            except Exception as e:
                errors.append(f"{symbol}: {str(e)}")
                logger.error(f"[yfinance] {symbol} failed: {e}")

        return CollectorResult(
            source="yfinance",
            signals=signals,
            errors=errors,
            symbols_scanned=scanned,
        )
