"""App Store signal collector. Scrapes public app data."""

import logging
import time
from typing import List, Optional, Dict

import requests
from bs4 import BeautifulSoup

from social_arb.collectors.base import BaseCollector, CollectorResult

logger = logging.getLogger(__name__)

HEADERS = {"User-Agent": "SocialArb/1.0 (information arbitrage research)"}

COMPANY_APPS = {
    "databricks": [],
    "stripe": [],
    "anduril": [],
    "coreweave": [],
    "anthropic": ["Claude"],
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
                    try:
                        gplay_signals = self._scrape_google_play(app_name)
                        signals.extend(gplay_signals)
                    except Exception as e:
                        errors.append(f"google_play_error: {app_name} - {str(e)}")

                    time.sleep(1)

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
        signals = []
        try:
            search_url = f"https://play.google.com/store/search?q={app_name}&c=apps"
            resp = requests.get(search_url, headers=HEADERS, timeout=15)
            resp.raise_for_status()

            soup = BeautifulSoup(resp.text, "html.parser")
            apps = soup.find_all("a", class_="SnUeec")[:3]

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
        signals = []
        try:
            search_url = f"https://apps.apple.com/search?term={app_name}"
            resp = requests.get(search_url, headers=HEADERS, timeout=15)
            resp.raise_for_status()

            soup = BeautifulSoup(resp.text, "html.parser")
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
