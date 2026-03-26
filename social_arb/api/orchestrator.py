"""Engine Orchestrator — auto-runs all 6 engines for a given symbol.

This is the core of the auto-stack architecture. When a signal cluster
gets promoted through a gate, the orchestrator runs every relevant engine
and assembles the combined result.

Engines:
1. Sentiment Divergence — social vs institutional signal gap
2. Technical Analyzer — 7 price indicators (SMA, EMA, RSI, MACD, BBands, ATR, Momentum)
3. Kelly Criterion Sizer — position sizing from ROI scenarios
4. IRR/MOIC Simulator — bear/base/bull private market scenarios
5. Regulatory Moat Scorer — ESG + patent + regulatory burden
6. Cross-Domain Amplifier — multi-domain signal convergence
"""

import logging
from typing import Dict, Any, Optional

from social_arb.db.store import query_signals, query_ohlcv, query_mosaics, query_theses
from social_arb.db.schema import DEFAULT_DB_PATH
from social_arb.engine.sentiment_divergence import SentimentDivergenceCalculator
from social_arb.engine.technical_analyzer import calculate_all_indicators
from social_arb.engine.kelly_sizer import KellyCriterionSizer
from social_arb.engine.irr_simulator import IRRMOICSim
from social_arb.engine.regulatory_moat import RegulatoryMoatScorer
from social_arb.engine.cross_domain_amplifier import CrossDomainAmplifier
from social_arb.engine.stepps_classifier import SteppsClassifier
from social_arb.core.protocols import ConvictionLevel

logger = logging.getLogger(__name__)


class EngineOrchestrator:
    """Runs all 6 engines for a symbol and returns combined results."""

    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = db_path
        self.divergence = SentimentDivergenceCalculator()
        self.kelly = KellyCriterionSizer()
        self.irr = IRRMOICSim()
        self.moat = RegulatoryMoatScorer()
        self.amplifier = CrossDomainAmplifier()
        self.stepps = SteppsClassifier(db_path=db_path)

    def run_all(self, symbol: str, portfolio_value: float = 100_000) -> Dict[str, Any]:
        """Run all engines for a symbol. Returns engine_name → result dict."""
        results = {}

        # Fetch data once
        signals = query_signals(db_path=self.db_path, symbol=symbol, limit=500)
        ohlcv = query_ohlcv(db_path=self.db_path, symbol=symbol, limit=365)
        mosaics = query_mosaics(db_path=self.db_path, symbol=symbol, limit=5)
        theses = query_theses(db_path=self.db_path, symbol=symbol, limit=5)

        # 1. Sentiment Divergence
        results["sentiment_divergence"] = self._run_divergence(signals)

        # 2. Technical Analyzer
        results["technical_analyzer"] = self._run_technical(ohlcv)

        # 3. Kelly Criterion
        results["kelly_sizer"] = self._run_kelly(theses, portfolio_value)

        # 4. IRR/MOIC Simulator
        results["irr_simulator"] = self._run_irr(symbol, signals)

        # 5. Regulatory Moat
        results["regulatory_moat"] = self._run_moat(signals)

        # 6. Cross-Domain Amplifier
        results["cross_domain_amplifier"] = self._run_amplifier(signals)

        # 7. STEPPS Classifier
        results["stepps_classifier"] = self._run_stepps(signals)

        return results

    def _run_divergence(self, signals: list) -> dict:
        try:
            social = [s for s in signals if s["source"] in ("reddit", "google_trends")]
            inst = [s for s in signals if s["source"] in ("sec_edgar", "yfinance", "coingecko")]
            social_growth = sum(s.get("strength", 0) for s in social) / max(1, len(social)) * 100
            inst_growth = sum(s.get("strength", 0) for s in inst) / max(1, len(inst)) * 100

            result = self.divergence.calculate(
                signal_data={"growth_pct": social_growth, "volume": len(signals)},
                market_data={"growth_pct": inst_growth},
            )
            return result.to_dict() if hasattr(result, "to_dict") else {"error": "no result"}
        except Exception as e:
            logger.error(f"Divergence engine error: {e}")
            return {"error": str(e)}

    def _run_technical(self, ohlcv: list) -> dict:
        try:
            if not ohlcv or len(ohlcv) < 20:
                return {"error": "insufficient OHLCV data (need 20+ bars)"}

            # Convert DB rows to format expected by technical_analyzer
            bars = [{
                "date": o["timestamp"],
                "open": float(o["open"]),
                "high": float(o["high"]),
                "low": float(o["low"]),
                "close": float(o["close"]),
                "volume": int(o.get("volume", 0) or 0),
            } for o in ohlcv]

            enriched = calculate_all_indicators(bars)
            latest = enriched[-1] if enriched else {}
            return {
                "latest": latest,
                "indicators": {k: v for k, v in latest.items() if k not in ("date", "open", "high", "low", "close", "volume")},
                "bar_count": len(enriched),
            }
        except Exception as e:
            logger.error(f"Technical analyzer error: {e}")
            return {"error": str(e)}

    def _run_kelly(self, theses: list, portfolio_value: float) -> dict:
        try:
            if not theses:
                return {"error": "no thesis data for Kelly sizing"}
            thesis = theses[0]
            result = self.kelly.size(
                conviction=ConvictionLevel.MEDIUM,
                portfolio_value=portfolio_value,
                params={
                    "roi_bear": thesis.get("roi_bear", -0.1),
                    "roi_base": thesis.get("roi_base", 0.05),
                    "roi_bull": thesis.get("roi_bull", 0.2),
                },
            )
            return result.to_dict() if hasattr(result, "to_dict") else {"kelly_fraction": 0}
        except Exception as e:
            logger.error(f"Kelly sizer error: {e}")
            return {"error": str(e)}

    def _run_irr(self, symbol: str, signals: list) -> dict:
        try:
            avg_strength = sum(s.get("strength", 0) for s in signals) / max(1, len(signals))
            team_score = min(10, avg_strength * 12)  # proxy from signal quality
            result = self.irr.simulate(params={
                "initial_investment": 50000,
                "stage": "series_a",
                "sector": "ai",
                "team_score": team_score,
                "market_size_score": 7,
                "moat_score": 6,
            })
            return result.to_dict() if hasattr(result, "to_dict") else {"error": "no result"}
        except Exception as e:
            logger.error(f"IRR simulator error: {e}")
            return {"error": str(e)}

    def _run_moat(self, signals: list) -> dict:
        try:
            # Derive inputs from signal data
            source_count = len(set(s["source"] for s in signals))
            avg_strength = sum(s.get("strength", 0) for s in signals) / max(1, len(signals))
            result = self.moat.scan(
                target="analysis",
                data={
                    "esg_score": avg_strength * 80,
                    "carbon_intensity": 50,
                    "patent_count": source_count * 5,
                    "regulatory_burden": 0.5,
                    "institutional_ownership": 0.3,
                },
            )
            return result.to_dict() if hasattr(result, "to_dict") else {"error": "no result"}
        except Exception as e:
            logger.error(f"Moat scorer error: {e}")
            return {"error": str(e)}

    def _run_amplifier(self, signals: list) -> dict:
        try:
            result = self.amplifier.score({"signals": signals})
            return result.to_dict() if hasattr(result, "to_dict") else {"error": "no result"}
        except Exception as e:
            logger.error(f"Cross-domain amplifier error: {e}")
            return {"error": str(e)}

    def _run_stepps(self, signals: list) -> dict:
        """Run STEPPS classifier on signals."""
        try:
            if not signals:
                return {"error": "no signals to score"}

            # Score each signal
            scores = []
            for signal in signals[:10]:  # Score top 10 most recent
                signal_dict = {
                    "id": signal.get("id"),
                    "strength": signal.get("strength", 0.5),
                    "confidence": signal.get("confidence", 0.5),
                    "direction": signal.get("direction", "neutral"),
                    "source": signal.get("source", "unknown"),
                    "signal_type": signal.get("signal_type", "general"),
                }
                result = self.stepps.score(signal_dict)
                scores.append(result.to_dict())

            avg_composite = sum(s["composite"] for s in scores) / len(scores) if scores else 0.5

            return {
                "scores": scores,
                "avg_composite": round(avg_composite, 2),
                "signal_count": len(scores),
            }
        except Exception as e:
            logger.error(f"STEPPS classifier error: {e}")
            return {"error": str(e)}
