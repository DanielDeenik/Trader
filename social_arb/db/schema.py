"""
Social Arb — Database Schema (12 tables)

Tiers:
  1. Reference: instruments (what we track)
  2. Raw: signals, ohlcv (immutable, append-only, timestamped)
  3. Computed: mosaics, theses (derived from raw, rebuildable)
  4. Human: decisions, positions (HITL sacred audit trail)
  5. Meta: scans (collection tracking)

Every table with data_class supports public/private classification.

Supports both SQLite (local dev) and PostgreSQL (Cloud SQL production):
- Uses .adapter module to detect DATABASE_URL env var
- Automatically generates compatible DDL for each backend
"""

from .adapter import get_connection, get_db_backend, DEFAULT_DB_PATH


def init_db(db_path: str = DEFAULT_DB_PATH) -> None:
    """Initialize database schema. Generates backend-specific DDL."""
    backend = get_db_backend()
    with get_connection(db_path) as conn:
        c = conn.cursor()

        # Generate backend-specific DDL
        if backend == "postgres":
            _init_db_postgres(c, conn)
        else:
            _init_db_sqlite(c, conn)


def _init_db_sqlite(c, conn) -> None:
    """SQLite schema with AUTOINCREMENT and TEXT timestamps."""
    # TIER 1: REFERENCE
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

    # TIER 2: RAW (append-only, immutable)
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

    # TIER 3: COMPUTED (derived, rebuildable)
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

    # TIER 4: HUMAN (sacred, auditable)
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
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            gate TEXT NOT NULL,
            symbol TEXT NOT NULL,
            entity_id INTEGER,
            entity_type TEXT CHECK(entity_type IN ('signal_cluster','mosaic','thesis','position')),
            scores_json TEXT,
            total_score REAL,
            threshold REAL DEFAULT 12.0,
            narrative TEXT,
            dominant_narrative TEXT,
            market_pricing TEXT,
            invalidation TEXT,
            decision TEXT CHECK(decision IN ('promote','watch','discard','forge','hold','reject','execute','defer')) NOT NULL,
            position_size TEXT,
            risk_note TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
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

    # TIER 5: META
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

    c.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_type TEXT NOT NULL,
            status TEXT CHECK(status IN ('pending','running','completed','failed','cancelled')) DEFAULT 'pending',
            params_json TEXT,
            result_json TEXT,
            error TEXT,
            attempts INTEGER DEFAULT 0,
            max_attempts INTEGER DEFAULT 3,
            next_retry_at TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            started_at TEXT,
            completed_at TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS stepps_scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            signal_id INTEGER NOT NULL,
            social_currency REAL,
            triggers REAL,
            emotion REAL,
            public_visibility REAL,
            practical_value REAL,
            stories REAL,
            composite REAL,
            scored_by TEXT CHECK(scored_by IN ('llm','classifier','human')) DEFAULT 'classifier',
            model_version TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(signal_id) REFERENCES signals(id),
            UNIQUE(signal_id, scored_by)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS stepps_training (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            signal_id INTEGER NOT NULL,
            social_currency REAL,
            triggers REAL,
            emotion REAL,
            public_visibility REAL,
            practical_value REAL,
            stories REAL,
            source TEXT CHECK(source IN ('llm_seed','human_correction')) DEFAULT 'human_correction',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(signal_id) REFERENCES signals(id)
        )
    """)

    # INDEXES
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
        "CREATE INDEX IF NOT EXISTS idx_reviews_gate ON reviews(gate)",
        "CREATE INDEX IF NOT EXISTS idx_reviews_symbol ON reviews(symbol)",
        "CREATE INDEX IF NOT EXISTS idx_reviews_decision ON reviews(decision)",
        "CREATE INDEX IF NOT EXISTS idx_positions_status ON positions(status)",
        "CREATE INDEX IF NOT EXISTS idx_positions_symbol ON positions(symbol)",
        "CREATE INDEX IF NOT EXISTS idx_audit_symbol ON audit_trail(symbol)",
        "CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)",
        "CREATE INDEX IF NOT EXISTS idx_tasks_status_created ON tasks(status, created_at)",
        "CREATE INDEX IF NOT EXISTS idx_tasks_next_retry ON tasks(next_retry_at)",
        "CREATE INDEX IF NOT EXISTS idx_stepps_scores_signal ON stepps_scores(signal_id)",
        "CREATE INDEX IF NOT EXISTS idx_stepps_scores_scored_by ON stepps_scores(scored_by)",
        "CREATE INDEX IF NOT EXISTS idx_stepps_scores_composite ON stepps_scores(composite DESC)",
        "CREATE INDEX IF NOT EXISTS idx_stepps_training_signal ON stepps_training(signal_id)",
        "CREATE INDEX IF NOT EXISTS idx_stepps_training_source ON stepps_training(source)",
    ]
    for idx in indexes:
        c.execute(idx)

    conn.commit()


def _init_db_postgres(c, conn) -> None:
    """PostgreSQL schema with SERIAL, TIMESTAMP, and standard PG types."""
    # TIER 5: META (created first — referenced by signals, mosaics FK)
    c.execute("""
        CREATE TABLE IF NOT EXISTS scans (
            id SERIAL PRIMARY KEY,
            scan_type TEXT NOT NULL,
            sources_json TEXT,
            symbols_json TEXT,
            signal_count INTEGER DEFAULT 0,
            errors_json TEXT,
            status TEXT CHECK(status IN ('running','completed','failed')) DEFAULT 'running',
            started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            completed_at TIMESTAMP WITH TIME ZONE
        )
    """)

    # TIER 1: REFERENCE
    c.execute("""
        CREATE TABLE IF NOT EXISTS instruments (
            id SERIAL PRIMARY KEY,
            symbol TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            type TEXT CHECK(type IN ('stock','private','etf','crypto')) NOT NULL,
            sector TEXT,
            vertical TEXT,
            exchange TEXT,
            market_cap_b NUMERIC,
            data_class TEXT CHECK(data_class IN ('public','private')) DEFAULT 'public',
            metadata_json TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        )
    """)

    # TIER 2: RAW (append-only, immutable)
    c.execute("""
        CREATE TABLE IF NOT EXISTS signals (
            id SERIAL PRIMARY KEY,
            timestamp TEXT NOT NULL,
            symbol TEXT NOT NULL,
            source TEXT NOT NULL,
            signal_type TEXT DEFAULT 'general',
            direction TEXT CHECK(direction IN ('bullish','bearish','neutral')),
            strength NUMERIC,
            confidence NUMERIC,
            raw_json TEXT,
            data_class TEXT CHECK(data_class IN ('public','private')) DEFAULT 'public',
            scan_id INTEGER,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            FOREIGN KEY(scan_id) REFERENCES scans(id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS ohlcv (
            id SERIAL PRIMARY KEY,
            timestamp TEXT NOT NULL,
            symbol TEXT NOT NULL,
            open NUMERIC,
            high NUMERIC,
            low NUMERIC,
            close NUMERIC NOT NULL,
            volume NUMERIC,
            source TEXT DEFAULT 'yfinance',
            data_class TEXT CHECK(data_class IN ('public','private')) DEFAULT 'public',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            UNIQUE(timestamp, symbol, source)
        )
    """)

    # TIER 3: COMPUTED (derived, rebuildable)
    c.execute("""
        CREATE TABLE IF NOT EXISTS mosaics (
            id SERIAL PRIMARY KEY,
            symbol TEXT NOT NULL,
            domain TEXT NOT NULL,
            coherence_score NUMERIC,
            divergence_strength NUMERIC,
            fragments_json TEXT,
            narrative TEXT,
            action TEXT CHECK(action IN ('build_thesis','investigate','pass')),
            data_class TEXT CHECK(data_class IN ('public','private')) DEFAULT 'public',
            scan_id INTEGER,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            FOREIGN KEY(scan_id) REFERENCES scans(id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS theses (
            id SERIAL PRIMARY KEY,
            mosaic_id INTEGER,
            symbol TEXT NOT NULL,
            domain TEXT NOT NULL,
            thesis_type TEXT CHECK(thesis_type IN ('public','private')) DEFAULT 'public',
            vulnerability_json TEXT,
            simulation_json TEXT,
            roi_bear NUMERIC,
            roi_base NUMERIC,
            roi_bull NUMERIC,
            kelly_fraction NUMERIC,
            risk_assessment TEXT,
            lifecycle_stage TEXT CHECK(lifecycle_stage IN ('emerging','validating','confirmed','saturated')),
            status TEXT CHECK(status IN ('pending_review','approved','rejected','deferred')) DEFAULT 'pending_review',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            FOREIGN KEY(mosaic_id) REFERENCES mosaics(id)
        )
    """)

    # TIER 4: HUMAN (sacred, auditable)
    c.execute("""
        CREATE TABLE IF NOT EXISTS decisions (
            id SERIAL PRIMARY KEY,
            thesis_id INTEGER NOT NULL,
            gate TEXT NOT NULL,
            symbol TEXT NOT NULL,
            decision TEXT CHECK(decision IN ('approve','reject','defer','escalate','auto_approve','auto_reject')) NOT NULL,
            confidence NUMERIC,
            human_override BOOLEAN DEFAULT FALSE,
            rationale TEXT,
            trust_level TEXT CHECK(trust_level IN ('manual','supervised','autonomous')),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            FOREIGN KEY(thesis_id) REFERENCES theses(id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS reviews (
            id SERIAL PRIMARY KEY,
            gate TEXT NOT NULL,
            symbol TEXT NOT NULL,
            entity_id INTEGER,
            entity_type TEXT CHECK(entity_type IN ('signal_cluster','mosaic','thesis','position')),
            scores_json TEXT,
            total_score NUMERIC,
            threshold NUMERIC DEFAULT 12.0,
            narrative TEXT,
            dominant_narrative TEXT,
            market_pricing TEXT,
            invalidation TEXT,
            decision TEXT CHECK(decision IN ('promote','watch','discard','forge','hold','reject','execute','defer')) NOT NULL,
            position_size TEXT,
            risk_note TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS positions (
            id SERIAL PRIMARY KEY,
            thesis_id INTEGER NOT NULL,
            symbol TEXT NOT NULL,
            domain TEXT NOT NULL,
            direction TEXT CHECK(direction IN ('long','short')) DEFAULT 'long',
            allocation_pct NUMERIC,
            conviction TEXT CHECK(conviction IN ('high','medium','low')),
            entry_price NUMERIC,
            entry_date TEXT,
            exit_price NUMERIC,
            exit_date TEXT,
            pnl NUMERIC,
            pnl_pct NUMERIC,
            status TEXT CHECK(status IN ('open','closed')) DEFAULT 'open',
            data_class TEXT CHECK(data_class IN ('public','private')) DEFAULT 'public',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            FOREIGN KEY(thesis_id) REFERENCES theses(id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS audit_trail (
            id SERIAL PRIMARY KEY,
            layer TEXT NOT NULL,
            action TEXT NOT NULL,
            symbol TEXT NOT NULL,
            domain TEXT,
            actor TEXT CHECK(actor IN ('human','system')) NOT NULL,
            details_json TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id SERIAL PRIMARY KEY,
            task_type TEXT NOT NULL,
            status TEXT CHECK(status IN ('pending','running','completed','failed','cancelled')) DEFAULT 'pending',
            params_json TEXT,
            result_json TEXT,
            error TEXT,
            attempts INTEGER DEFAULT 0,
            max_attempts INTEGER DEFAULT 3,
            next_retry_at TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            started_at TIMESTAMP WITH TIME ZONE,
            completed_at TIMESTAMP WITH TIME ZONE
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS stepps_scores (
            id SERIAL PRIMARY KEY,
            signal_id INTEGER NOT NULL,
            social_currency NUMERIC,
            triggers NUMERIC,
            emotion NUMERIC,
            public_visibility NUMERIC,
            practical_value NUMERIC,
            stories NUMERIC,
            composite NUMERIC,
            scored_by TEXT CHECK(scored_by IN ('llm','classifier','human')) DEFAULT 'classifier',
            model_version TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            FOREIGN KEY(signal_id) REFERENCES signals(id),
            UNIQUE(signal_id, scored_by)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS stepps_training (
            id SERIAL PRIMARY KEY,
            signal_id INTEGER NOT NULL,
            social_currency NUMERIC,
            triggers NUMERIC,
            emotion NUMERIC,
            public_visibility NUMERIC,
            practical_value NUMERIC,
            stories NUMERIC,
            source TEXT CHECK(source IN ('llm_seed','human_correction')) DEFAULT 'human_correction',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            FOREIGN KEY(signal_id) REFERENCES signals(id)
        )
    """)

    # INDEXES
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
        "CREATE INDEX IF NOT EXISTS idx_reviews_gate ON reviews(gate)",
        "CREATE INDEX IF NOT EXISTS idx_reviews_symbol ON reviews(symbol)",
        "CREATE INDEX IF NOT EXISTS idx_reviews_decision ON reviews(decision)",
        "CREATE INDEX IF NOT EXISTS idx_positions_status ON positions(status)",
        "CREATE INDEX IF NOT EXISTS idx_positions_symbol ON positions(symbol)",
        "CREATE INDEX IF NOT EXISTS idx_audit_symbol ON audit_trail(symbol)",
        "CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)",
        "CREATE INDEX IF NOT EXISTS idx_tasks_status_created ON tasks(status, created_at)",
        "CREATE INDEX IF NOT EXISTS idx_tasks_next_retry ON tasks(next_retry_at)",
        "CREATE INDEX IF NOT EXISTS idx_stepps_scores_signal ON stepps_scores(signal_id)",
        "CREATE INDEX IF NOT EXISTS idx_stepps_scores_scored_by ON stepps_scores(scored_by)",
        "CREATE INDEX IF NOT EXISTS idx_stepps_scores_composite ON stepps_scores(composite DESC)",
        "CREATE INDEX IF NOT EXISTS idx_stepps_training_signal ON stepps_training(signal_id)",
        "CREATE INDEX IF NOT EXISTS idx_stepps_training_source ON stepps_training(source)",
    ]
    for idx in indexes:
        try:
            c.execute(idx)
        except Exception:
            # Ignore errors for pre-existing indexes
            pass

    conn.commit()
