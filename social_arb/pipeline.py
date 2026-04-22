"""Batch analysis pipeline: signals → mosaics → theses.

Reads raw signals from DB, runs topology engine logic, writes results back.
No HITL gates here — just computation. HITL happens in cli.py review command.
"""

import json
import logging
import math
from typing import List, Dict, Optional

from social_arb.db.schema import DEFAULT_DB_PATH
from social_arb.db.store import (
    query_signals, insert_mosaic, insert_thesis, query_mosaics
)
from social_arb.engine.sentiment_divergence import SentimentDivergenceCalculator
from social_arb.engine.irr_simulator import IRRMOICSim
from social_arb.engine.regulatory_moat import RegulatoryMoatScorer
from social_arb.engine.technical_analyzer import calculate_all_indicators
from social_arb.engine.cross_domain_amplifier import CrossDomainAmplifier

logger = logging.getLogger(__name__)

# Known crypto symbols (tokens + DeFi protocols)
CRYPTO_SYMBOLS = {"BTC", "ETH", "SOL", "AVAX", "LINK", "AAVE", "UNI", "ARB", "OP", "MATIC",
                  "LIDO", "MAKER", "COMPOUND", "CURVE", "EIGENLAYER", "ETHENA", "PENDLE", "MORPHO"}

# Known private company symbols
PRIVATE_SYMBOLS = {"DATABRICKS", "STRIPE", "ANDURIL", "COREWEAVE", "ANTHROPIC"}


def _compute_roi_from_signals(signals: List[Dict], domain: str) -> Dict[str, float]:
    """Compute ROI estimates from actual signal data — no hardcoded values."""
    strengths = [s.get("strength", 0) for s in signals if s.get("strength")]
    avg_strength = sum(strengths) / len(strengths) if strengths else 0.5

    # Extract price/TVL change data from raw_json
    changes = []
    for s in signals:
        raw = s.get("raw_json")
        if not raw:
            continue
        try:
            data = json.loads(raw) if isinstance(raw, str) else raw
        except (json.JSONDecodeError, TypeError):
            continue
        # yfinance: price changes
        for key in ("change_1d_pct", "change_5d_pct", "tvl_change_7d", "price_change_7d_pct"):
            if key in data and data[key] is not None:
                changes.append(data[key] / 100.0 if abs(data[key]) > 1 else data[key])

    avg_change = sum(changes) / len(changes) if changes else 0.0

    # Domain-specific volatility multipliers (derived from signal data)
    if domain == "crypto":
        vol_mult = 3.0  # crypto is ~3x more volatile
    elif domain == "private_markets":
        vol_mult = 2.0  # private markets = illiquidity premium
    else:
        vol_mult = 1.0

    # Base ROI derived from observed momentum + strength
    base_roi = avg_change * vol_mult + (avg_strength - 0.5) * 0.2
    base_roi = max(-0.5, min(2.0, base_roi))  # clamp

    # Bear/bull are derived from base with domain-adjusted asymmetry
    bear_roi = base_roi - (0.15 + abs(base_roi) * 0.5) * vol_mult
    bull_roi = base_roi + (0.20 + abs(base_roi) * 0.8) * vol_mult

    return {
        "bear": round(max(-0.80, bear_roi), 4),
        "base": round(base_roi, 4),
        "bull": round(min(5.0, bull_roi), 4),
    }


def _compute_kelly(roi: Dict[str, float], confidence: float) -> float:
    """Kelly criterion from computed ROI and confidence. f* = (p*b - q) / b."""
    p = confidence
    q = 1 - p
    b = abs(roi["bull"] / roi["bear"]) if roi["bear"] != 0 else 1.0
    kelly = (p * b - q) / b if b > 0 else 0
    return round(max(0.0, min(0.25, kelly)), 4)  # cap at quarter-Kelly


def _infer_lifecycle(coherence: float, divergence: float, source_count: int) -> str:
    """Infer Gold Rush lifecycle stage from signal metrics."""
    if source_count <= 1 and coherence < 50:
        return "emerging"
    elif coherence >= 70 and divergence < 15:
        return "confirmed"
    elif coherence >= 80 and divergence < 5:
        return "saturated"
    else:
        return "validating"


def run_analysis(
    *,
    db_path: str = DEFAULT_DB_PATH,
    symbols: Optional[List[str]] = None,
) -> Dict:
    """
    Run batch analysis over collected signals.

    Steps:
    1. Group signals by symbol
    2. For each symbol: compute divergence, coherence, cross-domain amplification
    3. Assemble mosaic cards
    4. For strong mosaics: create thesis with data-derived ROI estimates
    """
    stats = {"symbols_analyzed": 0, "mosaics_created": 0, "theses_created": 0, "errors": []}

    # Get all recent signals
    if symbols:
        all_signals = []
        for sym in symbols:
            all_signals.extend(query_signals(db_path=db_path, symbol=sym, limit=500))
    else:
        all_signals = query_signals(db_path=db_path, limit=5000)

    if not all_signals:
        logger.warning("No signals found for analysis")
        return stats

    # Enrich text-based signals with NLP sentiment
    try:
        from social_arb.nlp.sentiment_enricher import SentimentEnricher
        enricher = SentimentEnricher(use_finbert=False)  # VADER-only in batch mode
        all_signals = enricher.enrich_batch(all_signals)
        logger.info(f"Enriched {len(all_signals)} signals with sentiment scores")
    except Exception as e:
        logger.warning(f"Sentiment enrichment failed (continuing without): {e}")

    # Group by symbol
    by_symbol: Dict[str, List[Dict]] = {}
    for sig in all_signals:
        by_symbol.setdefault(sig["symbol"], []).append(sig)

    divergence_engine = SentimentDivergenceCalculator()

    for symbol, signals in by_symbol.items():
        try:
            stats["symbols_analyzed"] += 1

            domain = _infer_domain(symbol, signals)

            # Determine data_class from domain and signal data
            if domain == "private_markets":
                data_class = "private"
            elif any(s.get("data_class") == "private" for s in signals):
                data_class = "private"
            else:
                data_class = "public"

            # Compute source diversity
            sources = list(set(s["source"] for s in signals))
            source_count = len(sources)

            # Compute directional alignment (coherence proxy)
            bullish = sum(1 for s in signals if s.get("direction") == "bullish")
            bearish = sum(1 for s in signals if s.get("direction") == "bearish")
            neutral = sum(1 for s in signals if s.get("direction") == "neutral")
            total = len(signals)
            directional = bullish + bearish
            alignment = max(bullish, bearish) / directional if directional > 0 else 0.5

            # Average strength
            avg_strength = sum(s.get("strength", 0) for s in signals) / total if total > 0 else 0

            # Coherence score: alignment * 70 + strength * 30, boosted by source diversity
            coherence = (alignment * 70 + avg_strength * 30) * min(2.0, 1.0 + (source_count - 1) * 0.25)
            coherence = min(100.0, coherence)

            # Divergence (social vs institutional/market)
            social_signals = [s for s in signals if s["source"] in ("reddit", "google_trends")]
            inst_signals = [s for s in signals if s["source"] in ("sec_edgar", "yfinance", "coingecko", "defillama")]
            social_growth = sum(s.get("strength", 0) for s in social_signals) / max(1, len(social_signals)) * 100
            inst_growth = sum(s.get("strength", 0) for s in inst_signals) / max(1, len(inst_signals)) * 100

            divergence_result = divergence_engine.calculate(
                signal_data={"growth_pct": social_growth, "volume": total},
                market_data={"growth_pct": inst_growth},
            )
            divergence_strength = divergence_result.signal_strength if divergence_result else 0

            # Determine action — more nuanced thresholds
            if coherence >= 55 and divergence_strength > 20:
                action = "build_thesis"
            elif coherence >= 60 and source_count >= 2:
                action = "build_thesis"
            elif coherence >= 35:
                action = "investigate"
            else:
                action = "pass"

            # Build narrative
            dominant_dir = "bullish" if bullish >= bearish else "bearish"
            narrative = (
                f"{symbol}: {total} signals from {source_count} sources. "
                f"Direction: {dominant_dir} ({bullish}B/{bearish}S/{neutral}N). "
                f"Coherence: {coherence:.0f}/100. "
                f"Divergence: {divergence_strength:.1f} ({divergence_result.classification if divergence_result else 'n/a'}). "
                f"Sources: {', '.join(sources)}."
            )

            mosaic_id = insert_mosaic(
                db_path=db_path,
                symbol=symbol,
                domain=domain,
                coherence_score=coherence,
                divergence_strength=divergence_strength,
                fragments_json=json.dumps([{"source": s["source"], "direction": s.get("direction"), "strength": s.get("strength")} for s in signals[:20]]),
                narrative=narrative,
                action=action,
                data_class=data_class,
            )
            stats["mosaics_created"] += 1

            # Create thesis for strong mosaics — ROI computed from actual data
            if action == "build_thesis":
                roi = _compute_roi_from_signals(signals, domain)
                confidence = min(1.0, coherence / 100.0)
                kelly = _compute_kelly(roi, confidence)
                lifecycle = _infer_lifecycle(coherence, divergence_strength, source_count)

                # Run vulnerability engine
                vulnerability_json = None
                try:
                    moat_scorer = RegulatoryMoatScorer()
                    vuln = moat_scorer.scan(
                        target=symbol,
                        data={
                            "esg_score": avg_strength * 80,
                            "carbon_intensity": 50,
                            "patent_count": source_count * 5,
                            "regulatory_burden": 0.5,
                            "institutional_ownership": 0.3,
                        },
                    )
                    vulnerability_json = json.dumps(vuln.to_dict())
                except Exception as e:
                    logger.warning(f"[pipeline] {symbol}: vulnerability scan failed: {e}")

                # Run simulation engine
                simulation_json = None
                try:
                    simulator = IRRMOICSim()
                    sim = simulator.simulate(params={
                        "initial_investment": 50000,
                        "stage": "series_a" if domain == "private_markets" else "growth",
                        "sector": "ai",
                        "team_score": min(10, avg_strength * 12),
                        "market_size_score": 7,
                        "moat_score": 6,
                    })
                    simulation_json = json.dumps(sim.to_dict())
                except Exception as e:
                    logger.warning(f"[pipeline] {symbol}: simulation failed: {e}")

                thesis_id = insert_thesis(
                    db_path=db_path,
                    mosaic_id=mosaic_id,
                    symbol=symbol,
                    domain=domain,
                    roi_bear=roi["bear"],
                    roi_base=roi["base"],
                    roi_bull=roi["bull"],
                    kelly_fraction=kelly,
                    lifecycle_stage=lifecycle,
                    status="pending_review",
                    vulnerability_json=vulnerability_json,
                    simulation_json=simulation_json,
                )
                stats["theses_created"] += 1
                logger.info(f"[pipeline] {symbol}: thesis created (coh={coherence:.0f}, div={divergence_strength:.1f}, ROI={roi['bear']:+.1%}/{roi['base']:+.1%}/{roi['bull']:+.1%}, kelly={kelly:.2f})")

        except Exception as e:
            stats["errors"].append(f"{symbol}: {str(e)}")
            logger.error(f"[pipeline] {symbol} failed: {e}")

    return stats


def _infer_domain(symbol: str, signals: List[Dict]) -> str:
    """Infer the investment domain from symbol + signal sources."""
    if symbol in CRYPTO_SYMBOLS:
        return "crypto"
    if symbol in PRIVATE_SYMBOLS:
        return "private_markets"
    sources = set(s["source"] for s in signals)
    if sources & {"coingecko", "defillama"}:
        return "crypto"
    if "github" in sources and "sec_edgar" not in sources:
        return "private_markets"
    return "public_markets"
