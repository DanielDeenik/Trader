"""DeFi TVL collector via DeFi Llama API. Free, no auth required."""

import logging
from datetime import datetime
from typing import List, Dict, Any

import requests

from social_arb.collectors.base import BaseCollector, CollectorResult

logger = logging.getLogger(__name__)

PROTOCOL_MAP = {
    "AAVE": "aave",
    "UNI": "uniswap",
    "LIDO": "lido",
    "MAKER": "makerdao",
    "COMPOUND": "compound-finance",
    "CURVE": "curve-dex",
    "EIGENLAYER": "eigenlayer",
    "ETHENA": "ethena",
    "PENDLE": "pendle",
    "MORPHO": "morpho",
}

BASE_URL = "https://api.llama.fi"


class DeFiLlamaCollector(BaseCollector):

    @property
    def source_name(self) -> str:
        return "defillama"

    def _get_all_protocols(self) -> Dict[str, Any]:
        """Fetch summary data for all protocols."""
        try:
            url = f"{BASE_URL}/protocols"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.warning(f"[defillama] Failed to fetch all protocols: {e}")
            return {}

    def _calculate_tvl_direction(self, tvl_history: list) -> str:
        """Determine direction based on TVL historical trend."""
        if not tvl_history or len(tvl_history) < 2:
            return "neutral"

        # Get last entry and entry from 7 days ago (if available)
        current_tvl = tvl_history[-1].get("totalLiquidityUSD", 0)

        # Find entry approximately 7 days ago
        tvl_7d_ago = None
        if len(tvl_history) > 7:
            tvl_7d_ago = tvl_history[-7].get("totalLiquidityUSD", 0)

        if tvl_7d_ago is None or tvl_7d_ago == 0:
            return "neutral"

        change_pct = ((current_tvl - tvl_7d_ago) / tvl_7d_ago) * 100

        if change_pct > 5:
            return "bullish"
        elif change_pct < -5:
            return "bearish"
        else:
            return "neutral"

    def _calculate_tvl_change_7d(self, tvl_history: list) -> float:
        """Calculate 7-day TVL percentage change."""
        if not tvl_history or len(tvl_history) < 2:
            return None

        current_tvl = tvl_history[-1].get("totalLiquidityUSD", 0)
        tvl_7d_ago = None

        if len(tvl_history) > 7:
            tvl_7d_ago = tvl_history[-7].get("totalLiquidityUSD", 0)

        if tvl_7d_ago is None or tvl_7d_ago == 0:
            return None

        return ((current_tvl - tvl_7d_ago) / tvl_7d_ago) * 100

    def collect(self, symbols: List[str], **kwargs) -> CollectorResult:
        signals = []
        errors = []
        scanned = []

        # Get all protocols for context
        all_protocols_data = self._get_all_protocols()

        for symbol in symbols:
            try:
                # Map symbol to DeFi Llama protocol name
                if symbol not in PROTOCOL_MAP:
                    errors.append(f"{symbol}: not in PROTOCOL_MAP")
                    logger.warning(f"[defillama] {symbol} not in PROTOCOL_MAP")
                    continue

                protocol_name = PROTOCOL_MAP[symbol]

                # Fetch protocol-specific data
                url = f"{BASE_URL}/protocol/{protocol_name}"
                response = requests.get(url, timeout=30)
                response.raise_for_status()
                data = response.json()

                scanned.append(symbol)

                # Extract TVL data
                tvl_history = data.get("tvl", [])
                current_chain_tvls = data.get("currentChainTvls", {})
                chain_tvls = data.get("chainTvls", {})
                category = data.get("category")

                if not tvl_history:
                    errors.append(f"{symbol}: TVL data unavailable")
                    logger.warning(f"[defillama] {symbol}: TVL data unavailable")
                    continue

                # Current TVL is the latest entry
                current_tvl = tvl_history[-1].get("totalLiquidityUSD", 0)

                if current_tvl == 0:
                    errors.append(f"{symbol}: Current TVL is zero")
                    logger.warning(f"[defillama] {symbol}: Current TVL is zero")
                    continue

                # Calculate TVL changes from historical data
                tvl_change_7d = self._calculate_tvl_change_7d(tvl_history)
                tvl_change_1d = None
                if len(tvl_history) > 1:
                    prev_tvl = tvl_history[-2].get("totalLiquidityUSD", 0)
                    if prev_tvl > 0:
                        tvl_change_1d = ((current_tvl - prev_tvl) / prev_tvl) * 100

                # Normalize strength: TVL relative to a baseline (arbitrary 1B baseline)
                tvl_baseline = 1_000_000_000  # $1B baseline
                strength = min(1.0, current_tvl / tvl_baseline) if current_tvl > 0 else 0.1

                # Determine direction based on trend
                direction = self._calculate_tvl_direction(tvl_history)

                # Create signal
                signal = {
                    "timestamp": datetime.utcnow().isoformat(),
                    "symbol": symbol,
                    "source": "defillama",
                    "signal_type": "tvl_metric",
                    "direction": direction,
                    "strength": strength,
                    "confidence": 0.8,
                    "data_class": "public",
                    "raw": {
                        "tvl": current_tvl,
                        "tvl_change_1d": tvl_change_1d,
                        "tvl_change_7d": tvl_change_7d,
                        "category": category,
                        "chains": list(current_chain_tvls.keys()) if current_chain_tvls else [],
                    },
                }

                signals.append(signal)
                logger.info(f"[defillama] {symbol} ({protocol_name}): TVL=${current_tvl:,.0f}, 7d change={tvl_change_7d}%, category={category}")

            except requests.exceptions.RequestException as e:
                errors.append(f"{symbol}: request failed - {str(e)}")
                logger.error(f"[defillama] {symbol} request failed: {e}")
            except Exception as e:
                errors.append(f"{symbol}: {str(e)}")
                logger.error(f"[defillama] {symbol} failed: {e}")

        return CollectorResult(
            source="defillama",
            signals=signals,
            errors=errors,
            symbols_scanned=scanned,
        )
