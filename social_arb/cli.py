"""Social Arb CLI — collect, analyze, review, status."""

import logging
import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from social_arb.config import config
from social_arb.db.schema import init_db
from social_arb.db.store import (
    start_scan, complete_scan, query_signals, query_mosaics,
    query_theses, query_positions, query_decisions,
    insert_decision,
)

console = Console()


@click.group()
@click.option("--db", default=None, help="Database path override")
@click.option("--verbose", is_flag=True)
def cli(db, verbose):
    """Social Arb — Information Arbitrage Engine"""
    if db:
        config.db_path = db
    if verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=getattr(logging, config.log_level))
    init_db(config.db_path)


@cli.command()
@click.option("--sources", default="yfinance,reddit,sec_edgar,github,coingecko,defillama", help="Comma-separated collectors")
@click.option("--symbols", default=None, help="Override symbols (comma-separated)")
@click.option("--domain", default="all", type=click.Choice(["all", "public", "private", "crypto"]), help="Which domain to collect")
def collect(sources, symbols, domain):
    """Collect signals from real data sources."""
    from social_arb.collectors.yfinance_collector import YFinanceCollector
    from social_arb.collectors.reddit_collector import RedditCollector
    from social_arb.collectors.sec_edgar_collector import SECEdgarCollector
    from social_arb.collectors.github_collector import GitHubCollector
    from social_arb.collectors.coingecko_collector import CoinGeckoCollector
    from social_arb.collectors.defillama_collector import DeFiLlamaCollector

    source_list = [s.strip() for s in sources.split(",")]

    # Domain-specific symbol routing
    if symbols:
        symbol_list = [s.strip() for s in symbols.split(",")]
    elif domain == "public":
        symbol_list = config.public_symbols
    elif domain == "private":
        symbol_list = config.private_symbols
    elif domain == "crypto":
        symbol_list = config.crypto_symbols
    else:
        symbol_list = config.all_symbols

    collectors = {
        "yfinance": YFinanceCollector(),
        "reddit": RedditCollector(),
        "sec_edgar": SECEdgarCollector(),
        "github": GitHubCollector(),
        "coingecko": CoinGeckoCollector(),
        "defillama": DeFiLlamaCollector(),
    }

    scan_id = start_scan(
        db_path=config.db_path,
        scan_type="collect",
        sources=source_list,
        symbols=symbol_list,
    )

    console.print(f"\n[bold gold1]SOCIAL ARB — Collecting signals[/bold gold1]")
    console.print(f"Scan #{scan_id} | Sources: {', '.join(source_list)} | Symbols: {len(symbol_list)}\n")

    total_signals = 0
    all_errors = []

    for source_name in source_list:
        collector = collectors.get(source_name)
        if not collector:
            console.print(f"  [red]Unknown source: {source_name}[/red]")
            continue

        with console.status(f"  Collecting from {source_name}..."):
            result = collector.collect(symbols=symbol_list)

        # Store signals — convert "raw" dict to "raw_json" string for DB
        if result.signals:
            import json as _json
            from social_arb.db.store import insert_signals_batch
            prepared = []
            for s in result.signals:
                sig = {**s, "scan_id": scan_id}
                if "raw" in sig and "raw_json" not in sig:
                    sig["raw_json"] = _json.dumps(sig.pop("raw"), default=str)
                prepared.append(sig)
            count = insert_signals_batch(
                db_path=config.db_path,
                signals=prepared,
            )
            total_signals += count
            console.print(f"  [green]✓[/green] {source_name}: {count} signals")
        else:
            console.print(f"  [yellow]–[/yellow] {source_name}: 0 signals")

        if result.errors:
            all_errors.extend(result.errors)
            for err in result.errors:
                console.print(f"    [dim red]{err}[/dim red]")

    complete_scan(
        db_path=config.db_path,
        scan_id=scan_id,
        signal_count=total_signals,
        errors=all_errors,
    )

    console.print(f"\n[bold]Total: {total_signals} signals collected[/bold]\n")


@cli.command()
@click.option("--symbols", default=None, help="Override symbols (comma-separated)")
def analyze(symbols):
    """Run batch analysis on collected signals."""
    from social_arb.pipeline import run_analysis

    symbol_list = [s.strip() for s in symbols.split(",")] if symbols else None

    console.print(f"\n[bold gold1]SOCIAL ARB — Running analysis[/bold gold1]\n")

    with console.status("Analyzing signals..."):
        result = run_analysis(db_path=config.db_path, symbols=symbol_list)

    console.print(f"  Symbols analyzed: {result['symbols_analyzed']}")
    console.print(f"  Mosaics created:  {result['mosaics_created']}")
    console.print(f"  Theses created:   {result['theses_created']}")

    if result["errors"]:
        console.print(f"\n  [red]Errors:[/red]")
        for err in result["errors"]:
            console.print(f"    {err}")

    # Show top mosaics
    mosaics = query_mosaics(db_path=config.db_path, limit=10)
    if mosaics:
        table = Table(title="Top Mosaic Cards", style="gold1")
        table.add_column("Symbol", style="bold white")
        table.add_column("Coherence", justify="right")
        table.add_column("Divergence", justify="right")
        table.add_column("Action", style="bold")
        table.add_column("Class")
        for m in mosaics:
            action_color = "green" if m["action"] == "build_thesis" else ("yellow" if m["action"] == "investigate" else "dim")
            table.add_row(
                m["symbol"],
                f"{m['coherence_score']:.0f}",
                f"{m.get('divergence_strength', 0):.1f}",
                f"[{action_color}]{m['action']}[/{action_color}]",
                m.get("data_class", "public"),
            )
        console.print()
        console.print(table)
    console.print()


@cli.command()
def review():
    """HITL review — approve/reject/defer pending theses."""
    theses = query_theses(db_path=config.db_path, status="pending_review")

    if not theses:
        console.print("\n[dim]No theses pending review.[/dim]\n")
        return

    console.print(f"\n[bold gold1]SOCIAL ARB — HITL Review[/bold gold1]")
    console.print(f"{len(theses)} theses pending\n")

    for thesis in theses:
        # Show thesis details
        mosaic = query_mosaics(db_path=config.db_path, symbol=thesis["symbol"])
        mosaic_data = mosaic[0] if mosaic else {}

        panel_text = (
            f"[bold]{thesis['symbol']}[/bold] | {thesis['domain']} | {thesis.get('data_class', thesis.get('thesis_type', 'public')).upper()}\n"
            f"ROI: Bear {thesis.get('roi_bear', 0):+.0%} / Base {thesis.get('roi_base', 0):+.0%} / Bull {thesis.get('roi_bull', 0):+.0%}\n"
            f"Lifecycle: {thesis.get('lifecycle_stage', 'unknown')}\n"
            f"Narrative: {mosaic_data.get('narrative', 'N/A')}"
        )
        console.print(Panel(panel_text, title=f"Thesis #{thesis['id']}", border_style="gold1"))

        # HITL gate
        decision = click.prompt(
            "  Decision",
            type=click.Choice(["approve", "reject", "defer", "skip"], case_sensitive=False),
            default="skip",
        )

        if decision == "skip":
            continue

        rationale = ""
        if decision in ("reject", "defer"):
            rationale = click.prompt("  Rationale", default="")

        insert_decision(
            db_path=config.db_path,
            thesis_id=thesis["id"],
            gate="L3_review",
            symbol=thesis["symbol"],
            decision=decision,
            confidence=float(mosaic_data.get("coherence_score", 0)) / 100,
            rationale=rationale,
            trust_level="manual",
        )

        # Update thesis status
        from social_arb.db.adapter import get_connection, get_placeholder
        ph = get_placeholder()
        status_map = {"approve": "approved", "reject": "rejected", "defer": "pending_review"}
        with get_connection(config.db_path) as conn:
            conn.execute(
                f"UPDATE theses SET status = {ph} WHERE id = {ph}",
                (status_map.get(decision, "pending_review"), thesis["id"]),
            )

        color = "green" if decision == "approve" else ("red" if decision == "reject" else "yellow")
        console.print(f"  [{color}]→ {decision.upper()}[/{color}]\n")

    console.print("[bold]Review complete.[/bold]\n")


@cli.command()
def status():
    """Portfolio status and audit trail."""
    console.print(f"\n[bold gold1]SOCIAL ARB — Status[/bold gold1]\n")

    # Signals summary
    all_sigs = query_signals(db_path=config.db_path, limit=10000)
    public_count = sum(1 for s in all_sigs if s.get("data_class") == "public")
    private_count = sum(1 for s in all_sigs if s.get("data_class") == "private")

    console.print(f"  Signals:    {len(all_sigs)} total ({public_count} public, {private_count} private)")

    mosaics = query_mosaics(db_path=config.db_path, limit=1000)
    console.print(f"  Mosaics:    {len(mosaics)}")

    theses = query_theses(db_path=config.db_path)
    pending = sum(1 for t in theses if t.get("status") == "pending_review")
    approved = sum(1 for t in theses if t.get("status") == "approved")
    rejected = sum(1 for t in theses if t.get("status") == "rejected")
    console.print(f"  Theses:     {len(theses)} ({pending} pending, {approved} approved, {rejected} rejected)")

    positions = query_positions(db_path=config.db_path)
    console.print(f"  Positions:  {len(positions)} open")

    decisions = query_decisions(db_path=config.db_path, limit=10)
    if decisions:
        console.print(f"\n  [bold]Recent Decisions:[/bold]")
        table = Table()
        table.add_column("Time")
        table.add_column("Symbol")
        table.add_column("Gate")
        table.add_column("Decision")
        table.add_column("Rationale")
        for d in decisions[:5]:
            color = "green" if d["decision"] == "approve" else ("red" if d["decision"] == "reject" else "yellow")
            table.add_row(
                d.get("created_at", "")[:16],
                d["symbol"],
                d["gate"],
                f"[{color}]{d['decision']}[/{color}]",
                (d.get("rationale") or "")[:60],
            )
        console.print(table)

    console.print()


@cli.command()
@click.option("--symbols", default=None, help="Override symbols (comma-separated)")
@click.option("--domain", default="all", type=click.Choice(["all", "public", "crypto"]), help="Which domain to backfill")
@click.option("--period", default="max", help="yfinance period: 1y, 2y, 5y, 10y, max")
@click.option("--crypto-days", default=365, type=int, help="Days of crypto history from CoinGecko")
def backfill(symbols, domain, period, crypto_days):
    """Backfill historical OHLCV data into local archive.

    Pulls deep history from yfinance (stocks) and CoinGecko (crypto)
    into the ohlcv table. Safe to re-run — duplicates are skipped.
    """
    from social_arb.db.store import insert_ohlcv_batch

    console.print(f"\n[bold gold1]SOCIAL ARB — Backfill Time Series[/bold gold1]\n")

    total_bars = 0

    # --- Stocks via yfinance ---
    if domain in ("all", "public"):
        import yfinance as yf

        stock_symbols = [s.strip() for s in symbols.split(",")] if symbols and domain == "public" else config.public_symbols
        console.print(f"[bold]Stocks[/bold] ({len(stock_symbols)} symbols, period={period})")

        for sym in stock_symbols:
            with console.status(f"  Fetching {sym}..."):
                try:
                    ticker = yf.Ticker(sym)
                    hist = ticker.history(period=period)
                    if hist.empty:
                        console.print(f"  [yellow]–[/yellow] {sym}: no data")
                        continue

                    bars = []
                    for date, row in hist.iterrows():
                        bars.append({
                            "timestamp": date.strftime("%Y-%m-%d"),
                            "symbol": sym,
                            "open": float(row["Open"]),
                            "high": float(row["High"]),
                            "low": float(row["Low"]),
                            "close": float(row["Close"]),
                            "volume": int(row["Volume"]) if row["Volume"] > 0 else 0,
                            "data_class": "public",
                        })

                    count = insert_ohlcv_batch(
                        db_path=config.db_path,
                        bars=bars,
                        source="yfinance",
                    )
                    total_bars += count
                    console.print(f"  [green]✓[/green] {sym}: {count} bars ({len(hist)} total, {len(hist) - count} existing)")
                except Exception as e:
                    console.print(f"  [red]✗[/red] {sym}: {e}")

    # --- Crypto via CoinGecko market_chart ---
    if domain in ("all", "crypto"):
        import requests
        import time

        from social_arb.collectors.coingecko_collector import TOKEN_MAP

        crypto_symbols = [s.strip() for s in symbols.split(",")] if symbols and domain == "crypto" else config.crypto_symbols
        console.print(f"\n[bold]Crypto[/bold] ({len(crypto_symbols)} tokens, {crypto_days} days)")

        for sym in crypto_symbols:
            gecko_id = TOKEN_MAP.get(sym)
            if not gecko_id:
                console.print(f"  [yellow]–[/yellow] {sym}: not in TOKEN_MAP")
                continue

            with console.status(f"  Fetching {sym} ({gecko_id})..."):
                try:
                    url = f"https://api.coingecko.com/api/v3/coins/{gecko_id}/market_chart"
                    resp = requests.get(url, params={"vs_currency": "usd", "days": str(crypto_days)}, timeout=30)
                    resp.raise_for_status()
                    data = resp.json()

                    prices = data.get("prices", [])
                    volumes = data.get("total_volumes", [])

                    # CoinGecko returns [timestamp_ms, value] pairs
                    # Build daily OHLCV from price points
                    from datetime import datetime as dt
                    vol_map = {}
                    for ts_ms, vol in volumes:
                        day = dt.utcfromtimestamp(ts_ms / 1000).strftime("%Y-%m-%d")
                        vol_map[day] = vol

                    # Group prices by day to get open/high/low/close
                    day_prices = {}
                    for ts_ms, price in prices:
                        day = dt.utcfromtimestamp(ts_ms / 1000).strftime("%Y-%m-%d")
                        day_prices.setdefault(day, []).append(price)

                    bars = []
                    for day in sorted(day_prices.keys()):
                        p = day_prices[day]
                        bars.append({
                            "timestamp": day,
                            "symbol": sym,
                            "open": p[0],
                            "high": max(p),
                            "low": min(p),
                            "close": p[-1],
                            "volume": int(vol_map.get(day, 0)),
                            "data_class": "public",
                        })

                    count = insert_ohlcv_batch(
                        db_path=config.db_path,
                        bars=bars,
                        source="coingecko",
                    )
                    total_bars += count
                    console.print(f"  [green]✓[/green] {sym}: {count} bars ({len(bars)} total, {len(bars) - count} existing)")

                    # Rate limit: CoinGecko free tier = 10-30 req/min
                    time.sleep(2)
                except Exception as e:
                    console.print(f"  [red]✗[/red] {sym}: {e}")

    console.print(f"\n[bold]Total: {total_bars} new bars archived[/bold]")

    # Show archive stats
    from social_arb.db.adapter import get_connection
    with get_connection(config.db_path) as conn:
        row = conn.execute("SELECT COUNT(*) as c FROM ohlcv").fetchone()
        total = dict(row).get("c", 0)
        symbols_row = conn.execute("SELECT COUNT(DISTINCT symbol) as c FROM ohlcv").fetchone()
        sym_count = dict(symbols_row).get("c", 0)
        oldest = conn.execute("SELECT MIN(timestamp) as t FROM ohlcv").fetchone()
        newest = conn.execute("SELECT MAX(timestamp) as t FROM ohlcv").fetchone()
        console.print(f"  Archive: {total} bars across {sym_count} symbols")
        console.print(f"  Range: {dict(oldest).get('t', '?')} → {dict(newest).get('t', '?')}")
    console.print()


@cli.command()
def dashboard():
    """Start the local dashboard + API server."""
    from social_arb.api_server import main as serve
    serve()


def main():
    cli()


if __name__ == "__main__":
    main()
