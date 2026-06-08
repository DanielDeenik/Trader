"""Option B lakehouse: sync to Parquet + DuckDB analytical parity."""

import os
from datetime import datetime, timedelta

import pytest

from social_arb.db.schema import init_db
from social_arb.db.adapter import get_connection
from social_arb.engine.trend_scorer import get_trending_tickers
from social_arb.lake import sync_to_parquet, LAKE_TABLES


def _seed(db_path):
    now = datetime.utcnow()
    iso = lambda h: (now - timedelta(hours=h)).isoformat()
    with get_connection(db_path) as c:
        for i, sym in enumerate(["NVDA", "TSLA", "SOFI", "RIOT"]):
            c.execute(
                "INSERT INTO instruments (symbol,name,type,sector,vertical,data_class)"
                " VALUES (?,?,?,?,?,?)",
                (sym, f"{sym} Inc", "crypto" if sym == "RIOT" else "stock",
                 "Tech", "AI", "public"),
            )
            for j in range((i + 2) * 3):
                c.execute(
                    "INSERT INTO signals (symbol,source,signal_type,direction,"
                    "strength,confidence,timestamp,raw_json) VALUES (?,?,?,?,?,?,?,?)",
                    (sym, ["reddit", "yfinance", "sec_edgar", "github", "news"][j % 5],
                     "mention", ["bullish", "bearish", "neutral"][j % 3],
                     0.6, 0.7, iso(j % 48), "{}"),
                )
            c.execute(
                "INSERT INTO mosaics (symbol,domain,coherence_score,divergence_strength,"
                "narrative,action,fragments_json,created_at) VALUES (?,?,?,?,?,?,?,?)",
                (sym, "public_markets", 72 + i, 22 + i * 4, f"{sym} story",
                 ["build_thesis", "investigate", "pass"][i % 3], "[]", iso(1)),
            )


@pytest.fixture(autouse=True)
def _clean_env():
    saved = {k: os.environ.get(k) for k in ("LAKE_DIR", "DATABASE_URL")}
    os.environ.pop("LAKE_DIR", None)
    os.environ.pop("DATABASE_URL", None)
    # Reset the cached lake connection between tests.
    import social_arb.lake.query as q
    q.refresh_lake()
    yield
    for k, v in saved.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v
    q.refresh_lake()


def test_sync_writes_parquet(tmp_path):
    db = str(tmp_path / "op.db")
    lake = str(tmp_path / "lake")
    init_db(db)
    _seed(db)

    written = sync_to_parquet(db_path=db, lake_dir=lake)

    assert written["signals"] > 0
    assert written["mosaics"] == 4
    for table in LAKE_TABLES:
        assert (tmp_path / "lake" / f"{table}.parquet").exists()


def test_lakehouse_matches_operational(tmp_path):
    db = str(tmp_path / "op.db")
    lake = str(tmp_path / "lake")
    init_db(db)
    _seed(db)

    operational = get_trending_tickers(db, hours=168, limit=50)
    sync_to_parquet(db_path=db, lake_dir=lake)

    os.environ["LAKE_DIR"] = lake
    import social_arb.lake.query as q
    q.refresh_lake()
    lakehouse = get_trending_tickers(db, hours=168, limit=50)

    def key(rows):
        return {r["symbol"]: (r["trend_score"], r["signal_count"],
                              r["source_count"], r["direction"],
                              r["divergence"], r["coherence"]) for r in rows}

    assert key(operational) == key(lakehouse)
    assert len(lakehouse) == 4


def test_lakehouse_serves_when_operational_empty(tmp_path):
    """Data must come from Parquet even when the operational store is wiped."""
    db = str(tmp_path / "op.db")
    lake = str(tmp_path / "lake")
    init_db(db)
    _seed(db)
    sync_to_parquet(db_path=db, lake_dir=lake)

    with get_connection(db) as c:
        c.execute("DELETE FROM signals")

    os.environ["LAKE_DIR"] = lake
    import social_arb.lake.query as q
    q.refresh_lake()
    lakehouse = get_trending_tickers(db, hours=168, limit=50)

    assert len(lakehouse) == 4  # served from the lake, not the empty op store
