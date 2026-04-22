# tests/test_db.py
import os
import tempfile
import json
import pytest
from social_arb.db.schema import init_db, get_connection
from social_arb.db.store import (
    insert_signal,
    insert_signals_batch,
    query_signals,
    insert_ohlcv_batch,
    query_ohlcv,
    insert_mosaic,
    query_mosaics,
    insert_thesis,
    query_theses,
    insert_decision,
    query_decisions,
    insert_position,
    query_positions,
    start_scan,
    complete_scan,
)


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
            conn.execute(
                "INSERT INTO signals (timestamp, symbol, source, direction, strength, data_class) VALUES (?, ?, ?, ?, ?, ?)",
                ("2026-03-25", "NVDA", "reddit", "bullish", 0.8, "public")
            )
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


class TestStore:
    def test_insert_and_query_signal(self, db_path):
        """Test inserting and querying a single signal."""
        init_db(db_path)

        # Insert a signal
        signal_id = insert_signal(
            timestamp="2026-03-25T10:00:00",
            symbol="NVDA",
            source="reddit",
            direction="bullish",
            strength=0.85,
            confidence=0.9,
            signal_type="general",
            raw_json=json.dumps({"post_id": "123", "upvotes": 500}),
            data_class="public",
            db_path=db_path,
        )
        assert signal_id == 1

        # Query the signal back
        signals = query_signals(symbol="NVDA", db_path=db_path)
        assert len(signals) == 1
        assert signals[0]["symbol"] == "NVDA"
        assert signals[0]["source"] == "reddit"
        assert signals[0]["direction"] == "bullish"
        assert signals[0]["strength"] == 0.85
        assert signals[0]["confidence"] == 0.9

        # Query by source
        signals = query_signals(source="reddit", db_path=db_path)
        assert len(signals) == 1

    def test_insert_and_query_ohlcv(self, db_path):
        """Test inserting and querying OHLCV bars."""
        init_db(db_path)

        bars = [
            {
                "timestamp": "2026-03-24",
                "symbol": "NVDA",
                "open": 130.0,
                "high": 135.0,
                "low": 129.0,
                "close": 134.5,
                "volume": 100000.0,
                "data_class": "public",
            },
            {
                "timestamp": "2026-03-25",
                "symbol": "NVDA",
                "open": 134.5,
                "high": 140.0,
                "low": 133.0,
                "close": 139.2,
                "volume": 120000.0,
                "data_class": "public",
            },
        ]

        count = insert_ohlcv_batch(bars=bars, source="yfinance", db_path=db_path)
        assert count == 2

        # Query back
        ohlcv = query_ohlcv(symbol="NVDA", db_path=db_path)
        assert len(ohlcv) == 2
        assert ohlcv[0]["close"] == 139.2  # Most recent first (DESC)
        assert ohlcv[1]["close"] == 134.5

    def test_insert_mosaic(self, db_path):
        """Test inserting a mosaic."""
        init_db(db_path)

        mosaic_id = insert_mosaic(
            symbol="NVDA",
            domain="AI",
            coherence_score=0.92,
            divergence_strength=0.15,
            fragments_json=json.dumps([{"source": "reddit", "strength": 0.8}]),
            narrative="Strong AI adoption signals from developer communities",
            action="build_thesis",
            data_class="public",
            db_path=db_path,
        )
        assert mosaic_id == 1

        # Query back
        mosaics = query_mosaics(symbol="NVDA", db_path=db_path)
        assert len(mosaics) == 1
        assert mosaics[0]["action"] == "build_thesis"
        assert mosaics[0]["coherence_score"] == 0.92

        # Query by action
        mosaics = query_mosaics(action="build_thesis", db_path=db_path)
        assert len(mosaics) == 1

    def test_insert_decision_with_audit(self, db_path):
        """Test inserting a decision AND verify audit_trail is written."""
        init_db(db_path)

        # First, create a mosaic and thesis (required for decision)
        mosaic_id = insert_mosaic(
            symbol="NVDA",
            domain="AI",
            coherence_score=0.92,
            divergence_strength=0.15,
            fragments_json="{}",
            narrative="Test",
            action="build_thesis",
            data_class="public",
            db_path=db_path,
        )

        thesis_id = insert_thesis(
            mosaic_id=mosaic_id,
            symbol="NVDA",
            domain="AI",
            roi_bear=0.1,
            roi_base=0.3,
            roi_bull=0.8,
            kelly_fraction=0.05,
            lifecycle_stage="validating",
            status="pending_review",
            vulnerability_json="{}",
            simulation_json="{}",
            db_path=db_path,
        )

        # Insert decision with human override
        decision_id = insert_decision(
            thesis_id=thesis_id,
            gate="risk_check",
            symbol="NVDA",
            decision="approve",
            confidence=0.95,
            human_override=True,
            rationale="Strong signals, low risk",
            trust_level="manual",
            db_path=db_path,
        )
        assert decision_id == 1

        # Verify decision was inserted
        decisions = query_decisions(symbol="NVDA", db_path=db_path)
        assert len(decisions) == 1
        assert decisions[0]["human_override"] == 1  # SQLite stores bool as 0/1
        assert decisions[0]["decision"] == "approve"

        # Verify audit_trail was also written
        with get_connection(db_path) as conn:
            audit = conn.execute(
                "SELECT * FROM audit_trail WHERE layer = 'HITL' AND symbol = 'NVDA'"
            ).fetchall()
            assert len(audit) == 1
            audit_row = dict(audit[0])
            assert audit_row["action"] == "decision"
            assert audit_row["actor"] == "human"
            details = json.loads(audit_row["details_json"])
            assert details["decision_id"] == 1
            assert details["decision"] == "approve"

    def test_private_data_isolation(self, db_path):
        """Test that public and private data can be separately queried."""
        init_db(db_path)

        # Insert both public and private signals
        insert_signal(
            timestamp="2026-03-25T10:00:00",
            symbol="NVDA",
            source="reddit",
            direction="bullish",
            strength=0.85,
            confidence=0.9,
            signal_type="general",
            raw_json="{}",
            data_class="public",
            db_path=db_path,
        )

        insert_signal(
            timestamp="2026-03-25T11:00:00",
            symbol="DATABRICKS",
            source="github",
            direction="bullish",
            strength=0.75,
            confidence=0.85,
            signal_type="general",
            raw_json="{}",
            data_class="private",
            db_path=db_path,
        )

        # Query public only
        public_signals = query_signals(data_class="public", db_path=db_path)
        assert len(public_signals) == 1
        assert public_signals[0]["symbol"] == "NVDA"

        # Query private only
        private_signals = query_signals(data_class="private", db_path=db_path)
        assert len(private_signals) == 1
        assert private_signals[0]["symbol"] == "DATABRICKS"

        # Query all (no data_class filter)
        all_signals = query_signals(db_path=db_path)
        assert len(all_signals) == 2
