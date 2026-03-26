"""Crypto price collector via CoinGecko API. Free, no auth required."""

import logging
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
}

BASE_URL = "https://api.coingecko.com/api/v3"


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

                # Determine direction based on 7d change
                if price_change_7d is not None:
                    if price_change_7d > 5:
                        direction = "bullish"
                    elif price_change_7d < -5:
                        direction = "bearish"
                    else:
                        direction = "neutral"
                else:
                    direction = "neutral"

                # Calculate strength: normalized absolute change
                strength = 0.0
                if price_change_7d is not None:
                    strength = min(1.0, abs(price_change_7d) / 20)

                # Create signal
                signal = {
                    "timestamp": datetime.utcnow().isoformat(),
                    "symbol": symbol,
                    "source": "coingecko",
                    "signal_type": "token_ohlcv",
                    "direction": direction,
                    "strength": strength,
                    "confidence": 0.8,
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
                logger.info(f"[coingecko] {symbol} ({gecko_id}): price=${current_price}, 7d={price_change_7d}%")

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
