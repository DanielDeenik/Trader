"""Task handlers for collection, analysis, and backfill jobs."""

import logging
from typing import Dict, Any, List

from social_arb.db import store
from social_arb.db.schema import DEFAULT_DB_PATH
from social_arb.collectors.yfinance_collector import YFinanceCollector
from social_arb.collectors.reddit_collector import RedditCollector
from social_arb.collectors.sec_edgar_collector import SECEdgarCollector
from social_arb.collectors.trends_collector import TrendsCollector
from social_arb.collectors.github_collector import GitHubCollector
from social_arb.collectors.coingecko_collector import CoinGeckoCollector
from social_arb.collectors.defillama_collector import DeFiLlamaCollector
from social_arb.pipeline import run_analysis

logger = logging.getLogger(__name__)

# Collector registry — instantiate once
COLLECTORS = {
    "yfinance": YFinanceCollector(),
    "reddit": RedditCollector(),
    "sec_edgar": SECEdgarCollector(),
    "google_trends": TrendsCollector(),
    "github": GitHubCollector(),
    "coingecko": CoinGeckoCollector(),
    "defillama": DeFiLlamaCollector(),
}


async def handle_collect(
    params: Dict[str, Any],
    db_path: str = DEFAULT_DB_PATH,
) -> Dict[str, Any]:
    """
    Handle a 'collect' task.

    Params:
        sources: List[str] - data sources to collect from
        symbols: Optional[List[str]] - specific symbols; if None, collect all tracked
        domain: str - 'public' or 'private'
    """
    sources = params.get("sources", [])
    symbols = params.get("symbols")

    logger.info(f"Collect task starting: sources={sources}, symbols={symbols}")

    # If symbols not specified, get all tracked instruments
    if symbols is None:
        instruments = store.query_instruments(db_path=db_path)
        symbols = [inst["symbol"] for inst in instruments]

    if not symbols:
        logger.warning("No symbols to collect")
        return {"signal_count": 0, "errors": ["No symbols specified"], "source_results": {}}

    total_signals = 0
    errors = []
    source_results = {}

    for source in sources:
        try:
            collector = COLLECTORS.get(source)
            if not collector:
                msg = f"Unknown source: {source}"
                logger.error(msg)
                errors.append(msg)
                source_results[source] = {"count": 0, "error": msg}
                continue

            logger.info(f"Collecting from {source} for {len(symbols)} symbols")

            # Call collector's collect method
            result = collector.collect(symbols=symbols)

            # Batch insert signals
            if result.signals:
                count = store.insert_signals_batch(signals=result.signals, db_path=db_path)
                total_signals += count
                source_results[source] = {"count": count, "error": None}
                logger.info(f"Collected {count} signals from {source}")
            else:
                source_results[source] = {"count": 0, "error": None}

            # Track errors from collector
            if result.errors:
                errors.extend(result.errors)

        except Exception as e:
            msg = f"Error collecting from {source}: {str(e)}"
            logger.error(msg, exc_info=True)
            errors.append(msg)
            source_results[source] = {"count": 0, "error": str(e)}

    logger.info(f"Collect task completed: {total_signals} total signals, {len(errors)} errors")

    return {
        "signal_count": total_signals,
        "errors": errors,
        "source_results": source_results,
    }


async def handle_analyze(
    params: Dict[str, Any],
    db_path: str = DEFAULT_DB_PATH,
) -> Dict[str, Any]:
    """
    Handle an 'analyze' task. Runs the full analysis pipeline.

    Params:
        symbols: Optional[List[str]] - specific symbols; if None, analyze all
    """
    symbols = params.get("symbols")

    logger.info(f"Analyze task starting: symbols={symbols}")

    if symbols is None:
        signals = store.query_signals(db_path=db_path, limit=10000)
        symbols = list(set(s["symbol"] for s in signals))

    if not symbols:
        logger.warning("No symbols to analyze")
        return {"analyzed_count": 0, "errors": ["No symbols specified"], "mosaic_count": 0, "thesis_count": 0}

    errors = []

    try:
        logger.info(f"Running analysis pipeline for {len(symbols)} symbols")
        stats = run_analysis(db_path=db_path, symbols=symbols)
        analyzed = len(symbols)

        mosaics = store.query_mosaics(db_path=db_path, limit=10000)
        theses = store.query_theses(db_path=db_path, limit=10000)

        logger.info(f"Analysis complete: {len(mosaics)} mosaics, {len(theses)} theses")

        return {
            "analyzed_count": analyzed,
            "errors": errors,
            "mosaic_count": len(mosaics),
            "thesis_count": len(theses),
        }

    except Exception as e:
        msg = f"Analysis pipeline error: {str(e)}"
        logger.error(msg, exc_info=True)
        errors.append(msg)
        return {"analyzed_count": 0, "errors": errors, "mosaic_count": 0, "thesis_count": 0}


async def handle_backfill(
    params: Dict[str, Any],
    db_path: str = DEFAULT_DB_PATH,
) -> Dict[str, Any]:
    """
    Handle a 'backfill' task. Fetches historical data.

    Params:
        source: str - data source
        symbol: str - symbol to backfill
        start_date: str - ISO date
        end_date: str - ISO date
    """
    source = params.get("source")
    symbol = params.get("symbol")
    start_date = params.get("start_date")
    end_date = params.get("end_date")

    logger.info(f"Backfill task: source={source}, symbol={symbol}, {start_date} to {end_date}")

    if not source or not symbol or not start_date or not end_date:
        msg = "Missing required params: source, symbol, start_date, end_date"
        logger.error(msg)
        return {"bar_count": 0, "error": msg}

    try:
        collector = COLLECTORS.get(source)
        if not collector:
            msg = f"Unknown source: {source}"
            logger.error(msg)
            return {"bar_count": 0, "error": msg}

        logger.info(f"Backfilling {symbol} from {source}")

        # Use collect with date params for backfill
        result = collector.collect(
            symbols=[symbol],
            period=f"{start_date}:{end_date}",
        )

        if result.signals:
            count = store.insert_signals_batch(signals=result.signals, db_path=db_path)
            logger.info(f"Backfilled {count} signals for {symbol}")
            return {"bar_count": count, "error": None}
        else:
            logger.warning(f"No data returned for {symbol}")
            return {"bar_count": 0, "error": None}

    except Exception as e:
        msg = f"Backfill error: {str(e)}"
        logger.error(msg, exc_info=True)
        return {"bar_count": 0, "error": msg}
