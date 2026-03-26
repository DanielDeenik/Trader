"""Web presence signal collector. Uses HTTP headers and meta tags."""

import logging
import time
from typing import List, Optional, Dict, Any

import requests
from bs4 import BeautifulSoup

from social_arb.collectors.base import BaseCollector, CollectorResult

logger = logging.getLogger(__name__)

HEADERS = {"User-Agent": "SocialArb/1.0 (information arbitrage research)"}

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

                resp = requests.get(url, headers=HEADERS, timeout=15, allow_redirects=True)
                resp.raise_for_status()

                server = resp.headers.get("server", "unknown")
                x_powered_by = resp.headers.get("x-powered-by", "")
                cf_ray = resp.headers.get("cf-ray")
                cache_control = resp.headers.get("cache-control", "")

                soup = BeautifulSoup(resp.text, "html.parser")

                sitemap_url = f"{url.rstrip('/')}/sitemap.xml"
                sitemap_pages = self._fetch_sitemap_count(sitemap_url)

                description = soup.find("meta", attrs={"name": "description"})

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
        try:
            resp = requests.get(sitemap_url, headers=HEADERS, timeout=10)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "xml")
                urls = soup.find_all("url")
                return len(urls)
        except Exception:
            pass
        return 0
