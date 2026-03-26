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
        signals = []
        errors = []
        symbols_scanned = []

        for symbol in symbols:
            try:
                logger.info(f"Searching patents for {symbol}")

                issued_count = self._search_patents(symbol, "issued", days_back)
                if issued_count is not None:
                    signals.append({
                        "symbol": symbol,
                        "source": self.source_name,
                        "signal_type": "patent_issued",
                        "direction": "bullish",
                        "strength": min(issued_count / 5.0, 1.0),
                        "confidence": 0.9,
                        "timestamp": datetime.utcnow().isoformat(),
                        "data_class": "private",
                        "raw_json": {
                            "patent_count": issued_count,
                            "type": "issued",
                            "days_back": days_back,
                        },
                    })

                app_count = self._search_patents(symbol, "application", days_back)
                if app_count is not None:
                    signals.append({
                        "symbol": symbol,
                        "source": self.source_name,
                        "signal_type": "patent_application",
                        "direction": "bullish",
                        "strength": min(app_count / 10.0, 1.0),
                        "confidence": 0.8,
                        "timestamp": datetime.utcnow().isoformat(),
                        "data_class": "private",
                        "raw_json": {
                            "patent_count": app_count,
                            "type": "application",
                            "days_back": days_back,
                        },
                    })

                symbols_scanned.append(symbol)
                time.sleep(2)

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
        try:
            base_url = PATFT_SEARCH if patent_type == "issued" else APPFT_SEARCH

            cutoff_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y%m%d")
            today = datetime.now().strftime("%Y%m%d")

            params = {
                "QUERY": f'((ASGN/("{company}") AND IDATE/{cutoff_date}-{today}))',
                "SORT": "ISSUED DESC",
                "ACTION": "SEARCH",
            }

            resp = requests.get(base_url, params=params, headers=HEADERS, timeout=15)
            resp.raise_for_status()

            soup = BeautifulSoup(resp.text, "html.parser")

            summary = soup.find("p", class_="summary")
            if summary:
                text = summary.get_text()
                if "found" in text.lower():
                    parts = text.split()
                    try:
                        count = int(parts[0])
                        logger.info(f"Found {count} {patent_type} patents for {company}")
                        return count
                    except (ValueError, IndexError):
                        pass

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
