"""Social Arb — WSGI API server.

Serves data from SQLite or PostgreSQL (auto-detected from DATABASE_URL).
Works with gunicorn in production, stdlib HTTPServer for local dev.

Run locally:  python -m social_arb.api_server
Production:   gunicorn social_arb.api_server:app --bind 0.0.0.0:8080
"""

import json
import os
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs

from social_arb.db.adapter import get_connection, get_db_backend
from social_arb.db.schema import DEFAULT_DB_PATH


# ---------------------------------------------------------------------------
# WSGI Application (for gunicorn)
# ---------------------------------------------------------------------------

def app(environ, start_response):
    """WSGI application entry point."""
    path = environ.get("PATH_INFO", "/")
    method = environ.get("REQUEST_METHOD", "GET")
    qs = parse_qs(environ.get("QUERY_STRING", ""))

    try:
        if method == "GET":
            status, body = _route_get(path, qs)
        elif method == "POST":
            status, body = _route_post(path, qs, environ)
        else:
            status, body = "405 Method Not Allowed", json.dumps({"error": "method not allowed"})
    except Exception as e:
        status, body = "500 Internal Server Error", json.dumps({"error": str(e)})

    # Dashboard HTML
    if path == "/" and isinstance(body, bytes):
        headers = [("Content-Type", "text/html"), ("Access-Control-Allow-Origin", "*")]
        start_response(status, headers)
        return [body]

    headers = [
        ("Content-Type", "application/json"),
        ("Access-Control-Allow-Origin", "*"),
    ]
    start_response(status, headers)
    return [body.encode() if isinstance(body, str) else body]


def _route_get(path, params):
    """Route GET requests."""
    if path == "/api/summary":
        return "200 OK", _json(_get_summary())
    elif path == "/api/signals":
        return "200 OK", _json(_get_signals(params))
    elif path == "/api/mosaics":
        return "200 OK", _json(_get_mosaics(params))
    elif path == "/api/theses":
        return "200 OK", _json(_get_theses(params))
    elif path == "/api/decisions":
        return "200 OK", _json(_get_decisions())
    elif path == "/api/positions":
        return "200 OK", _json(_get_positions())
    elif path == "/api/scans":
        return "200 OK", _json(_get_scans())
    elif path == "/api/symbol" and "s" in params:
        return "200 OK", _json(_get_symbol_detail(params["s"][0]))
    elif path == "/api/status":
        return "200 OK", _json(_get_status())
    elif path == "/api/health":
        return "200 OK", _json({"status": "ok", "backend": get_db_backend()})
    elif path == "/":
        return _serve_dashboard()
    else:
        return "404 Not Found", _json({"error": "not found"})


def _route_post(path, params, environ):
    """Route POST requests (for Cloud Scheduler triggers)."""
    if path == "/api/collect":
        domain = params.get("domain", ["public"])[0]
        return _run_collect(domain)
    elif path == "/api/analyze":
        return _run_analyze()
    else:
        return "404 Not Found", _json({"error": "not found"})


# ---------------------------------------------------------------------------
# Collection & Analysis endpoints (for Cloud Scheduler)
# ---------------------------------------------------------------------------

def _run_collect(domain):
    """Run data collection in background thread."""
    def _do_collect():
        try:
            from social_arb.config import config
            from social_arb.db.schema import init_db
            from social_arb.db.store import start_scan, insert_signals_batch, complete_scan
            import json as _json

            init_db()

            symbols = {
                "public": config.public_symbols,
                "crypto": config.crypto_symbols,
                "private": config.private_symbols,
            }.get(domain, config.public_symbols)

            sources = {
                "public": ["yfinance", "reddit", "trends", "sec_edgar"],
                "crypto": ["coingecko", "defillama", "reddit"],
                "private": ["github", "reddit", "trends"],
            }.get(domain, ["yfinance", "reddit", "trends"])

            scan_id = start_scan(scan_type=domain, sources=sources, symbols=symbols)

            all_signals = []
            errors = []

            for source_name in sources:
                try:
                    mod = __import__(
                        f"social_arb.collectors.{source_name}_collector",
                        fromlist=["Collector"],
                    )
                    CollectorClass = None
                    for attr in dir(mod):
                        obj = getattr(mod, attr)
                        if (
                            isinstance(obj, type)
                            and attr != "BaseCollector"
                            and hasattr(obj, "collect")
                        ):
                            CollectorClass = obj
                            break
                    if CollectorClass:
                        collector = CollectorClass()
                        result = collector.collect(symbols=symbols)
                        if result and result.signals:
                            for s in result.signals:
                                sig = {**s, "scan_id": scan_id}
                                if "raw" in sig and "raw_json" not in sig:
                                    sig["raw_json"] = _json.dumps(
                                        sig.pop("raw"), default=str
                                    )
                                all_signals.append(sig)
                except Exception as e:
                    errors.append(f"{source_name}: {str(e)}")

            count = 0
            if all_signals:
                count = insert_signals_batch(signals=all_signals)

            complete_scan(scan_id=scan_id, signal_count=count, errors=errors)
        except Exception as e:
            print(f"Collection error: {e}")

    thread = threading.Thread(target=_do_collect, daemon=True)
    thread.start()
    return "202 Accepted", _json({"status": "collecting", "domain": domain})


def _run_analyze():
    """Run analysis pipeline in background thread."""
    def _do_analyze():
        try:
            from social_arb.pipeline import run_analysis
            run_analysis()
        except Exception as e:
            print(f"Analysis error: {e}")

    thread = threading.Thread(target=_do_analyze, daemon=True)
    thread.start()
    return "202 Accepted", _json({"status": "analyzing"})


# ---------------------------------------------------------------------------
# Query helpers
# ---------------------------------------------------------------------------

def _json(obj):
    return json.dumps(obj, default=str)


def _query(sql, params=None):
    """Execute a read query and return list of dicts."""
    with get_connection() as conn:
        cursor = conn.execute(sql, params or ())
        rows = cursor.fetchall()
        return [dict(r) for r in rows]


def _query_one(sql, params=None):
    """Execute a read query and return single dict."""
    with get_connection() as conn:
        cursor = conn.execute(sql, params or ())
        row = cursor.fetchone()
        return dict(row) if row else {}


def _parse_json_fields(rows, fields):
    for row in rows:
        for f in fields:
            if row.get(f):
                try:
                    row[f] = json.loads(row[f])
                except (json.JSONDecodeError, TypeError):
                    pass
    return rows


# ---------------------------------------------------------------------------
# Data endpoints
# ---------------------------------------------------------------------------

def _get_summary():
    summary = {}
    summary["source_counts"] = {
        r["source"]: r["cnt"]
        for r in _query(
            "SELECT source, COUNT(*) as cnt FROM signals GROUP BY source"
        )
    }
    summary["symbol_counts"] = {
        r["symbol"]: r["cnt"]
        for r in _query(
            "SELECT symbol, COUNT(*) as cnt FROM signals GROUP BY symbol ORDER BY cnt DESC"
        )
    }
    summary["direction_counts"] = {
        r["direction"]: r["cnt"]
        for r in _query(
            "SELECT direction, COUNT(*) as cnt FROM signals GROUP BY direction"
        )
    }
    summary["total_signals"] = _query_one(
        "SELECT COUNT(*) as c FROM signals"
    ).get("c", 0)
    summary["total_mosaics"] = _query_one(
        "SELECT COUNT(*) as c FROM mosaics"
    ).get("c", 0)
    summary["total_theses"] = _query_one(
        "SELECT COUNT(*) as c FROM theses"
    ).get("c", 0)
    summary["total_decisions"] = _query_one(
        "SELECT COUNT(*) as c FROM decisions"
    ).get("c", 0)
    summary["total_positions"] = _query_one(
        "SELECT COUNT(*) as c FROM positions"
    ).get("c", 0)
    summary["thesis_statuses"] = {
        r["status"]: r["cnt"]
        for r in _query(
            "SELECT status, COUNT(*) as cnt FROM theses GROUP BY status"
        )
    }
    summary["domain_counts"] = {
        r["domain"]: r["cnt"]
        for r in _query(
            "SELECT domain, COUNT(*) as cnt FROM mosaics GROUP BY domain"
        )
    }
    return summary


def _get_status():
    return {
        "backend": get_db_backend(),
        "signals": _query_one("SELECT COUNT(*) as c FROM signals").get("c", 0),
        "mosaics": _query_one("SELECT COUNT(*) as c FROM mosaics").get("c", 0),
        "theses": _query_one("SELECT COUNT(*) as c FROM theses").get("c", 0),
        "positions": _query_one(
            "SELECT COUNT(*) as c FROM positions WHERE status = 'open'"
        ).get("c", 0),
    }


def _get_signals(params):
    ph = "?" if get_db_backend() == "sqlite" else "%s"
    sql = "SELECT * FROM signals WHERE 1=1"
    args = []
    if "symbol" in params:
        sql += f" AND symbol = {ph}"
        args.append(params["symbol"][0])
    if "source" in params:
        sql += f" AND source = {ph}"
        args.append(params["source"][0])
    limit = int(params.get("limit", [500])[0])
    sql += f" ORDER BY timestamp DESC LIMIT {ph}"
    args.append(limit)
    rows = _query(sql, tuple(args))
    return _parse_json_fields(rows, ["raw_json"])


def _get_mosaics(params):
    if "symbol" in params:
        ph = "?" if get_db_backend() == "sqlite" else "%s"
        rows = _query(
            f"SELECT * FROM mosaics WHERE symbol = {ph} ORDER BY created_at DESC",
            (params["symbol"][0],),
        )
    else:
        rows = _query("SELECT * FROM mosaics ORDER BY coherence_score DESC")
    return _parse_json_fields(rows, ["fragments_json"])


def _get_theses(params):
    if "status" in params:
        ph = "?" if get_db_backend() == "sqlite" else "%s"
        return _query(
            f"SELECT * FROM theses WHERE status = {ph} ORDER BY created_at DESC",
            (params["status"][0],),
        )
    return _query("SELECT * FROM theses ORDER BY created_at DESC")


def _get_decisions():
    return _query("SELECT * FROM decisions ORDER BY created_at DESC LIMIT 50")


def _get_positions():
    return _query("SELECT * FROM positions ORDER BY created_at DESC")


def _get_scans():
    rows = _query("SELECT * FROM scans ORDER BY started_at DESC LIMIT 20")
    return _parse_json_fields(rows, ["sources_json", "symbols_json", "errors_json"])


def _get_symbol_detail(symbol):
    ph = "?" if get_db_backend() == "sqlite" else "%s"
    data = {"symbol": symbol}
    data["signals"] = _parse_json_fields(
        _query(
            f"SELECT * FROM signals WHERE symbol = {ph} ORDER BY timestamp DESC",
            (symbol,),
        ),
        ["raw_json"],
    )
    data["mosaics"] = _parse_json_fields(
        _query(
            f"SELECT * FROM mosaics WHERE symbol = {ph} ORDER BY created_at DESC",
            (symbol,),
        ),
        ["fragments_json"],
    )
    data["theses"] = _query(
        f"SELECT * FROM theses WHERE symbol = {ph} ORDER BY created_at DESC",
        (symbol,),
    )
    data["decisions"] = _query(
        f"SELECT * FROM decisions WHERE symbol = {ph} ORDER BY created_at DESC",
        (symbol,),
    )
    return data


def _serve_dashboard():
    dashboard_path = Path(__file__).parent.parent / "dashboard.html"
    if dashboard_path.exists():
        return "200 OK", dashboard_path.read_bytes()
    return "404 Not Found", json.dumps({"error": "dashboard not built"}).encode()


# ---------------------------------------------------------------------------
# Standalone server (local dev)
# ---------------------------------------------------------------------------

PORT = int(os.getenv("PORT", "8787"))


class DevHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        try:
            status, body = _route_get(parsed.path, params)
        except Exception as e:
            status, body = "500 Internal Server Error", _json({"error": str(e)})

        code = int(status.split()[0])
        self.send_response(code)
        if isinstance(body, bytes):
            self.send_header("Content-Type", "text/html")
        else:
            self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body.encode() if isinstance(body, str) else body)

    def do_POST(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        try:
            status, body = _route_post(parsed.path, params, {})
        except Exception as e:
            status, body = "500 Internal Server Error", _json({"error": str(e)})

        code = int(status.split()[0])
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body.encode() if isinstance(body, str) else body)

    def log_message(self, format, *args):
        pass


def main():
    from social_arb.db.schema import init_db

    init_db()
    print(f"Social Arb API running on http://localhost:{PORT}")
    print(f"Backend: {get_db_backend()}")
    server = HTTPServer(("0.0.0.0", PORT), DevHandler)
    server.serve_forever()


if __name__ == "__main__":
    main()
