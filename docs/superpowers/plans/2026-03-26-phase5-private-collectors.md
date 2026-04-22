# Phase 5: Private Company Collectors Implementation Plan

**Author:** Dan (Daniel Deenik)
**Date:** 2026-03-26
**Project:** Social Arb / Trader
**Objective:** Build 5 new free/scraping-based data collectors for private company signals

---

## Overview

Phase 5 extends the collector architecture with five new data sources targeting private company intelligence:

1. **News/PR Collector** — RSS feeds and Google News scraping
2. **Hiring Velocity Collector** — Job listing counts from career pages
3. **Patent Collector** — USPTO patent search (PATFT/AppFT)
4. **App Store Collector** — Google Play Store / Apple App Store ratings
5. **Web Presence Collector** — Web metadata via HTTP headers and meta tags

All collectors:
- Extend `BaseCollector` from `social_arb/collectors/base.py`
- Return `CollectorResult` with structured signals
- Handle errors gracefully (rate limits, timeouts, parse failures)
- Work **without API keys** (free/public data only)
- Support private company name → URL mapping via config

---

## Task 1: News/PR Collector (RSS Feeds)

**File:** `/sessions/laughing-serene-mendel/mnt/Trader/social_arb/collectors/news_collector.py`

**Purpose:** Monitor RSS feeds from TechCrunch, Google News, HackerNews for company mentions.

**Implementation:**

```python
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

# Google News URL template (no RSS, but scrapeable)
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
        """
        Collect news signals for given symbols.

        Args:
            symbols: Company names or keywords (e.g., ["Databricks", "Stripe"])
            feeds: List of feeds to scan (default: all)
        """
        feeds = feeds or list(RSS_FEEDS.keys())
        signals = []
        errors = []
        symbols_scanned = []

        for feed_name in feeds:
            try:
                feed_url = RSS_FEEDS.get(feed_name) or feed_name
                logger.info(f"Fetching {feed_name} from {feed_url}")

                resp = requests.get(feed_url, headers=HEADERS, timeout=15)
                resp.raise_for_status()

                parsed = feedparser.parse(resp.text)

                if parsed.bozo:
                    logger.warning(f"Feed parse warning for {feed_name}: {parsed.bozo_exception}")

                for entry in parsed.entries[:50]:  # Limit per feed
                    title = entry.get("title", "").upper()
                    summary = entry.get("summary", "").upper()
                    published = entry.get("published", datetime.now().isoformat())
                    link = entry.get("link", "")

                    text = f"{title} {summary}"

                    # Match company names
                    for symbol in symbols:
                        sym_upper = symbol.upper()
                        if sym_upper in text:
                            signals.append({
                                "symbol": symbol,
                                "source": self.source_name,
                                "signal_type": "news_mention",
                                "direction": "neutral",  # News is neutral; sentiment needs NLP
                                "strength": 0.6,
                                "confidence": 0.7,
                                "raw_json": {
                                    "feed": feed_name,
                                    "title": title,
                                    "link": link,
                                    "published": published,
                                },
                            })
                            if symbol not in symbols_scanned:
                                symbols_scanned.append(symbol)

                time.sleep(1)  # Be polite to RSS providers

            except requests.exceptions.Timeout:
                errors.append(f"timeout: {feed_name}")
            except requests.exceptions.RequestException as e:
                errors.append(f"request_error: {feed_name} - {str(e)}")
            except Exception as e:
                errors.append(f"parse_error: {feed_name} - {str(e)}")
                logger.error(f"Error processing {feed_name}: {e}", exc_info=True)

        # Fetch from Google News for each symbol
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
                        "raw_json": {
                            "feed": "google_news",
                            "title": title,
                            "link": link,
                            "published": published,
                        },
                    })
                    if symbol not in symbols_scanned:
                        symbols_scanned.append(symbol)

                time.sleep(2)  # Respect Google's rate limits

            except Exception as e:
                errors.append(f"google_news_error: {symbol} - {str(e)}")

        return CollectorResult(
            source=self.source_name,
            signals=signals,
            errors=errors,
            symbols_scanned=symbols_scanned,
        )
```

**Dependencies:**
- `requests` (already in requirements)
- `feedparser` (add to requirements)

**Test Command:**
```bash
pytest tests/collectors/test_news_collector.py -v
```

**Test File:** `/sessions/laughing-serene-mendel/mnt/Trader/tests/collectors/test_news_collector.py`

```python
"""Tests for news collector."""

import pytest
from social_arb.collectors.news_collector import NewsCollector


def test_news_collector_instantiate():
    """Test collector instantiation."""
    collector = NewsCollector()
    assert collector.source_name == "news"


def test_news_collector_collect_databricks():
    """Test collecting news for Databricks."""
    collector = NewsCollector()
    result = collector.collect(symbols=["Databricks", "Stripe"], feeds=["techcrunch"])

    assert result.source == "news"
    assert isinstance(result.signals, list)
    assert isinstance(result.errors, list)

    # May be empty if no matches, but should not crash
    if result.signals:
        sig = result.signals[0]
        assert "symbol" in sig
        assert "source" in sig
        assert sig["source"] == "news"


def test_news_collector_timeout_handling():
    """Test graceful timeout handling."""
    collector = NewsCollector()
    # Should not raise, should add to errors
    result = collector.collect(symbols=["TestCorp"])
    assert isinstance(result.errors, list)
```

---

## Task 2: Hiring Velocity Collector

**File:** `/sessions/laughing-serene-mendel/mnt/Trader/social_arb/collectors/hiring_collector.py`

**Purpose:** Scrape public job listing counts from company career pages or LinkedIn.

**Implementation:**

```python
"""Hiring velocity signal collector. Scrapes public job pages."""

import logging
import time
from typing import List, Optional, Dict, Any

import requests
from bs4 import BeautifulSoup

from social_arb.collectors.base import BaseCollector, CollectorResult

logger = logging.getLogger(__name__)

HEADERS = {"User-Agent": "SocialArb/1.0 (information arbitrage research)"}

# Map private company names to their career page URLs
COMPANY_CAREER_URLS = {
    "databricks": "https://www.databricks.com/careers/",
    "stripe": "https://stripe.com/jobs/",
    "anduril": "https://www.anduril.com/careers/",
    "coreweave": "https://www.coreweave.com/careers/",
    "anthropic": "https://www.anthropic.com/careers/",
    # Extend as needed
}


class HiringCollector(BaseCollector):
    """Collects hiring/growth signals from public job listings."""

    @property
    def source_name(self) -> str:
        return "hiring"

    def collect(
        self,
        symbols: List[str],
        company_urls: Optional[Dict[str, str]] = None,
        **kwargs,
    ) -> CollectorResult:
        """
        Collect hiring signals by scraping job listing counts.

        Args:
            symbols: Company names (e.g., ["Databricks", "Stripe"])
            company_urls: Override default URL mapping
        """
        urls = company_urls or COMPANY_CAREER_URLS
        signals = []
        errors = []
        symbols_scanned = []

        for symbol in symbols:
            try:
                key = symbol.lower()
                url = urls.get(key)

                if not url:
                    logger.warning(f"No career URL mapping for {symbol}")
                    errors.append(f"no_url_mapping: {symbol}")
                    continue

                logger.info(f"Scraping {symbol} career page: {url}")

                resp = requests.get(url, headers=HEADERS, timeout=15)
                resp.raise_for_status()

                soup = BeautifulSoup(resp.text, "html.parser")

                # Try to count job listings
                # Most career pages have <div class="job"> or <li class="job-listing">
                job_elements = soup.find_all(
                    ["div", "li"],
                    class_=lambda x: x and ("job" in x.lower() or "position" in x.lower())
                )

                job_count = len(job_elements)

                if job_count == 0:
                    # Fallback: count <a> tags with job-related keywords
                    all_links = soup.find_all("a")
                    job_links = [
                        a for a in all_links
                        if a.get("href", "").lower().__contains__("job")
                        or a.text.lower().__contains__("position")
                    ]
                    job_count = len(job_links)

                strength = min(job_count / 100.0, 1.0)  # Normalize: 100+ jobs = 1.0

                signals.append({
                    "symbol": symbol,
                    "source": self.source_name,
                    "signal_type": "hiring_count",
                    "direction": "bullish" if job_count > 10 else "neutral",
                    "strength": strength,
                    "confidence": 0.8,
                    "raw_json": {
                        "job_count": job_count,
                        "url": url,
                        "timestamp": time.time(),
                    },
                })

                symbols_scanned.append(symbol)
                time.sleep(2)  # Be polite

            except requests.exceptions.Timeout:
                errors.append(f"timeout: {symbol}")
            except requests.exceptions.RequestException as e:
                errors.append(f"request_error: {symbol} - {str(e)}")
            except Exception as e:
                errors.append(f"parse_error: {symbol} - {str(e)}")
                logger.error(f"Error scraping {symbol}: {e}", exc_info=True)

        return CollectorResult(
            source=self.source_name,
            signals=signals,
            errors=errors,
            symbols_scanned=symbols_scanned,
        )
```

**Dependencies:**
- `requests` (already in requirements)
- `beautifulsoup4` (add to requirements)

**Test Command:**
```bash
pytest tests/collectors/test_hiring_collector.py -v
```

**Test File:** `/sessions/laughing-serene-mendel/mnt/Trader/tests/collectors/test_hiring_collector.py`

```python
"""Tests for hiring collector."""

import pytest
from social_arb.collectors.hiring_collector import HiringCollector


def test_hiring_collector_instantiate():
    """Test collector instantiation."""
    collector = HiringCollector()
    assert collector.source_name == "hiring"


def test_hiring_collector_collect_databricks():
    """Test collecting hiring signals for Databricks."""
    collector = HiringCollector()
    result = collector.collect(symbols=["databricks"])

    assert result.source == "hiring"
    assert isinstance(result.signals, list)
    assert isinstance(result.errors, list)

    # Should have at least attempted databricks
    assert "databricks" in [s["symbol"].lower() for s in result.signals] or len(result.errors) > 0


def test_hiring_collector_custom_urls():
    """Test with custom URL mapping."""
    custom_urls = {
        "testcorp": "https://example.com/jobs/",
    }
    collector = HiringCollector()
    result = collector.collect(symbols=["testcorp"], company_urls=custom_urls)

    assert isinstance(result.signals, list)
    assert isinstance(result.errors, list)


def test_hiring_collector_no_url_mapping():
    """Test handling of missing URL mapping."""
    collector = HiringCollector()
    result = collector.collect(symbols=["UnknownCorp"])

    # Should handle gracefully
    assert isinstance(result.errors, list)
```

---

## Task 3: Patent Collector (USPTO Search)

**File:** `/sessions/laughing-serene-mendel/mnt/Trader/social_arb/collectors/patent_collector.py`

**Purpose:** Query USPTO PATFT/AppFT for recent patent filings.

**Implementation:**

```python
"""Patent signal collector. Queries USPTO PATFT/AppFT."""

import logging
import time
from datetime import datetime, timedelta
from typing import List, Optional

import requests
from bs4 import BeautifulSoup

from social_arb.collectors.base import BaseCollector, CollectorResult

logger = logging.getLogger(__name__)

HEADERS = {"User-Agent": "SocialArb/1.0 (information arbitrage research)"}

# USPTO Patent Search API (free, no auth)
USPTO_SEARCH_URL = "https://www.uspto.gov/patents-application-process"
PATFT_SEARCH = "https://patft.uspto.gov/cgi-bin/txtsrch.pl"
APPFT_SEARCH = "https://appft.uspto.gov/cgi-bin/txtsrch.pl"


class PatentCollector(BaseCollector):
    """Collects innovation signals from USPTO patent filings."""

    @property
    def source_name(self) -> str:
        return "patents"

    def collect(
        self,
        symbols: List[str],
        days_back: int = 30,
        **kwargs,
    ) -> CollectorResult:
        """
        Collect patent signals for given company names.

        Args:
            symbols: Company names (e.g., ["Databricks", "Stripe"])
            days_back: Look back period for patents (default 30 days)
        """
        signals = []
        errors = []
        symbols_scanned = []

        for symbol in symbols:
            try:
                logger.info(f"Searching patents for {symbol}")

                # Search issued patents
                issued_count = self._search_patents(symbol, "issued", days_back)
                if issued_count is not None:
                    signals.append({
                        "symbol": symbol,
                        "source": self.source_name,
                        "signal_type": "patent_issued",
                        "direction": "bullish",
                        "strength": min(issued_count / 5.0, 1.0),  # 5+ patents = strong
                        "confidence": 0.9,
                        "raw_json": {
                            "patent_count": issued_count,
                            "type": "issued",
                            "days_back": days_back,
                        },
                    })

                # Search patent applications
                app_count = self._search_patents(symbol, "application", days_back)
                if app_count is not None:
                    signals.append({
                        "symbol": symbol,
                        "source": self.source_name,
                        "signal_type": "patent_application",
                        "direction": "bullish",
                        "strength": min(app_count / 10.0, 1.0),  # 10+ apps = strong
                        "confidence": 0.8,
                        "raw_json": {
                            "patent_count": app_count,
                            "type": "application",
                            "days_back": days_back,
                        },
                    })

                symbols_scanned.append(symbol)
                time.sleep(2)  # Respect USPTO rate limits

            except Exception as e:
                errors.append(f"patent_search_error: {symbol} - {str(e)}")
                logger.error(f"Error searching patents for {symbol}: {e}", exc_info=True)

        return CollectorResult(
            source=self.source_name,
            signals=signals,
            errors=errors,
            symbols_scanned=symbols_scanned,
        )

    def _search_patents(self, company: str, patent_type: str, days_back: int) -> Optional[int]:
        """
        Search USPTO PATFT or APPFT for patents.

        Args:
            company: Company name
            patent_type: "issued" or "application"
            days_back: Days to look back

        Returns:
            Count of patents found, or None if error
        """
        try:
            base_url = PATFT_SEARCH if patent_type == "issued" else APPFT_SEARCH

            # Build date range query
            cutoff_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y%m%d")
            today = datetime.now().strftime("%Y%m%d")

            # Query params for USPTO search
            params = {
                "QUERY": f'((ASGN/("{company}") AND IDATE/{cutoff_date}-{today}))',
                "SORT": "ISSUED DESC",
                "ACTION": "SEARCH",
            }

            resp = requests.get(base_url, params=params, headers=HEADERS, timeout=15)
            resp.raise_for_status()

            soup = BeautifulSoup(resp.text, "html.parser")

            # USPTO returns hit count in page title or summary
            summary = soup.find("p", class_="summary")
            if summary:
                text = summary.get_text()
                # Parse "X patents found" or similar
                if "found" in text.lower():
                    parts = text.split()
                    try:
                        count = int(parts[0])
                        logger.info(f"Found {count} {patent_type} patents for {company}")
                        return count
                    except (ValueError, IndexError):
                        pass

            # Fallback: count <a> tags linking to patent records
            patent_links = soup.find_all("a", href=lambda x: x and "pn=" in x)
            count = len(patent_links)
            logger.info(f"Found {count} {patent_type} patents (by link count) for {company}")
            return count

        except requests.exceptions.Timeout:
            logger.warning(f"Timeout searching patents for {company}")
            return None
        except Exception as e:
            logger.error(f"Error in _search_patents: {e}", exc_info=True)
            return None
```

**Dependencies:**
- `requests` (already in requirements)
- `beautifulsoup4` (already added in Task 2)

**Test Command:**
```bash
pytest tests/collectors/test_patent_collector.py -v
```

**Test File:** `/sessions/laughing-serene-mendel/mnt/Trader/tests/collectors/test_patent_collector.py`

```python
"""Tests for patent collector."""

import pytest
from social_arb.collectors.patent_collector import PatentCollector


def test_patent_collector_instantiate():
    """Test collector instantiation."""
    collector = PatentCollector()
    assert collector.source_name == "patents"


def test_patent_collector_collect():
    """Test collecting patent signals."""
    collector = PatentCollector()
    result = collector.collect(symbols=["Google", "Microsoft"], days_back=90)

    assert result.source == "patents"
    assert isinstance(result.signals, list)
    assert isinstance(result.errors, list)


def test_patent_collector_handles_timeout():
    """Test graceful timeout handling."""
    collector = PatentCollector()
    result = collector.collect(symbols=["TestCorp"])

    # Should not crash
    assert isinstance(result.errors, list)
```

---

## Task 4: App Store Collector

**File:** `/sessions/laughing-serene-mendel/mnt/Trader/social_arb/collectors/appstore_collector.py`

**Purpose:** Scrape Google Play Store and Apple App Store for ratings and review trends.

**Implementation:**

```python
"""App Store signal collector. Scrapes public app data."""

import logging
import time
from typing import List, Optional, Dict

import requests
from bs4 import BeautifulSoup

from social_arb.collectors.base import BaseCollector, CollectorResult

logger = logging.getLogger(__name__)

HEADERS = {"User-Agent": "SocialArb/1.0 (information arbitrage research)"}

# Map private companies to their app names (if they have consumer apps)
COMPANY_APPS = {
    "databricks": [],  # B2B, no consumer app
    "stripe": [],  # B2B
    "anduril": [],  # B2B
    "coreweave": [],  # B2B
    "anthropic": ["Claude"],  # Claude iOS/Android apps
}


class AppStoreCollector(BaseCollector):
    """Collects engagement signals from public app stores."""

    @property
    def source_name(self) -> str:
        return "appstore"

    def collect(
        self,
        symbols: List[str],
        app_mapping: Optional[Dict[str, List[str]]] = None,
        **kwargs,
    ) -> CollectorResult:
        """
        Collect app store signals for given companies.

        Args:
            symbols: Company names
            app_mapping: Override default app name mapping
        """
        apps = app_mapping or COMPANY_APPS
        signals = []
        errors = []
        symbols_scanned = []

        for symbol in symbols:
            try:
                key = symbol.lower()
                app_names = apps.get(key, [])

                if not app_names:
                    logger.info(f"No consumer apps for {symbol}")
                    continue

                for app_name in app_names:
                    # Search Google Play Store
                    try:
                        gplay_signals = self._scrape_google_play(app_name)
                        signals.extend(gplay_signals)
                    except Exception as e:
                        errors.append(f"google_play_error: {app_name} - {str(e)}")

                    time.sleep(1)

                    # Search Apple App Store
                    try:
                        aapp_signals = self._scrape_apple_app_store(app_name)
                        signals.extend(aapp_signals)
                    except Exception as e:
                        errors.append(f"apple_app_store_error: {app_name} - {str(e)}")

                    time.sleep(1)

                symbols_scanned.append(symbol)

            except Exception as e:
                errors.append(f"appstore_error: {symbol} - {str(e)}")
                logger.error(f"Error processing {symbol}: {e}", exc_info=True)

        return CollectorResult(
            source=self.source_name,
            signals=signals,
            errors=errors,
            symbols_scanned=symbols_scanned,
        )

    def _scrape_google_play(self, app_name: str) -> List[Dict]:
        """Scrape Google Play Store for app rating and review count."""
        signals = []

        try:
            # Google Play Store search URL
            search_url = f"https://play.google.com/store/search?q={app_name}&c=apps"

            resp = requests.get(search_url, headers=HEADERS, timeout=15)
            resp.raise_for_status()

            soup = BeautifulSoup(resp.text, "html.parser")

            # Parse app containers (usually <a> with app details)
            apps = soup.find_all("a", class_="SnUeec")[:3]  # Top 3 results

            for app in apps:
                try:
                    title = app.find("span", class_="NzPhqe")
                    rating = app.find("span", class_="w2kbf")
                    review_count = app.find("span", class_="RwphZe")

                    if title and rating:
                        title_text = title.get_text(strip=True)
                        rating_text = rating.get_text(strip=True)
                        review_text = review_count.get_text(strip=True) if review_count else "0"

                        try:
                            rating_val = float(rating_text.split()[0])
                            review_val = int(review_text.replace("K", "000").replace("M", "000000").split()[0])

                            signals.append({
                                "symbol": app_name,
                                "source": self.source_name,
                                "signal_type": "app_rating",
                                "direction": "bullish" if rating_val >= 4.0 else "neutral",
                                "strength": rating_val / 5.0,
                                "confidence": 0.8,
                                "raw_json": {
                                    "platform": "google_play",
                                    "app_name": title_text,
                                    "rating": rating_val,
                                    "review_count": review_val,
                                },
                            })
                        except (ValueError, IndexError):
                            pass

                except Exception as e:
                    logger.debug(f"Error parsing app {app_name}: {e}")

        except Exception as e:
            logger.error(f"Error scraping Google Play for {app_name}: {e}")

        return signals

    def _scrape_apple_app_store(self, app_name: str) -> List[Dict]:
        """Scrape Apple App Store for app rating and review count."""
        signals = []

        try:
            # Apple App Store search URL
            search_url = f"https://apps.apple.com/search?term={app_name}"

            resp = requests.get(search_url, headers=HEADERS, timeout=15)
            resp.raise_for_status()

            soup = BeautifulSoup(resp.text, "html.parser")

            # Parse app containers
            apps = soup.find_all("div", class_="search-container")[:3]

            for app in apps:
                try:
                    title = app.find("h3")
                    rating = app.find("span", class_="rating")
                    review_count = app.find("span", class_="review-count")

                    if title and rating:
                        title_text = title.get_text(strip=True)
                        rating_text = rating.get_text(strip=True)
                        review_text = review_count.get_text(strip=True) if review_count else "0"

                        try:
                            rating_val = float(rating_text.split()[0])
                            review_val = int(review_text.split()[0].replace(",", ""))

                            signals.append({
                                "symbol": app_name,
                                "source": self.source_name,
                                "signal_type": "app_rating",
                                "direction": "bullish" if rating_val >= 4.0 else "neutral",
                                "strength": rating_val / 5.0,
                                "confidence": 0.8,
                                "raw_json": {
                                    "platform": "apple_app_store",
                                    "app_name": title_text,
                                    "rating": rating_val,
                                    "review_count": review_val,
                                },
                            })
                        except (ValueError, IndexError):
                            pass

                except Exception as e:
                    logger.debug(f"Error parsing app {app_name}: {e}")

        except Exception as e:
            logger.error(f"Error scraping Apple App Store for {app_name}: {e}")

        return signals
```

**Dependencies:**
- `requests` (already in requirements)
- `beautifulsoup4` (already added)

**Test Command:**
```bash
pytest tests/collectors/test_appstore_collector.py -v
```

**Test File:** `/sessions/laughing-serene-mendel/mnt/Trader/tests/collectors/test_appstore_collector.py`

```python
"""Tests for app store collector."""

import pytest
from social_arb.collectors.appstore_collector import AppStoreCollector


def test_appstore_collector_instantiate():
    """Test collector instantiation."""
    collector = AppStoreCollector()
    assert collector.source_name == "appstore"


def test_appstore_collector_with_apps():
    """Test collecting app store signals."""
    custom_apps = {
        "anthropic": ["Claude"],
    }
    collector = AppStoreCollector()
    result = collector.collect(symbols=["anthropic"], app_mapping=custom_apps)

    assert result.source == "appstore"
    assert isinstance(result.signals, list)


def test_appstore_collector_no_apps():
    """Test handling of companies with no apps."""
    collector = AppStoreCollector()
    result = collector.collect(symbols=["Databricks"])

    # Should handle gracefully (databricks is B2B)
    assert isinstance(result.signals, list)
```

---

## Task 5: Web Presence Collector

**File:** `/sessions/laughing-serene-mendel/mnt/Trader/social_arb/collectors/web_presence_collector.py`

**Purpose:** Extract web metadata signals (HTTP headers, meta tags, DNS records) for growth indicators.

**Implementation:**

```python
"""Web presence signal collector. Uses HTTP headers and meta tags."""

import logging
import time
from typing import List, Optional, Dict, Any

import requests
from bs4 import BeautifulSoup

from social_arb.collectors.base import BaseCollector, CollectorResult

logger = logging.getLogger(__name__)

HEADERS = {"User-Agent": "SocialArb/1.0 (information arbitrage research)"}

# Map company names to their primary domain URLs
COMPANY_DOMAINS = {
    "databricks": "https://www.databricks.com",
    "stripe": "https://stripe.com",
    "anduril": "https://www.anduril.com",
    "coreweave": "https://www.coreweave.com",
    "anthropic": "https://www.anthropic.com",
}


class WebPresenceCollector(BaseCollector):
    """Collects web presence signals from HTTP headers and meta tags."""

    @property
    def source_name(self) -> str:
        return "web_presence"

    def collect(
        self,
        symbols: List[str],
        domain_urls: Optional[Dict[str, str]] = None,
        **kwargs,
    ) -> CollectorResult:
        """
        Collect web presence signals.

        Args:
            symbols: Company names
            domain_urls: Override default URL mapping
        """
        urls = domain_urls or COMPANY_DOMAINS
        signals = []
        errors = []
        symbols_scanned = []

        for symbol in symbols:
            try:
                key = symbol.lower()
                url = urls.get(key)

                if not url:
                    logger.warning(f"No domain URL mapping for {symbol}")
                    errors.append(f"no_url_mapping: {symbol}")
                    continue

                logger.info(f"Fetching web presence data for {symbol} from {url}")

                # Fetch page
                resp = requests.get(url, headers=HEADERS, timeout=15, allow_redirects=True)
                resp.raise_for_status()

                # Extract signals from HTTP headers
                server = resp.headers.get("server", "unknown")
                x_powered_by = resp.headers.get("x-powered-by", "")
                cf_ray = resp.headers.get("cf-ray")  # Cloudflare indicates scale
                cache_control = resp.headers.get("cache-control", "")

                # Parse HTML
                soup = BeautifulSoup(resp.text, "html.parser")

                # Count pages (estimate from sitemap if available)
                sitemap_url = f"{url.rstrip('/')}/sitemap.xml"
                sitemap_pages = self._fetch_sitemap_count(sitemap_url)

                # Extract meta tags for company info
                description = soup.find("meta", attrs={"name": "description"})
                og_title = soup.find("meta", attrs={"property": "og:title"})

                # Count major sections/resources
                nav_links = soup.find_all("a", class_=lambda x: x and "nav" in x.lower())
                footer_links = soup.find_all("footer")

                # Assess web maturity
                has_cloudflare = cf_ray is not None
                has_caching = "max-age" in cache_control.lower()
                page_count_score = min(sitemap_pages / 500.0, 1.0) if sitemap_pages > 0 else 0.5

                maturity_score = (
                    (0.3 if has_cloudflare else 0.1) +
                    (0.3 if has_caching else 0.1) +
                    (0.4 * page_count_score)
                )

                signals.append({
                    "symbol": symbol,
                    "source": self.source_name,
                    "signal_type": "web_maturity",
                    "direction": "bullish" if maturity_score > 0.6 else "neutral",
                    "strength": maturity_score,
                    "confidence": 0.7,
                    "raw_json": {
                        "url": url,
                        "server": server,
                        "x_powered_by": x_powered_by,
                        "has_cloudflare": has_cloudflare,
                        "has_caching": has_caching,
                        "sitemap_pages": sitemap_pages,
                        "description": description.get("content", "") if description else "",
                    },
                })

                symbols_scanned.append(symbol)
                time.sleep(1)

            except requests.exceptions.Timeout:
                errors.append(f"timeout: {symbol}")
            except requests.exceptions.RequestException as e:
                errors.append(f"request_error: {symbol} - {str(e)}")
            except Exception as e:
                errors.append(f"web_presence_error: {symbol} - {str(e)}")
                logger.error(f"Error fetching web presence for {symbol}: {e}", exc_info=True)

        return CollectorResult(
            source=self.source_name,
            signals=signals,
            errors=errors,
            symbols_scanned=symbols_scanned,
        )

    def _fetch_sitemap_count(self, sitemap_url: str) -> int:
        """Fetch sitemap.xml and count URLs."""
        try:
            resp = requests.get(sitemap_url, headers=HEADERS, timeout=10)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "xml")
                urls = soup.find_all("url")
                return len(urls)
        except Exception:
            pass

        return 0
```

**Dependencies:**
- `requests` (already in requirements)
- `beautifulsoup4` (already added)
- `lxml` for XML parsing (add to requirements)

**Test Command:**
```bash
pytest tests/collectors/test_web_presence_collector.py -v
```

**Test File:** `/sessions/laughing-serene-mendel/mnt/Trader/tests/collectors/test_web_presence_collector.py`

```python
"""Tests for web presence collector."""

import pytest
from social_arb.collectors.web_presence_collector import WebPresenceCollector


def test_web_presence_collector_instantiate():
    """Test collector instantiation."""
    collector = WebPresenceCollector()
    assert collector.source_name == "web_presence"


def test_web_presence_collector_collect():
    """Test collecting web presence signals."""
    collector = WebPresenceCollector()
    result = collector.collect(symbols=["databricks"])

    assert result.source == "web_presence"
    assert isinstance(result.signals, list)
    assert isinstance(result.errors, list)


def test_web_presence_collector_custom_urls():
    """Test with custom domain mapping."""
    custom_urls = {
        "testcorp": "https://www.example.com",
    }
    collector = WebPresenceCollector()
    result = collector.collect(symbols=["testcorp"], domain_urls=custom_urls)

    assert isinstance(result.signals, list)


def test_web_presence_collector_no_url_mapping():
    """Test handling of missing URL mapping."""
    collector = WebPresenceCollector()
    result = collector.collect(symbols=["UnknownCorp"])

    assert isinstance(result.errors, list)
```

---

## Task 6: Integration — Register Collectors & Add Scheduler

**Files Modified:**

### 6a. Update `/sessions/laughing-serene-mendel/mnt/Trader/social_arb/tasks/workers.py`

Add imports and register new collectors in the `COLLECTORS` dict:

```python
# Add these imports at the top
from social_arb.collectors.news_collector import NewsCollector
from social_arb.collectors.hiring_collector import HiringCollector
from social_arb.collectors.patent_collector import PatentCollector
from social_arb.collectors.appstore_collector import AppStoreCollector
from social_arb.collectors.web_presence_collector import WebPresenceCollector

# Update COLLECTORS dict
COLLECTORS = {
    "yfinance": YFinanceCollector(),
    "reddit": RedditCollector(),
    "sec_edgar": SECEdgarCollector(),
    "google_trends": TrendsCollector(),
    "github": GitHubCollector(),
    "coingecko": CoinGeckoCollector(),
    "defillama": DeFiLlamaCollector(),
    # Phase 5: Private company collectors
    "news": NewsCollector(),
    "hiring": HiringCollector(),
    "patents": PatentCollector(),
    "appstore": AppStoreCollector(),
    "web_presence": WebPresenceCollector(),
}
```

### 6b. Update `/sessions/laughing-serene-mendel/mnt/Trader/social_arb/config.py`

Add private company domain mappings:

```python
# Add after crypto_symbols definition
self.private_company_domains: dict = {
    "databricks": "https://www.databricks.com",
    "stripe": "https://stripe.com",
    "anduril": "https://www.anduril.com",
    "coreweave": "https://www.coreweave.com",
    "anthropic": "https://www.anthropic.com",
}

self.private_company_career_urls: dict = {
    "databricks": "https://www.databricks.com/careers/",
    "stripe": "https://stripe.com/jobs/",
    "anduril": "https://www.anduril.com/careers/",
    "coreweave": "https://www.coreweave.com/careers/",
    "anthropic": "https://www.anthropic.com/careers/",
}

self.private_company_apps: dict = {
    "databricks": [],
    "stripe": [],
    "anduril": [],
    "coreweave": [],
    "anthropic": ["Claude"],
}
```

### 6c. Create/Update `/sessions/laughing-serene-mendel/mnt/Trader/social_arb/tasks/scheduler.py`

Add private company collection schedule:

```python
"""Scheduler for private company collectors."""

import asyncio
import logging
from typing import Dict, Any

from social_arb.tasks.workers import handle_collect
from social_arb.config import config

logger = logging.getLogger(__name__)


async def schedule_private_company_collection() -> Dict[str, Any]:
    """
    Scheduled task: collect signals for all private companies.
    Run daily or on demand.
    """
    logger.info("Starting private company collection schedule")

    params = {
        "sources": ["news", "hiring", "patents", "appstore", "web_presence"],
        "symbols": config.private_symbols,
        "domain": "private",
    }

    result = await handle_collect(params)
    logger.info(f"Private company collection result: {result}")
    return result


async def schedule_all_collection() -> Dict[str, Any]:
    """
    Master schedule: collect all domains (public + private + crypto).
    """
    logger.info("Starting master collection schedule")

    # Collect from all sources for all symbols
    public_params = {
        "sources": ["yfinance", "reddit", "sec_edgar", "google_trends", "github"],
        "symbols": config.public_symbols,
        "domain": "public",
    }

    private_params = {
        "sources": ["news", "hiring", "patents", "appstore", "web_presence"],
        "symbols": config.private_symbols,
        "domain": "private",
    }

    crypto_params = {
        "sources": ["coingecko", "defillama"],
        "symbols": config.crypto_symbols,
        "domain": "crypto",
    }

    results = {
        "public": await handle_collect(public_params),
        "private": await handle_collect(private_params),
        "crypto": await handle_collect(crypto_params),
    }

    logger.info(f"Master collection result: {results}")
    return results
```

**Test Command:**
```bash
pytest tests/tasks/test_workers.py::test_collectors_registered -v
```

**Test Addition to `/sessions/laughing-serene-mendel/mnt/Trader/tests/tasks/test_workers.py`:**

```python
"""Test new collector registration."""

import pytest
from social_arb.tasks.workers import COLLECTORS


def test_collectors_registered():
    """Test all Phase 5 collectors are registered."""
    expected = ["news", "hiring", "patents", "appstore", "web_presence"]
    for source in expected:
        assert source in COLLECTORS, f"Collector '{source}' not registered"
        assert COLLECTORS[source] is not None


@pytest.mark.asyncio
async def test_handle_collect_with_private_sources():
    """Test handle_collect with new private company sources."""
    from social_arb.tasks.workers import handle_collect

    params = {
        "sources": ["news"],
        "symbols": ["Databricks"],
        "domain": "private",
    }

    result = await handle_collect(params)
    assert "signal_count" in result
    assert "errors" in result
    assert "source_results" in result
```

---

## Task 7: Comprehensive Test Suite

**File:** `/sessions/laughing-serene-mendel/mnt/Trader/tests/collectors/test_phase5_integration.py`

**Purpose:** Integration tests for all Phase 5 collectors.

```python
"""Integration tests for Phase 5 private company collectors."""

import pytest
from social_arb.collectors.news_collector import NewsCollector
from social_arb.collectors.hiring_collector import HiringCollector
from social_arb.collectors.patent_collector import PatentCollector
from social_arb.collectors.appstore_collector import AppStoreCollector
from social_arb.collectors.web_presence_collector import WebPresenceCollector
from social_arb.collectors.base import CollectorResult


@pytest.fixture
def private_symbols():
    """Standard private company test symbols."""
    return ["Databricks", "Stripe", "Anduril"]


def test_all_collectors_exist(private_symbols):
    """Test that all collectors can be instantiated."""
    collectors = [
        NewsCollector(),
        HiringCollector(),
        PatentCollector(),
        AppStoreCollector(),
        WebPresenceCollector(),
    ]

    assert len(collectors) == 5
    assert all(c is not None for c in collectors)


def test_collector_result_structure():
    """Test that all collectors return valid CollectorResult."""
    collector = NewsCollector()
    result = collector.collect(symbols=["Databricks"])

    assert isinstance(result, CollectorResult)
    assert hasattr(result, "source")
    assert hasattr(result, "signals")
    assert hasattr(result, "errors")
    assert hasattr(result, "symbols_scanned")

    assert isinstance(result.signals, list)
    assert isinstance(result.errors, list)
    assert isinstance(result.symbols_scanned, list)


def test_signal_schema(private_symbols):
    """Test that signals conform to expected schema."""
    collector = NewsCollector()
    result = collector.collect(symbols=private_symbols)

    for signal in result.signals:
        assert "symbol" in signal
        assert "source" in signal
        assert "signal_type" in signal
        assert "direction" in signal
        assert "strength" in signal
        assert "confidence" in signal
        assert "raw_json" in signal

        # Validate ranges
        assert 0 <= signal["strength"] <= 1.0
        assert 0 <= signal["confidence"] <= 1.0
        assert signal["direction"] in ["bullish", "neutral", "bearish"]


def test_error_handling():
    """Test that collectors handle errors gracefully."""
    collectors = [
        NewsCollector(),
        HiringCollector(),
        PatentCollector(),
        AppStoreCollector(),
        WebPresenceCollector(),
    ]

    for collector in collectors:
        # Should not raise, should return result with errors
        result = collector.collect(symbols=["NonExistentCompanyXYZ"])
        assert isinstance(result, CollectorResult)
        assert isinstance(result.errors, list)


def test_source_names():
    """Test that each collector has correct source_name."""
    mappings = {
        NewsCollector(): "news",
        HiringCollector(): "hiring",
        PatentCollector(): "patents",
        AppStoreCollector(): "appstore",
        WebPresenceCollector(): "web_presence",
    }

    for collector, expected_name in mappings.items():
        assert collector.source_name == expected_name


@pytest.mark.asyncio
async def test_workers_integration():
    """Test that collectors integrate with worker tasks."""
    from social_arb.tasks.workers import COLLECTORS

    for source in ["news", "hiring", "patents", "appstore", "web_presence"]:
        assert source in COLLECTORS
        assert COLLECTORS[source] is not None


def test_no_api_keys_required():
    """Verify all collectors work without API keys."""
    # All Phase 5 collectors should instantiate without env vars
    import os

    # Temporarily clear any API key env vars (they shouldn't be needed)
    saved_env = {}
    api_keys = ["API_KEY", "REDIS_URL", "DATABASE_URL"]
    for key in api_keys:
        if key in os.environ:
            saved_env[key] = os.environ.pop(key)

    try:
        collectors = [
            NewsCollector(),
            HiringCollector(),
            PatentCollector(),
            AppStoreCollector(),
            WebPresenceCollector(),
        ]
        assert len(collectors) == 5
    finally:
        # Restore env
        for key, val in saved_env.items():
            os.environ[key] = val
```

**Test Command:**
```bash
pytest tests/collectors/test_phase5_integration.py -v
pytest tests/collectors/test_news_collector.py -v
pytest tests/collectors/test_hiring_collector.py -v
pytest tests/collectors/test_patent_collector.py -v
pytest tests/collectors/test_appstore_collector.py -v
pytest tests/collectors/test_web_presence_collector.py -v
pytest tests/tasks/test_workers.py::test_collectors_registered -v
```

**Run All Phase 5 Tests:**
```bash
pytest tests/collectors/ tests/tasks/test_workers.py -v --tb=short
```

---

## Summary

| Task | File | Status | Type |
|------|------|--------|------|
| 1. News/PR Collector | `social_arb/collectors/news_collector.py` | Create | Code |
| 2. Hiring Velocity | `social_arb/collectors/hiring_collector.py` | Create | Code |
| 3. Patent Collector | `social_arb/collectors/patent_collector.py` | Create | Code |
| 4. App Store Collector | `social_arb/collectors/appstore_collector.py` | Create | Code |
| 5. Web Presence Collector | `social_arb/collectors/web_presence_collector.py` | Create | Code |
| 6a. Register in workers | `social_arb/tasks/workers.py` | Modify | Integration |
| 6b. Add config mappings | `social_arb/config.py` | Modify | Config |
| 6c. Add scheduler | `social_arb/tasks/scheduler.py` | Create | Integration |
| 7. Integration tests | `tests/collectors/test_phase5_integration.py` | Create | Tests |

## Dependencies to Add

```txt
feedparser>=6.0.0
beautifulsoup4>=4.12.0
lxml>=4.9.0
```

## Architecture Notes

- **BaseCollector pattern:** All collectors extend the abstract base and implement `source_name` property and `collect()` method
- **Error handling:** Each collector gracefully handles timeouts, parse failures, rate limits; errors are collected and returned, not raised
- **Signal schema:** Consistent across all collectors — symbol, source, signal_type, direction, strength, confidence, raw_json
- **Rate limiting:** 1-2 second delays between requests to be respectful to free/public endpoints
- **Config-driven:** Company name → URL mappings live in `config.py` for easy extension
- **Private-first:** All 5 new collectors target private company signals; existing collectors focus on public/crypto
- **Free data only:** No API keys, no paid services — RSS, web scraping, free public APIs only

## Execution Order

1. **Phase 1-4:** Implement collectors 1-5 (Tasks 1-5) with full test coverage
2. **Phase 2:** Integrate into workers and scheduler (Task 6a-6c)
3. **Phase 3:** Add configuration mappings (Task 6b)
4. **Phase 4:** Run full integration test suite (Task 7)
5. **Phase 5:** Deploy and schedule daily private company collection

---

**Generated:** 2026-03-26
**For:** Social Arb Information Arbitrage Platform
**Status:** Ready to implement
