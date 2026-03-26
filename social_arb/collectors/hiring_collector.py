"""Hiring velocity signal collector. Scrapes public job pages."""

import logging
import time
from datetime import datetime
from typing import List, Optional, Dict, Any

import requests
from bs4 import BeautifulSoup

from social_arb.collectors.base import BaseCollector, CollectorResult

logger = logging.getLogger(__name__)

HEADERS = {"User-Agent": "SocialArb/1.0 (information arbitrage research)"}

COMPANY_CAREER_URLS = {
    "databricks": "https://www.databricks.com/careers/",
    "stripe": "https://stripe.com/jobs/",
    "anduril": "https://www.anduril.com/careers/",
    "coreweave": "https://www.coreweave.com/careers/",
    "anthropic": "https://www.anthropic.com/careers/",
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

                job_elements = soup.find_all(
                    ["div", "li"],
                    class_=lambda x: x and ("job" in x.lower() or "position" in x.lower())
                )

                job_count = len(job_elements)

                if job_count == 0:
                    all_links = soup.find_all("a")
                    job_links = [
                        a for a in all_links
                        if "job" in a.get("href", "").lower()
                        or "position" in a.text.lower()
                    ]
                    job_count = len(job_links)

                strength = min(job_count / 100.0, 1.0)

                signals.append({
                    "symbol": symbol,
                    "source": self.source_name,
                    "signal_type": "hiring_count",
                    "direction": "bullish" if job_count > 10 else "neutral",
                    "strength": strength,
                    "confidence": 0.8,
                    "timestamp": datetime.utcnow().isoformat(),
                    "data_class": "private",
                    "raw_json": {
                        "job_count": job_count,
                        "url": url,
                    },
                })

                symbols_scanned.append(symbol)
                time.sleep(2)

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
