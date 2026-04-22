"""Crypto sentiment collector via CoinGecko trending and community data. Free, no auth required."""

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


class CryptoSentimentCollector(BaseCollector):

    @property
    def source_name(self) -> str:
        return "crypto_sentiment"

    def collect(self, symbols: List[str], **kwargs) -> CollectorResult:
        signals = []
        errors = []
        scanned = []

        # Fetch trending coins globally
        trending_coins = self._get_trending_coins()
        trending_ids = {coin.get("item", {}).get("id") for coin in trending_coins}

        for symbol in symbols:
            try:
                # Map symbol to CoinGecko ID
                if symbol not in TOKEN_MAP:
                    errors.append(f"{symbol}: not in TOKEN_MAP")
                    logger.warning(f"[crypto_sentiment] {symbol} not in TOKEN_MAP")
                    continue

                gecko_id = TOKEN_MAP[symbol]
                scanned.append(symbol)

                # Fetch community and developer data
                url = f"{BASE_URL}/coins/{gecko_id}"
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                data = response.json()

                community_data = data.get("community_data", {})
                developer_data = data.get("developer_data", {})

                # Social growth signals
                twitter_followers = community_data.get("twitter_followers")
                reddit_subscribers = community_data.get("reddit_subscribers")
                facebook_likes = community_data.get("facebook_likes")

                # Create social growth signal if we have data
                if twitter_followers is not None or reddit_subscribers is not None:
                    total_social = (twitter_followers or 0) + (reddit_subscribers or 0) + (facebook_likes or 0)

                    # Baseline for social strength (arbitrary: 1M combined followers = 1.0 strength)
                    social_baseline = 1_000_000
                    strength = min(1.0, total_social / social_baseline) if total_social > 0 else 0.1

                    signals.append({
                        "timestamp": datetime.utcnow().isoformat(),
                        "symbol": symbol,
                        "source": "crypto_sentiment",
                        "signal_type": "social_growth",
                        "direction": "bullish" if total_social > social_baseline * 0.5 else "neutral",
                        "strength": strength,
                        "confidence": 0.65,
                        "data_class": "public",
                        "raw": {
                            "twitter_followers": twitter_followers,
                            "reddit_subscribers": reddit_subscribers,
                            "facebook_likes": facebook_likes,
                            "total_social": total_social,
                        },
                    })

                # Trending coin signal
                if gecko_id in trending_ids:
                    signals.append({
                        "timestamp": datetime.utcnow().isoformat(),
                        "symbol": symbol,
                        "source": "crypto_sentiment",
                        "signal_type": "trending_coin",
                        "direction": "bullish",
                        "strength": 0.9,
                        "confidence": 0.95,
                        "data_class": "public",
                        "raw": {"trending": True, "gecko_id": gecko_id},
                    })

                # Developer activity signal
                github_repos = developer_data.get("repos", {}).get("repo_url")
                github_stars = developer_data.get("stars")
                github_followers = developer_data.get("followers")
                github_commits_4w = developer_data.get("last_4_weeks_commit_activity")

                if github_commits_4w is not None and github_commits_4w > 0:
                    # Higher commit activity = more development
                    dev_strength = min(1.0, github_commits_4w / 100)  # Normalize by assuming 100+ commits is active
                    signals.append({
                        "timestamp": datetime.utcnow().isoformat(),
                        "symbol": symbol,
                        "source": "crypto_sentiment",
                        "signal_type": "developer_activity",
                        "direction": "bullish",
                        "strength": dev_strength,
                        "confidence": 0.7,
                        "data_class": "public",
                        "raw": {
                            "github_commits_4w": github_commits_4w,
                            "github_stars": github_stars,
                            "github_followers": github_followers,
                        },
                    })

                logger.info(
                    f"[crypto_sentiment] {symbol} ({gecko_id}): "
                    f"twitter={twitter_followers}, reddit={reddit_subscribers}, trending={gecko_id in trending_ids}"
                )

                # Rate limiting
                time.sleep(RATE_LIMIT_DELAY)

            except requests.exceptions.RequestException as e:
                errors.append(f"{symbol}: request failed - {str(e)}")
                logger.error(f"[crypto_sentiment] {symbol} request failed: {e}")
            except Exception as e:
                errors.append(f"{symbol}: {str(e)}")
                logger.error(f"[crypto_sentiment] {symbol} failed: {e}")

        return CollectorResult(
            source="crypto_sentiment",
            signals=signals,
            errors=errors,
            symbols_scanned=scanned,
        )

    def _get_trending_coins(self) -> List[dict]:
        """Fetch trending coins from CoinGecko."""
        try:
            url = f"{BASE_URL}/search/trending"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            return data.get("coins", [])
        except Exception as e:
            logger.warning(f"[crypto_sentiment] Failed to fetch trending coins: {e}")
            return []
