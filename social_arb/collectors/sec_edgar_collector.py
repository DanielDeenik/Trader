"""SEC EDGAR collector using free EFTS API. No key required."""

import logging
import time
from datetime import datetime
from typing import List, Dict

import requests

from social_arb.collectors.base import BaseCollector, CollectorResult

logger = logging.getLogger(__name__)

EDGAR_FILINGS = "https://data.sec.gov/submissions"
HEADERS = {"User-Agent": "SocialArb dan@socialarb.com", "Accept": "application/json"}

TICKER_CIK: Dict[str, str] = {
    "NVDA": "0001045810",
    "PLTR": "0001321655",
    "MSFT": "0000789019",
    "AAPL": "0000320193",
    "GOOGL": "0001652044",
    "AMD": "0000002488",
    "TSLA": "0001318605",
    "SHOP": "0001594805",
    "SQ": "0001512673",
    "DDOG": "0001561550",
}


class SECEdgarCollector(BaseCollector):

    @property
    def source_name(self) -> str:
        return "sec_edgar"

    def collect(self, symbols: List[str], **kwargs) -> CollectorResult:
        signals = []
        errors = []
        scanned = []

        for symbol in symbols:
            cik = TICKER_CIK.get(symbol.upper())
            if not cik:
                errors.append(f"{symbol}: CIK not found — add to TICKER_CIK mapping")
                continue

            try:
                url = f"{EDGAR_FILINGS}/CIK{cik}.json"
                resp = requests.get(url, headers=HEADERS, timeout=10)
                resp.raise_for_status()
                data = resp.json()

                recent = data.get("filings", {}).get("recent", {})
                forms = recent.get("form", [])
                dates = recent.get("filingDate", [])
                descriptions = recent.get("primaryDocDescription", [])

                scanned.append(symbol)

                for j in range(min(10, len(forms))):
                    form_type = forms[j]
                    filing_date = dates[j]
                    desc = descriptions[j] if j < len(descriptions) else ""

                    strength = 0.3
                    direction = "neutral"
                    if form_type in ("10-K", "10-Q"):
                        strength = 0.5
                    elif form_type == "8-K":
                        strength = 0.7
                        direction = "bullish"
                    elif "13F" in form_type:
                        strength = 0.6
                        direction = "bullish"

                    signals.append({
                        "timestamp": filing_date,
                        "symbol": symbol,
                        "source": "sec_edgar",
                        "signal_type": f"filing_{form_type.lower().replace('-', '')}",
                        "direction": direction,
                        "strength": strength,
                        "confidence": 0.85,
                        "data_class": "public",
                        "raw": {
                            "form_type": form_type,
                            "description": desc,
                            "cik": cik,
                        },
                    })

                logger.info(f"[sec] {symbol}: {min(10, len(forms))} filings collected")
                time.sleep(0.5)

            except Exception as e:
                errors.append(f"{symbol}: {str(e)}")
                logger.error(f"[sec] {symbol} failed: {e}")

        return CollectorResult(
            source="sec_edgar",
            signals=signals,
            errors=errors,
            symbols_scanned=scanned,
        )
