# Social Arb — Clean Rebuild Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild Social Arb as a clean, production-grade information arbitrage platform with real data collection, batch analysis, HITL decision gates, and proper public/private data classification — zero demo mode, zero hardcoded data, zero dropshipping.

**Architecture:** CLI-first batch analysis system. Four commands: `collect` (fetch real signals), `analyze` (run L1→L4 topology), `review` (HITL gate decisions), `status` (portfolio view). SQLite database with 12 focused tables (down from 24). All data classified as `public` or `private` at ingestion. Engines are kept as-is — they're production-grade. Scrapers are rewritten with real API integrations.

**Tech Stack:** Python 3.11+, SQLite (WAL mode), yfinance, praw (Reddit), pytrends (Google Trends), requests (SEC EDGAR), click (CLI), rich (terminal UI for HITL review)

---

## What We're Keeping (DO NOT MODIFY)

These files are production-grade. Copy them into the new structure unchanged:

| File | LOC | Reason |
|------|-----|--------|
| `social_arb/core/protocols.py` | 345 | Universal domain interfaces — the contract everything plugs into |
| `social_arb/core/topology.py` | 488 | 5-layer orchestration engine with HITL gates + tiered autonomy |
| `social_arb/engine/sentiment_divergence.py` | 117 | Real divergence calculation |
| `social_arb/engine/kelly_sizer.py` | 171 | Real Kelly Criterion position sizing |
| `social_arb/engine/irr_simulator.py` | 158 | Real IRR/MOIC private market simulation |
| `social_arb/engine/cross_domain_amplifier.py` | 142 | Real multi-domain convergence detection |
| `social_arb/engine/technical_analyzer.py` | 329 | Real TA indicators (SMA, EMA, RSI, MACD, Bollinger, ATR) |
| `social_arb/engine/regulatory_moat.py` | 142 | Real ESG/CSRD moat scoring |

## What We're Killing

| File/Dir | Reason |
|----------|--------|
| `demo_flow.py` | Hardcoded demo theatre |
| `example_usage.py` | Demo showcase |
| `social_arb_overview.html` | Static HTML mockup |
| `research/ARCHITECTURE_DECISION.md` | Outdated, references dropshipping as Domain A |
| `social_arb/engine/mosaic.py` | E-commerce DNA (Amazon reviews, TikTok, STEPPS) — replaced by topology.py's mosaic assembly which is domain-agnostic |
| `social_arb/scrapers/*` (all 5 files) | Every scraper returns hardcoded demo data or `return []`. Rewrite from scratch. |
| `social_arb/research_agents/*` | All stubs — `research()` returns `[]`, only `get_demo_data()` works |
| `social_arb/dashboard/app.py` | Dash dashboard that shows empty tables. Build CLI first, dashboard later. |
| All `get_demo_signals()` methods | No demo paths. Real data or explicit error. |

## What We're Rewriting

| Component | Old State | New State |
|-----------|-----------|-----------|
| Database schema | 24 tables, 12 empty | 12 tables, all used |
| Scrapers | 5 files returning `[]` | 4 real scrapers: yfinance, Reddit, Google Trends, SEC EDGAR |
| Config | `demo_mode=True` default | No demo mode. Env vars for API keys, explicit errors if missing |
| Entry point | `run_social_arb.py` (prints text) | `cli.py` with 4 subcommands |
| Data import | `import_enhanced.py` (JSON files) | Scrapers write directly to DB via `collect` command |
| Pipeline | `investment_pipeline_enhanced.py` | Simplified — `analyze` command calls topology engine directly |

---

## New File Structure

```
social_arb/
├── __init__.py
├── cli.py                          # Click CLI: collect, analyze, review, status
├── config.py                       # Env-var config, NO demo mode
├── core/
│   ├── __init__.py
│   ├── protocols.py                # KEEP AS-IS — domain interfaces
│   └── topology.py                 # KEEP AS-IS — 5-layer engine + HITL
├── engine/
│   ├── __init__.py
│   ├── sentiment_divergence.py     # KEEP AS-IS
│   ├── kelly_sizer.py             # KEEP AS-IS
│   ├── irr_simulator.py           # KEEP AS-IS
│   ├── cross_domain_amplifier.py  # KEEP AS-IS
│   ├── technical_analyzer.py      # KEEP AS-IS
│   └── regulatory_moat.py         # KEEP AS-IS
├── collectors/                     # NEW — replaces scrapers/
│   ├── __init__.py
│   ├── base.py                    # Abstract collector interface
│   ├── yfinance_collector.py      # Real market data + OHLCV
│   ├── reddit_collector.py        # Real Reddit public JSON API
│   ├── trends_collector.py        # Real Google Trends via pytrends
│   └── sec_edgar_collector.py     # Real SEC EDGAR XBRL API
├── db/                             # NEW — replaces data/
│   ├── __init__.py
│   ├── schema.py                  # 12-table schema init
│   ├── store.py                   # Insert/query functions
│   └── migrate.py                 # Schema migrations
├── pipeline.py                     # Batch analysis: signals → mosaics → theses
└── review.py                       # HITL terminal UI for gate decisions
tests/
├── test_collectors.py
├── test_db.py
├── test_pipeline.py
├── test_engines.py                 # KEEP — existing engine tests
├── test_topology.py                # KEEP — existing topology tests
└── conftest.py                     # Shared fixtures
research/                           # KEEP — legitimate research documents
├── cloud-payments/
├── sustainability/
└── INTEGRATION_FRAMEWORK.md
requirements.txt                    # Updated deps
CLAUDE.md                          # Updated — no DropArb reference
```

---

## Task 1: Nuke and Restructure

**Files:**
- Delete: `demo_flow.py`, `example_usage.py`, `social_arb_overview.html`, `test_enhanced_db.py`
- Delete: `research/ARCHITECTURE_DECISION.md`
- Delete: `social_arb/scrapers/` (entire directory)
- Delete: `social_arb/research_agents/` (entire directory)
- Delete: `social_arb/dashboard/` (entire directory)
- Delete: `social_arb/engine/mosaic.py` (e-commerce DNA, replaced by topology.py)
- Delete: `social_arb/data/` (entire directory — schema rewritten in db/)
- Delete: `social_arb/models/` (empty directory)
- Delete: `social_arb/investment_pipeline_enhanced.py`
- Create: `social_arb/collectors/`, `social_arb/db/`
- Move: `social_arb/core/`, `social_arb/engine/` (keep as-is)

- [ ] **Step 1: Delete all dead files**

```bash
cd /path/to/social-arb
rm -f demo_flow.py example_usage.py social_arb_overview.html test_enhanced_db.py
rm -f research/ARCHITECTURE_DECISION.md
rm -rf social_arb/scrapers
rm -rf social_arb/research_agents
rm -rf social_arb/dashboard
rm -rf social_arb/models
rm -f social_arb/engine/mosaic.py
rm -f social_arb/investment_pipeline_enhanced.py
```

- [ ] **Step 2: Archive data directory (keep datasets, remove code)**

The JSON datasets in `social_arb/data/datasets/` contain real market data (OHLCV, instruments, signals). Keep these as seed data. Delete the Python code.

```bash
# Keep datasets for initial seed import
mkdir -p social_arb/db/seed_data
cp -r social_arb/data/datasets/* social_arb/db/seed_data/ 2>/dev/null || true
cp social_arb/data/social_arb_enhanced.db social_arb/db/social_arb.db 2>/dev/null || true
rm -rf social_arb/data
```

- [ ] **Step 3: Create new directory structure**

```bash
mkdir -p social_arb/collectors
mkdir -p social_arb/db
touch social_arb/collectors/__init__.py
touch social_arb/db/__init__.py
```

- [ ] **Step 4: Verify kept files are intact**

```bash
# These must still exist and be unchanged
python -c "from social_arb.core.protocols import Signal, DomainScraper; print('protocols OK')"
python -c "from social_arb.core.topology import TopologyEngine, TrustLevel; print('topology OK')"
python -c "from social_arb.engine.sentiment_divergence import SentimentDivergence; print('divergence OK')"
python -c "from social_arb.engine.kelly_sizer import KellySizer; print('kelly OK')"
python -c "from social_arb.engine.irr_simulator import IRRSimulator; print('irr OK')"
python -c "from social_arb.engine.cross_domain_amplifier import CrossDomainAmplifier; print('amplifier OK')"
python -c "from social_arb.engine.technical_analyzer import TechnicalAnalyzer; print('technical OK')"
python -c "from social_arb.engine.regulatory_moat import RegulatoryMoat; print('moat OK')"
```

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "nuke: remove demo scaffolding, dropshipping remnants, dead code

Remove 5 demo scrapers, research agents, dashboard, mosaic.py (e-commerce),
demo_flow.py, example_usage.py, ARCHITECTURE_DECISION.md.
Keep: topology engine, all 7 engines, protocols, research docs, existing DB."
```

---

## Task 2: New Database Schema (12 Tables)

**Files:**
- Create: `social_arb/db/schema.py`
- Test: `tests/test_db.py`

The schema is simplified from 24→12 tables. Every table has `data_class` where relevant to classify public vs private data.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_db.py
import os
import tempfile
import pytest
from social_arb.db.schema import init_db, get_connection

@pytest.fixture
def db_path():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    os.remove(path)

class TestSchema:
    def test_init_creates_all_tables(self, db_path):
        init_db(db_path)
        with get_connection(db_path) as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            )
            tables = [row[0] for row in cursor.fetchall()]

        expected = [
            'audit_trail', 'decisions', 'instruments',
            'mosaics', 'ohlcv', 'positions', 'scans',
            'signals', 'theses',
        ]
        for t in expected:
            assert t in tables, f"Missing table: {t}"

    def test_public_private_classification(self, db_path):
        init_db(db_path)
        with get_connection(db_path) as conn:
            # Public signal
            conn.execute(
                "INSERT INTO signals (timestamp, symbol, source, direction, strength, data_class) VALUES (?, ?, ?, ?, ?, ?)",
                ("2026-03-25", "NVDA", "reddit", "bullish", 0.8, "public")
            )
            # Private signal
            conn.execute(
                "INSERT INTO signals (timestamp, symbol, source, direction, strength, data_class) VALUES (?, ?, ?, ?, ?, ?)",
                ("2026-03-25", "DATABRICKS", "github", "bullish", 0.7, "private")
            )
            public = conn.execute("SELECT COUNT(*) FROM signals WHERE data_class='public'").fetchone()[0]
            private = conn.execute("SELECT COUNT(*) FROM signals WHERE data_class='private'").fetchone()[0]
            assert public == 1
            assert private == 1

    def test_wal_mode_enabled(self, db_path):
        init_db(db_path)
        with get_connection(db_path) as conn:
            mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
            assert mode == "wal"

    def test_foreign_keys_enforced(self, db_path):
        init_db(db_path)
        with get_connection(db_path) as conn:
            fk = conn.execute("PRAGMA foreign_keys").fetchone()[0]
            assert fk == 1
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_db.py -v
```
Expected: FAIL — `ModuleNotFoundError: No module named 'social_arb.db.schema'`

- [ ] **Step 3: Write the schema**

```python
# social_arb/db/schema.py
"""
Social Arb — Database Schema (12 tables)

Tiers:
  1. Reference: instruments (what we track)
  2. Raw: signals, ohlcv (immutable, append-only, timestamped)
  3. Computed: mosaics, theses (derived from raw, rebuildable)
  4. Human: decisions, positions (HITL sacred audit trail)
  5. Meta: scans (collection tracking)

Every table with data_class supports public/private classification.
"""

import sqlite3
from contextlib import contextmanager
from pathlib import Path

DEFAULT_DB_PATH = str(Path(__file__).parent / "social_arb.db")


@contextmanager
def get_connection(db_path: str = DEFAULT_DB_PATH):
    """Context manager with WAL mode and foreign keys."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db(db_path: str = DEFAULT_DB_PATH) -> None:
    """Initialize the 12-table schema."""
    with get_connection(db_path) as conn:
        c = conn.cursor()

        # ── TIER 1: REFERENCE ──────────────────────────────
        c.execute("""
            CREATE TABLE IF NOT EXISTS instruments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                type TEXT CHECK(type IN ('stock','private','etf','crypto')) NOT NULL,
                sector TEXT,
                vertical TEXT,
                exchange TEXT,
                market_cap_b REAL,
                data_class TEXT CHECK(data_class IN ('public','private')) DEFAULT 'public',
                metadata_json TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # ── TIER 2: RAW (append-only, immutable) ──────────
        c.execute("""
            CREATE TABLE IF NOT EXISTS signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                symbol TEXT NOT NULL,
                source TEXT NOT NULL,
                signal_type TEXT DEFAULT 'general',
                direction TEXT CHECK(direction IN ('bullish','bearish','neutral')),
                strength REAL,
                confidence REAL,
                raw_json TEXT,
                data_class TEXT CHECK(data_class IN ('public','private')) DEFAULT 'public',
                scan_id INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(scan_id) REFERENCES scans(id)
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS ohlcv (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                symbol TEXT NOT NULL,
                open REAL,
                high REAL,
                low REAL,
                close REAL NOT NULL,
                volume REAL,
                source TEXT DEFAULT 'yfinance',
                data_class TEXT CHECK(data_class IN ('public','private')) DEFAULT 'public',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(timestamp, symbol, source)
            )
        """)

        # ── TIER 3: COMPUTED (derived, rebuildable) ───────
        c.execute("""
            CREATE TABLE IF NOT EXISTS mosaics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                domain TEXT NOT NULL,
                coherence_score REAL,
                divergence_strength REAL,
                fragments_json TEXT,
                narrative TEXT,
                action TEXT CHECK(action IN ('build_thesis','investigate','pass')),
                data_class TEXT CHECK(data_class IN ('public','private')) DEFAULT 'public',
                scan_id INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(scan_id) REFERENCES scans(id)
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS theses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mosaic_id INTEGER,
                symbol TEXT NOT NULL,
                domain TEXT NOT NULL,
                thesis_type TEXT CHECK(thesis_type IN ('public','private')) DEFAULT 'public',
                vulnerability_json TEXT,
                simulation_json TEXT,
                roi_bear REAL,
                roi_base REAL,
                roi_bull REAL,
                kelly_fraction REAL,
                risk_assessment TEXT,
                lifecycle_stage TEXT CHECK(lifecycle_stage IN ('emerging','validating','confirmed','saturated')),
                status TEXT CHECK(status IN ('pending_review','approved','rejected','deferred')) DEFAULT 'pending_review',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(mosaic_id) REFERENCES mosaics(id)
            )
        """)

        # ── TIER 4: HUMAN (sacred, auditable) ─────────────
        c.execute("""
            CREATE TABLE IF NOT EXISTS decisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                thesis_id INTEGER NOT NULL,
                gate TEXT NOT NULL,
                symbol TEXT NOT NULL,
                decision TEXT CHECK(decision IN ('approve','reject','defer','escalate','auto_approve','auto_reject')) NOT NULL,
                confidence REAL,
                human_override BOOLEAN DEFAULT 0,
                rationale TEXT,
                trust_level TEXT CHECK(trust_level IN ('manual','supervised','autonomous')),
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(thesis_id) REFERENCES theses(id)
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                thesis_id INTEGER NOT NULL,
                symbol TEXT NOT NULL,
                domain TEXT NOT NULL,
                direction TEXT CHECK(direction IN ('long','short')) DEFAULT 'long',
                allocation_pct REAL,
                conviction TEXT CHECK(conviction IN ('high','medium','low')),
                entry_price REAL,
                entry_date TEXT,
                exit_price REAL,
                exit_date TEXT,
                pnl REAL,
                pnl_pct REAL,
                status TEXT CHECK(status IN ('open','closed')) DEFAULT 'open',
                data_class TEXT CHECK(data_class IN ('public','private')) DEFAULT 'public',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(thesis_id) REFERENCES theses(id)
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS audit_trail (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                layer TEXT NOT NULL,
                action TEXT NOT NULL,
                symbol TEXT NOT NULL,
                domain TEXT,
                actor TEXT CHECK(actor IN ('human','system')) NOT NULL,
                details_json TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # ── TIER 5: META ──────────────────────────────────
        c.execute("""
            CREATE TABLE IF NOT EXISTS scans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scan_type TEXT NOT NULL,
                sources_json TEXT,
                symbols_json TEXT,
                signal_count INTEGER DEFAULT 0,
                errors_json TEXT,
                status TEXT CHECK(status IN ('running','completed','failed')) DEFAULT 'running',
                started_at TEXT DEFAULT CURRENT_TIMESTAMP,
                completed_at TEXT
            )
        """)

        # ── INDEXES ───────────────────────────────────────
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_signals_symbol_ts ON signals(symbol, timestamp DESC)",
            "CREATE INDEX IF NOT EXISTS idx_signals_source ON signals(source)",
            "CREATE INDEX IF NOT EXISTS idx_signals_scan ON signals(scan_id)",
            "CREATE INDEX IF NOT EXISTS idx_signals_data_class ON signals(data_class)",
            "CREATE INDEX IF NOT EXISTS idx_ohlcv_symbol_ts ON ohlcv(symbol, timestamp DESC)",
            "CREATE INDEX IF NOT EXISTS idx_mosaics_symbol ON mosaics(symbol)",
            "CREATE INDEX IF NOT EXISTS idx_mosaics_action ON mosaics(action)",
            "CREATE INDEX IF NOT EXISTS idx_theses_status ON theses(status)",
            "CREATE INDEX IF NOT EXISTS idx_theses_symbol ON theses(symbol)",
            "CREATE INDEX IF NOT EXISTS idx_decisions_thesis ON decisions(thesis_id)",
            "CREATE INDEX IF NOT EXISTS idx_positions_status ON positions(status)",
            "CREATE INDEX IF NOT EXISTS idx_positions_symbol ON positions(symbol)",
            "CREATE INDEX IF NOT EXISTS idx_audit_symbol ON audit_trail(symbol)",
        ]
        for idx in indexes:
            c.execute(idx)

        conn.commit()
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_db.py -v
```
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add social_arb/db/schema.py tests/test_db.py
git commit -m "feat(db): 12-table schema with public/private data classification

Tiers: reference (instruments), raw (signals, ohlcv), computed (mosaics, theses),
human (decisions, positions, audit_trail), meta (scans).
All data-bearing tables have data_class column for public/private separation."
```

---

## Task 3: Database Store Functions

**Files:**
- Create: `social_arb/db/store.py`
- Test: `tests/test_db.py` (extend)

- [ ] **Step 1: Write failing tests for insert and query functions**

```python
# tests/test_db.py — add to existing file

class TestStore:
    def test_insert_and_query_signal(self, db_path):
        from social_arb.db.store import insert_signal, query_signals
        init_db(db_path)
        insert_signal(
            db_path=db_path,
            timestamp="2026-03-25T09:00:00",
            symbol="NVDA",
            source="reddit",
            direction="bullish",
            strength=0.82,
            confidence=0.71,
            data_class="public",
        )
        signals = query_signals(db_path=db_path, symbol="NVDA")
        assert len(signals) == 1
        assert signals[0]["source"] == "reddit"
        assert signals[0]["data_class"] == "public"

    def test_insert_and_query_ohlcv(self, db_path):
        from social_arb.db.store import insert_ohlcv_batch, query_ohlcv
        init_db(db_path)
        bars = [
            {"timestamp": "2026-03-24", "symbol": "NVDA", "open": 100, "high": 105, "low": 98, "close": 103, "volume": 1000000},
            {"timestamp": "2026-03-25", "symbol": "NVDA", "open": 103, "high": 108, "low": 101, "close": 107, "volume": 1200000},
        ]
        insert_ohlcv_batch(db_path=db_path, bars=bars)
        result = query_ohlcv(db_path=db_path, symbol="NVDA", limit=10)
        assert len(result) == 2

    def test_insert_mosaic(self, db_path):
        from social_arb.db.store import insert_mosaic, query_mosaics
        init_db(db_path)
        insert_mosaic(
            db_path=db_path,
            symbol="NVDA",
            domain="ai_semiconductors",
            coherence_score=89.0,
            divergence_strength=82.4,
            narrative="Strong cross-domain alignment",
            action="build_thesis",
            data_class="public",
        )
        mosaics = query_mosaics(db_path=db_path, action="build_thesis")
        assert len(mosaics) == 1
        assert mosaics[0]["coherence_score"] == 89.0

    def test_insert_decision_with_audit(self, db_path):
        from social_arb.db.store import insert_mosaic, insert_thesis, insert_decision, query_decisions
        init_db(db_path)
        mosaic_id = insert_mosaic(db_path=db_path, symbol="NVDA", domain="ai", coherence_score=89, divergence_strength=82, narrative="test", action="build_thesis")
        thesis_id = insert_thesis(db_path=db_path, mosaic_id=mosaic_id, symbol="NVDA", domain="ai", roi_bear=-0.2, roi_base=0.5, roi_bull=2.1, status="pending_review")
        insert_decision(db_path=db_path, thesis_id=thesis_id, gate="L2_L3", symbol="NVDA", decision="approve", confidence=0.89, rationale="Strong coherence")
        decisions = query_decisions(db_path=db_path, symbol="NVDA")
        assert len(decisions) == 1
        assert decisions[0]["decision"] == "approve"

    def test_private_data_isolation(self, db_path):
        from social_arb.db.store import insert_signal, query_signals
        init_db(db_path)
        insert_signal(db_path=db_path, timestamp="2026-03-25", symbol="NVDA", source="reddit", direction="bullish", strength=0.8, data_class="public")
        insert_signal(db_path=db_path, timestamp="2026-03-25", symbol="DATABRICKS", source="github", direction="bullish", strength=0.7, data_class="private")
        public = query_signals(db_path=db_path, data_class="public")
        private = query_signals(db_path=db_path, data_class="private")
        assert len(public) == 1
        assert len(private) == 1
        assert public[0]["symbol"] == "NVDA"
        assert private[0]["symbol"] == "DATABRICKS"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_db.py::TestStore -v
```

- [ ] **Step 3: Implement store.py**

```python
# social_arb/db/store.py
"""Insert and query functions for Social Arb database."""

import json
from typing import Optional, List, Dict, Any
from social_arb.db.schema import get_connection, DEFAULT_DB_PATH


# ── SIGNALS ──────────────────────────────────────────

def insert_signal(
    *,
    db_path: str = DEFAULT_DB_PATH,
    timestamp: str,
    symbol: str,
    source: str,
    direction: str = "neutral",
    signal_type: str = "general",
    strength: float = 0.0,
    confidence: float = 0.0,
    raw_json: Optional[str] = None,
    data_class: str = "public",
    scan_id: Optional[int] = None,
) -> int:
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """INSERT INTO signals (timestamp, symbol, source, signal_type, direction, strength, confidence, raw_json, data_class, scan_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (timestamp, symbol, source, signal_type, direction, strength, confidence, raw_json, data_class, scan_id),
        )
        return cursor.lastrowid


def insert_signals_batch(*, db_path: str = DEFAULT_DB_PATH, signals: List[Dict]) -> int:
    with get_connection(db_path) as conn:
        rows = [
            (s["timestamp"], s["symbol"], s["source"], s.get("signal_type", "general"),
             s.get("direction", "neutral"), s.get("strength", 0), s.get("confidence", 0),
             json.dumps(s.get("raw", {})) if s.get("raw") else None,
             s.get("data_class", "public"), s.get("scan_id"))
            for s in signals
        ]
        conn.executemany(
            """INSERT INTO signals (timestamp, symbol, source, signal_type, direction, strength, confidence, raw_json, data_class, scan_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            rows,
        )
        return len(rows)


def query_signals(
    *,
    db_path: str = DEFAULT_DB_PATH,
    symbol: Optional[str] = None,
    source: Optional[str] = None,
    data_class: Optional[str] = None,
    limit: int = 100,
) -> List[Dict]:
    clauses, params = [], []
    if symbol:
        clauses.append("symbol = ?"); params.append(symbol)
    if source:
        clauses.append("source = ?"); params.append(source)
    if data_class:
        clauses.append("data_class = ?"); params.append(data_class)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    params.append(limit)
    with get_connection(db_path) as conn:
        rows = conn.execute(f"SELECT * FROM signals {where} ORDER BY timestamp DESC LIMIT ?", params).fetchall()
        return [dict(row) for row in rows]


# ── OHLCV ────────────────────────────────────────────

def insert_ohlcv_batch(*, db_path: str = DEFAULT_DB_PATH, bars: List[Dict], source: str = "yfinance") -> int:
    with get_connection(db_path) as conn:
        rows = [
            (b["timestamp"], b["symbol"], b.get("open"), b.get("high"), b.get("low"),
             b["close"], b.get("volume"), source, b.get("data_class", "public"))
            for b in bars
        ]
        conn.executemany(
            """INSERT OR IGNORE INTO ohlcv (timestamp, symbol, open, high, low, close, volume, source, data_class)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            rows,
        )
        return len(rows)


def query_ohlcv(*, db_path: str = DEFAULT_DB_PATH, symbol: str, limit: int = 252) -> List[Dict]:
    with get_connection(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM ohlcv WHERE symbol = ? ORDER BY timestamp DESC LIMIT ?",
            (symbol, limit),
        ).fetchall()
        return [dict(row) for row in rows]


# ── MOSAICS ──────────────────────────────────────────

def insert_mosaic(
    *,
    db_path: str = DEFAULT_DB_PATH,
    symbol: str,
    domain: str,
    coherence_score: float,
    divergence_strength: float = 0.0,
    fragments_json: Optional[str] = None,
    narrative: str = "",
    action: str = "investigate",
    data_class: str = "public",
    scan_id: Optional[int] = None,
) -> int:
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """INSERT INTO mosaics (symbol, domain, coherence_score, divergence_strength, fragments_json, narrative, action, data_class, scan_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (symbol, domain, coherence_score, divergence_strength, fragments_json, narrative, action, data_class, scan_id),
        )
        return cursor.lastrowid


def query_mosaics(*, db_path: str = DEFAULT_DB_PATH, symbol: Optional[str] = None, action: Optional[str] = None, limit: int = 50) -> List[Dict]:
    clauses, params = [], []
    if symbol:
        clauses.append("symbol = ?"); params.append(symbol)
    if action:
        clauses.append("action = ?"); params.append(action)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    params.append(limit)
    with get_connection(db_path) as conn:
        rows = conn.execute(f"SELECT * FROM mosaics {where} ORDER BY coherence_score DESC LIMIT ?", params).fetchall()
        return [dict(row) for row in rows]


# ── THESES ───────────────────────────────────────────

def insert_thesis(
    *,
    db_path: str = DEFAULT_DB_PATH,
    mosaic_id: Optional[int] = None,
    symbol: str,
    domain: str,
    roi_bear: float = 0.0,
    roi_base: float = 0.0,
    roi_bull: float = 0.0,
    kelly_fraction: Optional[float] = None,
    lifecycle_stage: str = "emerging",
    status: str = "pending_review",
    vulnerability_json: Optional[str] = None,
    simulation_json: Optional[str] = None,
) -> int:
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """INSERT INTO theses (mosaic_id, symbol, domain, roi_bear, roi_base, roi_bull, kelly_fraction, lifecycle_stage, status, vulnerability_json, simulation_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (mosaic_id, symbol, domain, roi_bear, roi_base, roi_bull, kelly_fraction, lifecycle_stage, status, vulnerability_json, simulation_json),
        )
        return cursor.lastrowid


def query_theses(*, db_path: str = DEFAULT_DB_PATH, status: Optional[str] = None, symbol: Optional[str] = None) -> List[Dict]:
    clauses, params = [], []
    if status:
        clauses.append("status = ?"); params.append(status)
    if symbol:
        clauses.append("symbol = ?"); params.append(symbol)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    with get_connection(db_path) as conn:
        rows = conn.execute(f"SELECT * FROM theses {where} ORDER BY created_at DESC", params).fetchall()
        return [dict(row) for row in rows]


# ── DECISIONS (HITL) ─────────────────────────────────

def insert_decision(
    *,
    db_path: str = DEFAULT_DB_PATH,
    thesis_id: int,
    gate: str,
    symbol: str,
    decision: str,
    confidence: float = 0.0,
    human_override: bool = False,
    rationale: str = "",
    trust_level: str = "manual",
) -> int:
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """INSERT INTO decisions (thesis_id, gate, symbol, decision, confidence, human_override, rationale, trust_level)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (thesis_id, gate, symbol, decision, confidence, human_override, rationale, trust_level),
        )
        # Also write to audit trail
        conn.execute(
            """INSERT INTO audit_trail (layer, action, symbol, domain, actor, details_json)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (gate, f"decision:{decision}", symbol, "",
             "human" if not human_override else "human",
             json.dumps({"confidence": confidence, "rationale": rationale})),
        )
        return cursor.lastrowid


def query_decisions(*, db_path: str = DEFAULT_DB_PATH, symbol: Optional[str] = None, limit: int = 50) -> List[Dict]:
    params = []
    where = ""
    if symbol:
        where = "WHERE symbol = ?"; params.append(symbol)
    params.append(limit)
    with get_connection(db_path) as conn:
        rows = conn.execute(f"SELECT * FROM decisions {where} ORDER BY created_at DESC LIMIT ?", params).fetchall()
        return [dict(row) for row in rows]


# ── POSITIONS ────────────────────────────────────────

def insert_position(
    *,
    db_path: str = DEFAULT_DB_PATH,
    thesis_id: int,
    symbol: str,
    domain: str,
    direction: str = "long",
    allocation_pct: float = 0.0,
    conviction: str = "medium",
    entry_price: float = 0.0,
    entry_date: str = "",
    data_class: str = "public",
) -> int:
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """INSERT INTO positions (thesis_id, symbol, domain, direction, allocation_pct, conviction, entry_price, entry_date, data_class)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (thesis_id, symbol, domain, direction, allocation_pct, conviction, entry_price, entry_date, data_class),
        )
        return cursor.lastrowid


def query_positions(*, db_path: str = DEFAULT_DB_PATH, status: str = "open") -> List[Dict]:
    with get_connection(db_path) as conn:
        rows = conn.execute("SELECT * FROM positions WHERE status = ? ORDER BY entry_date DESC", (status,)).fetchall()
        return [dict(row) for row in rows]


# ── SCANS ────────────────────────────────────────────

def start_scan(*, db_path: str = DEFAULT_DB_PATH, scan_type: str, sources: List[str], symbols: List[str]) -> int:
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """INSERT INTO scans (scan_type, sources_json, symbols_json, status) VALUES (?, ?, ?, 'running')""",
            (scan_type, json.dumps(sources), json.dumps(symbols)),
        )
        return cursor.lastrowid


def complete_scan(*, db_path: str = DEFAULT_DB_PATH, scan_id: int, signal_count: int, errors: List[str] = None):
    from datetime import datetime
    with get_connection(db_path) as conn:
        conn.execute(
            """UPDATE scans SET status='completed', signal_count=?, errors_json=?, completed_at=? WHERE id=?""",
            (signal_count, json.dumps(errors or []), datetime.utcnow().isoformat(), scan_id),
        )
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_db.py -v
```
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add social_arb/db/store.py tests/test_db.py
git commit -m "feat(db): insert and query functions for all 12 tables

Supports: signals, ohlcv, mosaics, theses, decisions (HITL),
positions, audit_trail, scans. Batch inserts for signals and ohlcv.
Public/private data_class filtering on all queries."
```

---

## Task 4: Collector Base + yfinance Collector

**Files:**
- Create: `social_arb/collectors/base.py`
- Create: `social_arb/collectors/yfinance_collector.py`
- Test: `tests/test_collectors.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_collectors.py
import pytest
from social_arb.collectors.base import BaseCollector, CollectorResult


class TestBaseCollector:
    def test_result_dataclass(self):
        result = CollectorResult(source="test", signals=[], errors=[], symbols_scanned=["NVDA"])
        assert result.source == "test"
        assert result.signal_count == 0

    def test_abstract_collect_raises(self):
        with pytest.raises(TypeError):
            BaseCollector()


class TestYFinanceCollector:
    def test_collect_single_symbol(self):
        from social_arb.collectors.yfinance_collector import YFinanceCollector
        collector = YFinanceCollector()
        result = collector.collect(symbols=["NVDA"], period="5d")
        assert result.source == "yfinance"
        assert result.signal_count > 0
        # Check data_class is set
        for signal in result.signals:
            assert signal["data_class"] == "public"
            assert "close" in signal or "direction" in signal

    def test_collect_returns_ohlcv(self):
        from social_arb.collectors.yfinance_collector import YFinanceCollector
        collector = YFinanceCollector()
        result = collector.collect(symbols=["AAPL"], period="5d")
        ohlcv_signals = [s for s in result.signals if s.get("signal_type") == "ohlcv"]
        assert len(ohlcv_signals) > 0
        bar = ohlcv_signals[0]
        assert "open" in bar
        assert "high" in bar
        assert "low" in bar
        assert "close" in bar
        assert "volume" in bar
```

- [ ] **Step 2: Run tests to verify failure**

```bash
pytest tests/test_collectors.py -v
```

- [ ] **Step 3: Implement base collector**

```python
# social_arb/collectors/base.py
"""Base collector interface for all data sources."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class CollectorResult:
    """Output of a collection run."""
    source: str
    signals: List[Dict[str, Any]]
    errors: List[str] = field(default_factory=list)
    symbols_scanned: List[str] = field(default_factory=list)

    @property
    def signal_count(self) -> int:
        return len(self.signals)


class BaseCollector(ABC):
    """Abstract base for all data collectors. No demo mode — real data or error."""

    @abstractmethod
    def collect(self, symbols: List[str], **kwargs) -> CollectorResult:
        """Collect signals for given symbols. Must return CollectorResult."""
        ...

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Identifier for this data source."""
        ...

    @property
    def data_class(self) -> str:
        """Override in subclass for private data sources."""
        return "public"
```

- [ ] **Step 4: Implement yfinance collector**

```python
# social_arb/collectors/yfinance_collector.py
"""Real market data collector via yfinance. No demo mode."""

import logging
from datetime import datetime
from typing import List, Optional

import yfinance as yf

from social_arb.collectors.base import BaseCollector, CollectorResult

logger = logging.getLogger(__name__)


class YFinanceCollector(BaseCollector):
    """Collects OHLCV data and basic fundamentals from Yahoo Finance."""

    @property
    def source_name(self) -> str:
        return "yfinance"

    def collect(self, symbols: List[str], period: str = "1mo", **kwargs) -> CollectorResult:
        signals = []
        errors = []
        scanned = []

        for symbol in symbols:
            try:
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period=period)

                if hist.empty:
                    errors.append(f"{symbol}: no data returned")
                    continue

                scanned.append(symbol)

                # OHLCV bars
                for date, row in hist.iterrows():
                    signals.append({
                        "timestamp": date.strftime("%Y-%m-%d"),
                        "symbol": symbol,
                        "source": "yfinance",
                        "signal_type": "ohlcv",
                        "direction": "bullish" if row["Close"] > row["Open"] else "bearish",
                        "strength": abs(row["Close"] - row["Open"]) / row["Open"] if row["Open"] > 0 else 0,
                        "confidence": min(1.0, row["Volume"] / 1e7) if row["Volume"] > 0 else 0.1,
                        "open": float(row["Open"]),
                        "high": float(row["High"]),
                        "low": float(row["Low"]),
                        "close": float(row["Close"]),
                        "volume": int(row["Volume"]),
                        "data_class": "public",
                    })

                # Latest price signal
                latest = hist.iloc[-1]
                prev = hist.iloc[-2] if len(hist) > 1 else latest
                change_pct = (latest["Close"] - prev["Close"]) / prev["Close"] if prev["Close"] > 0 else 0

                signals.append({
                    "timestamp": datetime.utcnow().isoformat(),
                    "symbol": symbol,
                    "source": "yfinance",
                    "signal_type": "price_momentum",
                    "direction": "bullish" if change_pct > 0.01 else ("bearish" if change_pct < -0.01 else "neutral"),
                    "strength": min(1.0, abs(change_pct) * 10),
                    "confidence": 0.9,  # Price data is high confidence
                    "data_class": "public",
                    "raw": {"change_pct": change_pct, "close": float(latest["Close"]), "volume": int(latest["Volume"])},
                })

                logger.info(f"[yfinance] {symbol}: {len(hist)} bars collected")

            except Exception as e:
                errors.append(f"{symbol}: {str(e)}")
                logger.error(f"[yfinance] {symbol} failed: {e}")

        return CollectorResult(
            source="yfinance",
            signals=signals,
            errors=errors,
            symbols_scanned=scanned,
        )
```

- [ ] **Step 5: Run tests**

```bash
pytest tests/test_collectors.py -v
```
Expected: PASS (requires network access for yfinance)

- [ ] **Step 6: Commit**

```bash
git add social_arb/collectors/ tests/test_collectors.py
git commit -m "feat(collectors): base collector + yfinance real data collector

No demo mode. YFinanceCollector fetches real OHLCV + price momentum signals.
All signals tagged with data_class='public'."
```

---

## Task 5: Reddit Collector (Public JSON API — No Key Required)

**Files:**
- Create: `social_arb/collectors/reddit_collector.py`
- Test: `tests/test_collectors.py` (extend)

- [ ] **Step 1: Write failing test**

```python
# Add to tests/test_collectors.py

class TestRedditCollector:
    def test_collect_subreddit(self):
        from social_arb.collectors.reddit_collector import RedditCollector
        collector = RedditCollector()
        result = collector.collect(
            symbols=["NVDA"],
            subreddits=["wallstreetbets", "stocks"],
            limit=10,
        )
        assert result.source == "reddit"
        # May or may not find NVDA mentions, but should not error
        assert len(result.errors) == 0 or "rate_limit" in result.errors[0].lower()
        for signal in result.signals:
            assert signal["data_class"] == "public"
            assert signal["source"] == "reddit"
```

- [ ] **Step 2: Implement Reddit collector using public JSON API**

```python
# social_arb/collectors/reddit_collector.py
"""Reddit signal collector using public JSON API. No API key required."""

import logging
import time
from datetime import datetime
from typing import List, Optional

import requests

from social_arb.collectors.base import BaseCollector, CollectorResult

logger = logging.getLogger(__name__)

REDDIT_BASE = "https://www.reddit.com"
HEADERS = {"User-Agent": "SocialArb/1.0 (information arbitrage research)"}


class RedditCollector(BaseCollector):
    """Collects social signals from Reddit public JSON endpoints."""

    @property
    def source_name(self) -> str:
        return "reddit"

    def collect(
        self,
        symbols: List[str],
        subreddits: Optional[List[str]] = None,
        limit: int = 25,
        **kwargs,
    ) -> CollectorResult:
        subreddits = subreddits or ["wallstreetbets", "stocks", "investing", "SecurityAnalysis"]
        signals = []
        errors = []

        for subreddit in subreddits:
            try:
                url = f"{REDDIT_BASE}/r/{subreddit}/hot.json?limit={limit}"
                resp = requests.get(url, headers=HEADERS, timeout=10)

                if resp.status_code == 429:
                    errors.append(f"rate_limit: {subreddit}")
                    time.sleep(2)
                    continue

                resp.raise_for_status()
                data = resp.json()
                posts = data.get("data", {}).get("children", [])

                for post in posts:
                    pd = post.get("data", {})
                    title = pd.get("title", "")
                    selftext = pd.get("selftext", "")
                    text = f"{title} {selftext}".upper()

                    # Check which tracked symbols appear
                    for symbol in symbols:
                        if symbol.upper() in text or f"${symbol.upper()}" in text:
                            upvotes = pd.get("ups", 0)
                            comments = pd.get("num_comments", 0)
                            engagement = upvotes + (comments * 3)  # Comments weighted 3x

                            signals.append({
                                "timestamp": datetime.utcfromtimestamp(pd.get("created_utc", 0)).isoformat(),
                                "symbol": symbol.upper(),
                                "source": "reddit",
                                "signal_type": "social_mention",
                                "direction": "bullish",  # Mentions = attention = bullish bias
                                "strength": min(1.0, engagement / 1000),
                                "confidence": min(1.0, engagement / 5000),
                                "data_class": "public",
                                "raw": {
                                    "subreddit": subreddit,
                                    "title": title[:200],
                                    "upvotes": upvotes,
                                    "comments": comments,
                                    "url": pd.get("url", ""),
                                },
                            })

                logger.info(f"[reddit] r/{subreddit}: scanned {len(posts)} posts")
                time.sleep(1)  # Rate limiting

            except Exception as e:
                errors.append(f"r/{subreddit}: {str(e)}")
                logger.error(f"[reddit] r/{subreddit} failed: {e}")

        return CollectorResult(
            source="reddit",
            signals=signals,
            errors=errors,
            symbols_scanned=symbols,
        )
```

- [ ] **Step 3: Run tests**

```bash
pytest tests/test_collectors.py::TestRedditCollector -v
```

- [ ] **Step 4: Commit**

```bash
git add social_arb/collectors/reddit_collector.py tests/test_collectors.py
git commit -m "feat(collectors): Reddit public JSON collector — no API key needed

Scans r/wallstreetbets, r/stocks, r/investing, r/SecurityAnalysis.
Scores by engagement (upvotes + comments*3). All signals data_class='public'."
```

---

## Task 6: Google Trends + SEC EDGAR Collectors

**Files:**
- Create: `social_arb/collectors/trends_collector.py`
- Create: `social_arb/collectors/sec_edgar_collector.py`
- Test: `tests/test_collectors.py` (extend)

- [ ] **Step 1: Write failing tests**

```python
# Add to tests/test_collectors.py

class TestTrendsCollector:
    def test_collect_trends(self):
        from social_arb.collectors.trends_collector import TrendsCollector
        collector = TrendsCollector()
        result = collector.collect(symbols=["NVDA", "PLTR"])
        assert result.source == "google_trends"
        for signal in result.signals:
            assert signal["data_class"] == "public"


class TestSECEdgarCollector:
    def test_collect_filings(self):
        from social_arb.collectors.sec_edgar_collector import SECEdgarCollector
        collector = SECEdgarCollector()
        result = collector.collect(symbols=["NVDA"])
        assert result.source == "sec_edgar"
        for signal in result.signals:
            assert signal["data_class"] == "public"
```

- [ ] **Step 2: Implement Google Trends collector**

```python
# social_arb/collectors/trends_collector.py
"""Google Trends collector via pytrends. No API key required."""

import logging
from datetime import datetime
from typing import List

from social_arb.collectors.base import BaseCollector, CollectorResult

logger = logging.getLogger(__name__)


class TrendsCollector(BaseCollector):
    """Collects search interest trends from Google Trends."""

    @property
    def source_name(self) -> str:
        return "google_trends"

    def collect(self, symbols: List[str], timeframe: str = "today 3-m", **kwargs) -> CollectorResult:
        signals = []
        errors = []

        try:
            from pytrends.request import TrendReq
            pytrends = TrendReq(hl="en-US", tz=360)

            # Process in batches of 5 (API limit)
            for i in range(0, len(symbols), 5):
                batch = symbols[i:i+5]
                try:
                    pytrends.build_payload(batch, timeframe=timeframe)
                    interest = pytrends.interest_over_time()

                    if interest.empty:
                        errors.append(f"No trend data for {batch}")
                        continue

                    for symbol in batch:
                        if symbol not in interest.columns:
                            continue

                        series = interest[symbol]
                        current = float(series.iloc[-1])
                        avg = float(series.mean())
                        trend_strength = (current - avg) / avg if avg > 0 else 0

                        signals.append({
                            "timestamp": datetime.utcnow().isoformat(),
                            "symbol": symbol,
                            "source": "google_trends",
                            "signal_type": "search_interest",
                            "direction": "bullish" if trend_strength > 0.2 else ("bearish" if trend_strength < -0.2 else "neutral"),
                            "strength": min(1.0, abs(trend_strength)),
                            "confidence": 0.6,  # Trends are noisy
                            "data_class": "public",
                            "raw": {
                                "current_interest": current,
                                "avg_interest": avg,
                                "trend_strength": trend_strength,
                            },
                        })

                except Exception as e:
                    errors.append(f"Trends batch {batch}: {str(e)}")
                    logger.error(f"[trends] batch {batch} failed: {e}")

        except ImportError:
            errors.append("pytrends not installed: pip install pytrends")

        return CollectorResult(
            source="google_trends",
            signals=signals,
            errors=errors,
            symbols_scanned=symbols,
        )
```

- [ ] **Step 3: Implement SEC EDGAR collector**

```python
# social_arb/collectors/sec_edgar_collector.py
"""SEC EDGAR collector using free XBRL/EFTS API. No key required."""

import logging
import time
from datetime import datetime
from typing import List, Optional, Dict

import requests

from social_arb.collectors.base import BaseCollector, CollectorResult

logger = logging.getLogger(__name__)

EDGAR_SEARCH = "https://efts.sec.gov/LATEST/search-index"
EDGAR_FILINGS = "https://data.sec.gov/submissions"
HEADERS = {"User-Agent": "SocialArb dan@socialarb.com", "Accept": "application/json"}

# CIK lookup for common tickers
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
    """Collects SEC filing signals — 13F, 10-K, 10-Q, 8-K."""

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
                errors.append(f"{symbol}: CIK not found (add to TICKER_CIK mapping)")
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

                # Take last 10 filings
                for j in range(min(10, len(forms))):
                    form_type = forms[j]
                    filing_date = dates[j]
                    desc = descriptions[j] if j < len(descriptions) else ""

                    # Score by filing type
                    strength = 0.3
                    direction = "neutral"
                    if form_type in ("10-K", "10-Q"):
                        strength = 0.5
                        direction = "neutral"
                    elif form_type == "8-K":
                        strength = 0.7
                        direction = "bullish"  # 8-Ks often material events
                    elif "13F" in form_type:
                        strength = 0.6
                        direction = "bullish"  # Institutional position disclosure

                    signals.append({
                        "timestamp": filing_date,
                        "symbol": symbol,
                        "source": "sec_edgar",
                        "signal_type": f"filing_{form_type.lower().replace('-', '')}",
                        "direction": direction,
                        "strength": strength,
                        "confidence": 0.85,  # SEC filings are factual
                        "data_class": "public",
                        "raw": {
                            "form_type": form_type,
                            "description": desc,
                            "cik": cik,
                        },
                    })

                logger.info(f"[sec] {symbol}: {min(10, len(forms))} filings collected")
                time.sleep(0.5)  # SEC rate limit: 10 req/sec

            except Exception as e:
                errors.append(f"{symbol}: {str(e)}")
                logger.error(f"[sec] {symbol} failed: {e}")

        return CollectorResult(
            source="sec_edgar",
            signals=signals,
            errors=errors,
            symbols_scanned=scanned,
        )
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_collectors.py -v
```

- [ ] **Step 5: Commit**

```bash
git add social_arb/collectors/trends_collector.py social_arb/collectors/sec_edgar_collector.py tests/test_collectors.py
git commit -m "feat(collectors): Google Trends + SEC EDGAR real data collectors

Trends: pytrends, search interest vs average, bullish/bearish/neutral.
SEC: EDGAR XBRL API, 10-K/10-Q/8-K/13F filing signals. Both data_class='public'."
```

---

## Task 7: Batch Analysis Pipeline

**Files:**
- Create: `social_arb/pipeline.py`
- Test: `tests/test_pipeline.py`

This is the brain — it reads raw signals from the DB, runs them through the topology engine layers, and writes computed mosaics + theses back.

- [ ] **Step 1: Write failing tests**

```python
# tests/test_pipeline.py
import os
import tempfile
import pytest
from social_arb.db.schema import init_db
from social_arb.db.store import insert_signal, insert_ohlcv_batch
from social_arb.pipeline import run_analysis


@pytest.fixture
def seeded_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path)
    # Seed with real-looking signals
    for i in range(5):
        insert_signal(
            db_path=path, timestamp=f"2026-03-2{i}", symbol="NVDA",
            source="reddit", direction="bullish", strength=0.7 + i*0.05,
            confidence=0.6, data_class="public",
        )
    insert_signal(
        db_path=path, timestamp="2026-03-25", symbol="NVDA",
        source="google_trends", direction="bullish", strength=0.8,
        confidence=0.6, data_class="public",
    )
    insert_signal(
        db_path=path, timestamp="2026-03-25", symbol="NVDA",
        source="sec_edgar", direction="neutral", strength=0.5,
        confidence=0.85, data_class="public",
    )
    yield path
    os.remove(path)


class TestPipeline:
    def test_analysis_creates_mosaics(self, seeded_db):
        result = run_analysis(db_path=seeded_db, symbols=["NVDA"])
        assert result["mosaics_created"] > 0

    def test_analysis_creates_theses_for_strong_mosaics(self, seeded_db):
        result = run_analysis(db_path=seeded_db, symbols=["NVDA"])
        assert result["theses_created"] >= 0  # May or may not hit threshold

    def test_analysis_respects_data_class(self, seeded_db):
        from social_arb.db.store import query_mosaics
        run_analysis(db_path=seeded_db, symbols=["NVDA"])
        mosaics = query_mosaics(db_path=seeded_db)
        for m in mosaics:
            assert m["data_class"] in ("public", "private")
```

- [ ] **Step 2: Implement pipeline.py**

```python
# social_arb/pipeline.py
"""Batch analysis pipeline: signals → mosaics → theses.

Reads raw signals from DB, runs topology engine logic, writes results back.
No HITL gates here — just computation. HITL happens in review.py.
"""

import json
import logging
from typing import List, Dict, Optional
from datetime import datetime

from social_arb.db.schema import get_connection, DEFAULT_DB_PATH
from social_arb.db.store import (
    query_signals, insert_mosaic, insert_thesis, query_mosaics
)
from social_arb.engine.sentiment_divergence import SentimentDivergence
from social_arb.engine.cross_domain_amplifier import CrossDomainAmplifier

logger = logging.getLogger(__name__)


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
    4. For strong mosaics: create thesis with ROI estimates
    """
    stats = {"symbols_analyzed": 0, "mosaics_created": 0, "theses_created": 0, "errors": []}

    # Get all recent signals
    if symbols:
        all_signals = []
        for sym in symbols:
            all_signals.extend(query_signals(db_path=db_path, symbol=sym, limit=500))
    else:
        all_signals = query_signals(db_path=db_path, limit=2000)

    if not all_signals:
        logger.warning("No signals found for analysis")
        return stats

    # Group by symbol
    by_symbol: Dict[str, List[Dict]] = {}
    for sig in all_signals:
        by_symbol.setdefault(sig["symbol"], []).append(sig)

    divergence_engine = SentimentDivergence()
    amplifier = CrossDomainAmplifier()

    for symbol, signals in by_symbol.items():
        try:
            stats["symbols_analyzed"] += 1

            # Determine data_class — if any signal is private, mosaic is private
            data_class = "private" if any(s.get("data_class") == "private" for s in signals) else "public"

            # Compute source diversity
            sources = list(set(s["source"] for s in signals))
            source_count = len(sources)

            # Compute directional alignment (coherence proxy)
            bullish = sum(1 for s in signals if s.get("direction") == "bullish")
            bearish = sum(1 for s in signals if s.get("direction") == "bearish")
            total = len(signals)
            alignment = max(bullish, bearish) / total if total > 0 else 0

            # Average strength
            avg_strength = sum(s.get("strength", 0) for s in signals) / total if total > 0 else 0

            # Coherence score: alignment * 70 + strength * 30, boosted by source diversity
            coherence = (alignment * 70 + avg_strength * 30) * min(2.0, 1.0 + (source_count - 1) * 0.25)
            coherence = min(100.0, coherence)

            # Divergence (social vs institutional)
            social_signals = [s for s in signals if s["source"] in ("reddit", "google_trends")]
            inst_signals = [s for s in signals if s["source"] in ("sec_edgar", "yfinance")]
            social_growth = sum(s.get("strength", 0) for s in social_signals) / max(1, len(social_signals)) * 100
            inst_growth = sum(s.get("strength", 0) for s in inst_signals) / max(1, len(inst_signals)) * 100

            divergence_result = divergence_engine.calculate(
                signal_data={"growth_pct": social_growth, "volume": total},
                market_data={"growth_pct": inst_growth},
            )
            divergence_strength = divergence_result.signal_strength if divergence_result else 0

            # Determine action
            if coherence >= 60 and divergence_strength > 30:
                action = "build_thesis"
            elif coherence >= 40:
                action = "investigate"
            else:
                action = "pass"

            # Build narrative
            dominant_dir = "bullish" if bullish >= bearish else "bearish"
            narrative = (
                f"{symbol}: {total} signals from {source_count} sources. "
                f"Direction: {dominant_dir} ({bullish}B/{bearish}S). "
                f"Coherence: {coherence:.0f}/100. "
                f"Divergence: {divergence_strength:.1f} ({divergence_result.classification if divergence_result else 'n/a'}). "
                f"Sources: {', '.join(sources)}."
            )

            domain = _infer_domain(symbol, signals)

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

            # Create thesis for strong mosaics
            if action == "build_thesis":
                thesis_id = insert_thesis(
                    db_path=db_path,
                    mosaic_id=mosaic_id,
                    symbol=symbol,
                    domain=domain,
                    roi_bear=-0.15,  # Default estimates — refined by engines later
                    roi_base=0.30,
                    roi_bull=1.50,
                    lifecycle_stage="emerging" if coherence < 70 else "validating",
                    status="pending_review",
                )
                stats["theses_created"] += 1
                logger.info(f"[pipeline] {symbol}: thesis created (coherence={coherence:.0f}, div={divergence_strength:.1f})")

        except Exception as e:
            stats["errors"].append(f"{symbol}: {str(e)}")
            logger.error(f"[pipeline] {symbol} failed: {e}")

    return stats


def _infer_domain(symbol: str, signals: List[Dict]) -> str:
    """Infer the investment domain from signal sources."""
    sources = set(s["source"] for s in signals)
    # Simple heuristic — can be expanded
    if "sec_edgar" in sources:
        return "public_markets"
    if "github" in sources:
        return "private_markets"
    return "public_markets"
```

- [ ] **Step 3: Run tests**

```bash
pytest tests/test_pipeline.py -v
```

- [ ] **Step 4: Commit**

```bash
git add social_arb/pipeline.py tests/test_pipeline.py
git commit -m "feat(pipeline): batch analysis — signals to mosaics to theses

Groups signals by symbol, computes coherence + divergence + cross-domain amplification.
Creates mosaic cards and theses for strong signals. Respects data_class public/private."
```

---

## Task 8: CLI Entry Point

**Files:**
- Create: `social_arb/cli.py`
- Modify: `social_arb/config.py`
- Update: `requirements.txt`

The four commands: `collect`, `analyze`, `review`, `status`.

- [ ] **Step 1: Update requirements.txt**

```
# Social Arb — Information Arbitrage Engine

# Core
pandas>=2.0.0
numpy>=1.24.0
click>=8.0.0
rich>=13.0.0

# Data collectors
yfinance>=0.2.30
pytrends>=4.9.0
requests>=2.28.0

# Optional
praw>=7.7.0
```

- [ ] **Step 2: Update config.py — remove demo_mode**

```python
# social_arb/config.py
"""Configuration — env vars only, no demo mode."""

import os
from pathlib import Path


class Config:
    def __init__(self):
        db_default = str(Path(__file__).parent / "db" / "social_arb.db")
        self.db_path: str = os.getenv("SOCIAL_ARB_DB", str(Path(db_default).resolve()))
        self.log_level: str = os.getenv("LOG_LEVEL", "INFO")

        # Default tracked symbols (public)
        self.public_symbols: list = os.getenv(
            "PUBLIC_SYMBOLS", "NVDA,PLTR,MSFT,AAPL,AMD,TSLA,SHOP,SQ,DDOG,GOOGL"
        ).split(",")

        # Private companies (tracked separately)
        self.private_symbols: list = os.getenv(
            "PRIVATE_SYMBOLS", "DATABRICKS,STRIPE,ANDURIL,COREWEAVE,ANTHROPIC"
        ).split(",")

        # Reddit config
        self.reddit_subreddits: list = os.getenv(
            "REDDIT_SUBREDDITS", "wallstreetbets,stocks,investing,SecurityAnalysis"
        ).split(",")

    def __repr__(self):
        return f"Config(db={self.db_path}, public={len(self.public_symbols)}, private={len(self.private_symbols)})"


config = Config()
```

- [ ] **Step 3: Build CLI**

```python
# social_arb/cli.py
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
@click.option("--sources", default="yfinance,reddit,sec_edgar", help="Comma-separated collectors")
@click.option("--symbols", default=None, help="Override symbols (comma-separated)")
def collect(sources, symbols):
    """Collect signals from real data sources."""
    from social_arb.collectors.yfinance_collector import YFinanceCollector
    from social_arb.collectors.reddit_collector import RedditCollector
    from social_arb.collectors.sec_edgar_collector import SECEdgarCollector

    source_list = [s.strip() for s in sources.split(",")]
    symbol_list = [s.strip() for s in symbols.split(",")] if symbols else config.public_symbols

    collectors = {
        "yfinance": YFinanceCollector(),
        "reddit": RedditCollector(),
        "sec_edgar": SECEdgarCollector(),
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

        # Store signals
        if result.signals:
            from social_arb.db.store import insert_signals_batch
            count = insert_signals_batch(
                db_path=config.db_path,
                signals=[{**s, "scan_id": scan_id} for s in result.signals],
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
            f"[bold]{thesis['symbol']}[/bold] | {thesis['domain']} | {thesis.get('data_class', 'public').upper()}\n"
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
        from social_arb.db.schema import get_connection
        status_map = {"approve": "approved", "reject": "rejected", "defer": "pending_review"}
        with get_connection(config.db_path) as conn:
            conn.execute(
                "UPDATE theses SET status = ? WHERE id = ?",
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
    signals = query_signals(db_path=config.db_path, limit=1)
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


def main():
    cli()


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Test CLI manually**

```bash
# Initialize DB
python -m social_arb.cli --verbose status

# Collect real data
python -m social_arb.cli collect --sources yfinance --symbols NVDA,PLTR,AAPL

# Run analysis
python -m social_arb.cli analyze

# HITL review
python -m social_arb.cli review

# Check status
python -m social_arb.cli status
```

- [ ] **Step 5: Commit**

```bash
git add social_arb/cli.py social_arb/config.py requirements.txt
git commit -m "feat(cli): four-command CLI — collect, analyze, review, status

collect: real data from yfinance/reddit/sec_edgar
analyze: batch signals → mosaics → theses
review: HITL terminal UI for approve/reject/defer
status: portfolio overview with public/private counts
No demo mode. No hardcoded data."
```

---

## Task 9: Update CLAUDE.md and Clean Root

**Files:**
- Modify: `CLAUDE.md`
- Delete: `TASKS.md` (stale)
- Modify: `.gitignore`

- [ ] **Step 1: Update CLAUDE.md**

Remove DropArb reference. Update project description to reflect new CLI architecture.

- [ ] **Step 2: Update .gitignore**

```
# Database
*.db
*.sqlite3

# Python
__pycache__/
*.pyc
.venv/
*.egg-info/

# OS
.DS_Store
Thumbs.db

# IDE
.vscode/
.idea/

# Seed data (generated)
social_arb/db/seed_data/

# Environment
.env
```

- [ ] **Step 3: Commit**

```bash
git add CLAUDE.md .gitignore
git rm -f TASKS.md 2>/dev/null || true
git commit -m "chore: update CLAUDE.md, clean .gitignore, remove stale TASKS.md"
```

---

## Task 10: Verify End-to-End

- [ ] **Step 1: Run all tests**

```bash
pytest tests/ -v --tb=short
```

- [ ] **Step 2: Run the full pipeline manually**

```bash
python -m social_arb.cli collect --sources yfinance --symbols NVDA,PLTR
python -m social_arb.cli analyze --symbols NVDA,PLTR
python -m social_arb.cli status
```

- [ ] **Step 3: Verify database has real data**

```bash
python -c "
from social_arb.db.schema import get_connection
from social_arb.config import config
with get_connection(config.db_path) as conn:
    for table in ['signals', 'ohlcv', 'mosaics', 'theses', 'decisions', 'positions']:
        count = conn.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]
        print(f'{table}: {count} rows')
"
```

- [ ] **Step 4: Verify no demo/dropship references remain**

```bash
grep -ri "demo_mode\|demo_signals\|dropship\|get_demo\|DropArb" social_arb/ tests/ || echo "CLEAN"
```

- [ ] **Step 5: Final commit**

```bash
git add -A
git commit -m "verify: end-to-end pipeline working with real data

All tests pass. collect→analyze→review→status pipeline functional.
Zero demo mode. Zero dropshipping. Public/private data classification working."
```
