"""Crypto price collector via CoinGecko API. Free, no auth required."""

import logging
import time
from datetime import datetime
from typing import List

import requests

from social_arb.collectors.base import BaseCollector, CollectorResult

logger = logging.getLogger(__name__)

TOKEN_MAP = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "SOL": "solana",
    "AVAX": "avalanche-2",
    "LINK": "chainlink",
    "AAVE": "aave",
    "UNI": "uniswap",
    "ARB": "arbitrum",
    "OP": "optimism",
    "MATIC": "matic-network",
    "CRV": "curve-dao-token",
    "LIDO": "lido",
    "MKR": "maker",
    "COMP": "compound-governance-token",
    "DOGE": "dogecoin",
    "ADA": "cardano",
    "NEAR": "near",
    "FIL": "filecoin",
    "ATOM": "cosmos",
}

BASE_URL = "https://api.coingecko.com/api/v3"
RATE_LIMIT_DELAY = 0.2  # 200ms delay between requests


class CoinGeckoCollector(BaseCollector):

    @property
    def source_name(self) -> str:
        return "coingecko"

    def collect(self, symbols: List[str], **kwargs) -> CollectorResult:
        signals = []
        errors = []
        scanned = []

        for symbol in symbols:
            try:
                # Map symbol to CoinGecko ID
                if symbol not in TOKEN_MAP:
                    errors.append(f"{symbol}: not in TOKEN_MAP")
                    logger.warning(f"[coingecko] {symbol} not in TOKEN_MAP")
                    continue

                gecko_id = TOKEN_MAP[symbol]

                # Fetch coin data from CoinGecko
                url = f"{BASE_URL}/coins/{gecko_id}"
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                data = response.json()

                scanned.append(symbol)

                # Extract relevant fields
                market_data = data.get("market_data", {})
                current_price = market_data.get("current_price", {}).get("usd")
                market_cap = market_data.get("market_cap", {}).get("usd")
                volume_24h = market_data.get("total_volume", {}).get("usd")
                price_change_24h = market_data.get("price_change_percentage_24h")
                price_change_7d = market_data.get("price_change_percentage_7d")
                price_change_30d = market_data.get("price_change_percentage_30d")
                market_cap_rank = data.get("market_cap_rank")

                if current_price is None:
                    errors.append(f"{symbol}: price data unavailable")
                    logger.warning(f"[coingecko] {symbol}: price data unavailable")
                    continue

                # Determine direction based on 24h change
                if price_change_24h is not None:
                    if price_change_24h > 2:
                        direction = "bullish"
                    elif price_change_24h < -2:
                        direction = "bearish"
                    else:
                        direction = "neutral"
                else:
                    direction = "neutral"

                # Calculate strength: normalized absolute change
                strength = 0.0
                if price_change_24h is not None:
                    strength = min(1.0, abs(price_change_24h) / 10)

                # Create price action signal
                signal = {
                    "timestamp": datetime.utcnow().isoformat(),
                    "symbol": symbol,
                    "source": "coingecko",
                    "signal_type": "price_action",
                    "direction": direction,
                    "strength": strength,
                    "confidence": 0.85,
                    "data_class": "public",
                    "raw": {
                        "price": current_price,
                        "market_cap": market_cap,
                        "volume_24h": volume_24h,
                        "price_change_24h": price_change_24h,
                        "price_change_7d": price_change_7d,
                        "price_change_30d": price_change_30d,
                        "market_cap_rank": market_cap_rank,
                    },
                }

                signals.append(signal)

                # Volume spike signal
                if volume_24h is not None and market_cap is not None and market_cap > 0:
                    volume_to_mcap = volume_24h / market_cap
                    if volume_to_mcap > 0.3:
                        vol_direction = "bullish" if price_change_24h and price_change_24h > 0 else "bearish"
                        signals.append({
                            "timestamp": datetime.utcnow().isoformat(),
                            "symbol": symbol,
                            "source": "coingecko",
                            "signal_type": "volume_spike",
                            "direction": vol_direction,
                            "strength": min(1.0, volume_to_mcap / 0.5),
                            "confidence": 0.7,
                            "data_class": "public",
                            "raw": {"volume_24h": volume_24h, "volume_to_mcap_ratio": volume_to_mcap},
                        })

                # Market cap change signal
                if price_change_7d is not None:
                    mcap_direction = "bullish" if price_change_7d > 0 else "bearish"
                    signals.append({
                        "timestamp": datetime.utcnow().isoformat(),
                        "symbol": symbol,
                        "source": "coingecko",
                        "signal_type": "market_cap_change",
                        "direction": mcap_direction,
                        "strength": min(1.0, abs(price_change_7d) / 20),
                        "confidence": 0.75,
                        "data_class": "public",
                        "raw": {"price_change_7d": price_change_7d, "market_cap_rank": market_cap_rank},
                    })

                # Fetch historical OHLCV data (30 days)
                time.sleep(RATE_LIMIT_DELAY)
                chart_url = f"{BASE_URL}/coins/{gecko_id}/market_chart?vs_currency=usd&days=30"
                chart_response = requests.get(chart_url, timeout=10)
                chart_response.raise_for_status()
                chart_data = chart_response.json()

                prices = chart_data.get("prices", [])
                for price_point in prices:
                    ts_ms, price_val = price_point
                    price_date = datetime.utcfromtimestamp(ts_ms / 1000).strftime("%Y-%m-%d")
                    # Create daily OHLCV signals (simplified: using price as close)
                    signals.append({
                        "timestamp": price_date,
                        "symbol": symbol,
                        "source": "coingecko",
                        "signal_type": "ohlcv",
                        "direction": "neutral",
                        "strength": 0.5,
                        "confidence": 0.6,
                        "close": float(price_val),
                        "data_class": "public",
                        "raw": {"price": price_val},
                    })

                logger.info(f"[coingecko] {symbol} ({gecko_id}): price=${current_price}, 24h={price_change_24h}%, {len(prices)} OHLCV bars")

                # Rate limiting
                time.sleep(RATE_LIMIT_DELAY)

            except requests.exceptions.RequestException as e:
                errors.append(f"{symbol}: request failed - {str(e)}")
                logger.error(f"[coingecko] {symbol} request failed: {e}")
            except Exception as e:
                errors.append(f"{symbol}: {str(e)}")
                logger.error(f"[coingecko] {symbol} failed: {e}")

        return CollectorResult(
            source="coingecko",
            signals=signals,
            errors=errors,
            symbols_scanned=scanned,
        )
