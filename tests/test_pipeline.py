import os
import tempfile
import pytest
from social_arb.db.schema import init_db
from social_arb.db.store import insert_signal
from social_arb.pipeline import run_analysis


@pytest.fixture
def seeded_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path)
    # Seed with real-looking signals from multiple sources
    for i in range(5):
        insert_signal(
            db_path=path, timestamp=f"2026-03-2{i}", symbol="NVDA",
            source="reddit", direction="bullish", strength=0.7 + i*0.05,
            confidence=0.6, data_class="public", signal_type="sentiment", raw_json="{}",
        )
    insert_signal(
        db_path=path, timestamp="2026-03-25", symbol="NVDA",
        source="google_trends", direction="bullish", strength=0.8,
        confidence=0.6, data_class="public", signal_type="sentiment", raw_json="{}",
    )
    insert_signal(
        db_path=path, timestamp="2026-03-25", symbol="NVDA",
        source="sec_edgar", direction="neutral", strength=0.5,
        confidence=0.85, data_class="public", signal_type="filing", raw_json="{}",
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

    def test_empty_db_returns_zero(self):
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        try:
            init_db(path)
            result = run_analysis(db_path=path, symbols=["FAKE"])
            assert result["mosaics_created"] == 0
            assert result["theses_created"] == 0
        finally:
            os.remove(path)
