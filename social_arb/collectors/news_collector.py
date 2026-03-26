"""News/PR signal collector using public RSS feeds."""

import logging
import time
from datetime import datetime
from typing import List, Optional, Dict, Any
from urllib.parse import quote

import requests
import feedparser

from social_arb.collectors.base import BaseCollector, CollectorResult

logger = logging.getLogger(__name__)

HEADERS = {"User-Agent": "SocialArb/1.0 (information arbitrage research)"}

# Free RSS feeds — no auth required
RSS_FEEDS = {
    "techcrunch": "https://techcrunch.com/feed/",
    "hackernews": "https://news.ycombinator.com/rss",
    "producthunt": "https://www.producthunt.com/feed.xml",
}

# Google News URL template
GOOGLE_NEWS_URL = "https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"


class NewsCollector(BaseCollector):
    """Collects news/PR signals from RSS feeds."""

    @property
    def source_name(self) -> str:
        return "news"

    def collect(
        self,
        symbols: List[str],
        feeds: Optional[List[str]] = None,
        **kwargs,
    ) -> CollectorResult:
        feeds = feeds or list(RSS_FEEDS.keys())
        signals = []
        errors = []
        symbols_scanned = set()

        for feed_name in feeds:
            try:
                feed_url = RSS_FEEDS.get(feed_name) or feed_name
                logger.info(f"Fetching {feed_name} from {feed_url}")

                resp = requests.get(feed_url, headers=HEADERS, timeout=15)
                resp.raise_for_status()

                parsed = feedparser.parse(resp.text)

                if parsed.bozo:
                    logger.warning(f"Feed parse warning for {feed_name}: {parsed.bozo_exception}")

                for entry in parsed.entries[:50]:
                    title = entry.get("title", "").upper()
                    summary = entry.get("summary", "").upper()
                    published = entry.get("published", datetime.now().isoformat())
                    link = entry.get("link", "")

                    text = f"{title} {summary}"

                    for symbol in symbols:
                        sym_upper = symbol.upper()
                        if sym_upper in text:
                            signals.append({
                                "symbol": symbol,
                                "source": self.source_name,
                                "signal_type": "news_mention",
                                "direction": "neutral",
                                "strength": 0.6,
                                "confidence": 0.7,
                                "timestamp": datetime.utcnow().isoformat(),
                                "data_class": "private",
                                "raw_json": {
                                    "feed": feed_name,
                                    "title": title,
                                    "link": link,
                                    "published": published,
                                },
                            })
                            symbols_scanned.add(symbol)

                time.sleep(1)

            except requests.exceptions.Timeout:
                errors.append(f"timeout: {feed_name}")
            except requests.exceptions.RequestException as e:
                errors.append(f"request_error: {feed_name} - {str(e)}")
            except Exception as e:
                errors.append(f"parse_error: {feed_name} - {str(e)}")
                logger.error(f"Error processing {feed_name}: {e}", exc_info=True)

        for symbol in symbols:
            try:
                gn_url = GOOGLE_NEWS_URL.format(query=quote(symbol))
                resp = requests.get(gn_url, headers=HEADERS, timeout=15)
                resp.raise_for_status()

                parsed = feedparser.parse(resp.text)

                for entry in parsed.entries[:10]:
                    title = entry.get("title", "").upper()
                    link = entry.get("link", "")
                    published = entry.get("published", datetime.now().isoformat())

                    signals.append({
                        "symbol": symbol,
                        "source": self.source_name,
                        "signal_type": "google_news",
                        "direction": "neutral",
                        "strength": 0.5,
                        "confidence": 0.7,
                        "timestamp": datetime.utcnow().isoformat(),
                        "data_class": "private",
                        "raw_json": {
                            "feed": "google_news",
                            "title": title,
                            "link": link,
                            "published": published,
                        },
                    })
                    symbols_scanned.add(symbol)

                time.sleep(2)

            except Exception as e:
                errors.append(f"google_news_error: {symbol} - {str(e)}")

        return CollectorResult(
            source=self.source_name,
            signals=signals,
            errors=errors,
            symbols_scanned=list(symbols_scanned),
        )
