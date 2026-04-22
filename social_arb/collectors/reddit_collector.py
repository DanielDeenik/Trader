"""Reddit signal collector using public JSON API. No API key required."""

import logging
import time
from datetime import datetime
from typing import List, Optional

import requests

from social_arb.collectors.base import BaseCollector, CollectorResult

logger = logging.getLogger(__name__)

REDDIT_BASE = "https://www.reddit.com"
HEADERS = {"User-Agent": "SocialArb/1.0 (information arbitrage research)"}


class RedditCollector(BaseCollector):
    """Collects social signals from Reddit public JSON endpoints."""

    @property
    def source_name(self) -> str:
        return "reddit"

    def collect(
        self,
        symbols: List[str],
        subreddits: Optional[List[str]] = None,
        limit: int = 25,
        **kwargs,
    ) -> CollectorResult:
        subreddits = subreddits or ["wallstreetbets", "stocks", "investing", "SecurityAnalysis"]
        signals = []
        errors = []

        for subreddit in subreddits:
            try:
                url = f"{REDDIT_BASE}/r/{subreddit}/hot.json?limit={limit}"
                resp = requests.get(url, headers=HEADERS, timeout=10)

                if resp.status_code == 429:
                    errors.append(f"rate_limit: r/{subreddit}")
                    time.sleep(2)
                    continue

                resp.raise_for_status()
                data = resp.json()
                posts = data.get("data", {}).get("children", [])

                for post in posts:
                    pd = post.get("data", {})
                    title = pd.get("title", "")
                    selftext = pd.get("selftext", "")
                    text = f"{title} {selftext}".upper()

                    for symbol in symbols:
                        sym_upper = symbol.upper()
                        if sym_upper in text or f"${sym_upper}" in text:
                            upvotes = pd.get("ups", 0)
                            comments = pd.get("num_comments", 0)
                            engagement = upvotes + (comments * 3)

                            signals.append({
                                "timestamp": datetime.utcfromtimestamp(pd.get("created_utc", 0)).isoformat(),
                                "symbol": sym_upper,
                                "source": "reddit",
                                "signal_type": "social_mention",
                                "direction": "bullish",
                                "strength": min(1.0, engagement / 1000),
                                "confidence": min(1.0, engagement / 5000),
                                "data_class": "public",
                                "raw": {
                                    "subreddit": subreddit,
                                    "title": title[:200],
                                    "upvotes": upvotes,
                                    "comments": comments,
                                    "url": pd.get("url", ""),
                                },
                            })

                logger.info(f"[reddit] r/{subreddit}: scanned {len(posts)} posts")
                time.sleep(1)  # Rate limiting between subreddits

            except Exception as e:
                errors.append(f"r/{subreddit}: {str(e)}")
                logger.error(f"[reddit] r/{subreddit} failed: {e}")

        return CollectorResult(
            source="reddit",
            signals=signals,
            errors=errors,
            symbols_scanned=symbols,
        )
