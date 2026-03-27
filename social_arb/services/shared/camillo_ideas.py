"""
Camillo Ideas — Idea scoring and storage for the Social Arb scan modules.

Provides:
  - CamilloIdea dataclass with 8-factor Camillo scoring (Discovery/Arbitrage/Window)
  - store_idea() / get_ideas() / log_scan() for DB persistence
  - init_ideas_db() to create the ideas + scan_log tables

Camillo Score (0-100):
  Discovery (30%): c1_organic, c2_velocity, c3_crossplatform
  Arbitrage (40%): c4_premainstream, c5_pricetotrend
  Window (30%): c6_category, c7_demographic, c8_timing

Grade:  A (80+), B (60-79), C (40-59), D (20-39), F (<20)
"""

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional, List, Dict
from pathlib import Path

# Use the same DB as the main social_arb database
DB_PATH = str(Path(__file__).parent / "../../db/social_arb.db")

import sqlite3


def _get_conn(db_path: Optional[str] = None):
    path = db_path or DB_PATH
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_ideas_db(db_path: Optional[str] = None):
    """Create the camillo_ideas and camillo_scan_log tables if they don't exist."""
    conn = _get_conn(db_path)
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS camillo_ideas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                instrument_type TEXT NOT NULL,
                ticker TEXT NOT NULL,
                name TEXT NOT NULL,
                stage TEXT DEFAULT 'signal',
                signal_source TEXT,
                signal_description TEXT,
                signal_date TEXT,
                thesis TEXT,
                narrative TEXT,
                c1_organic REAL DEFAULT 0.0,
                c2_velocity REAL DEFAULT 0.0,
                c3_crossplatform REAL DEFAULT 0.0,
                c4_premainstream REAL DEFAULT 0.0,
                c5_pricetotrend REAL DEFAULT 0.0,
                c6_category REAL DEFAULT 0.0,
                c7_demographic REAL DEFAULT 0.0,
                c8_timing REAL DEFAULT 0.0,
                camillo_score REAL DEFAULT 0.0,
                camillo_grade TEXT DEFAULT 'F',
                confidence REAL DEFAULT 0.0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS camillo_scan_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scan_name TEXT NOT NULL,
                instrument_type TEXT NOT NULL,
                searches INTEGER DEFAULT 0,
                facts_found INTEGER DEFAULT 0,
                ideas_created INTEGER DEFAULT 0,
                ideas_updated INTEGER DEFAULT 0,
                top_signal TEXT,
                summary TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_camillo_ideas_ticker ON camillo_ideas(ticker)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_camillo_ideas_type ON camillo_ideas(instrument_type)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_camillo_ideas_grade ON camillo_ideas(camillo_grade)")
        conn.commit()
    finally:
        conn.close()


@dataclass
class CamilloIdea:
    instrument_type: str
    ticker: str
    name: str
    stage: str = "signal"
    signal_source: str = ""
    signal_description: str = ""
    signal_date: str = ""
    thesis: str = ""
    narrative: str = ""
    # Discovery (30%)
    c1_organic: float = 0.0
    c2_velocity: float = 0.0
    c3_crossplatform: float = 0.0
    # Arbitrage (40%)
    c4_premainstream: float = 0.0
    c5_pricetotrend: float = 0.0
    # Window (30%)
    c6_category: float = 0.0
    c7_demographic: float = 0.0
    c8_timing: float = 0.0
    confidence: float = 0.0

    @property
    def camillo_score(self) -> float:
        """Weighted Camillo score (0-100). Crypto weights: Discovery 30%, Arbitrage 40%, Window 30%."""
        discovery = (self.c1_organic + self.c2_velocity + self.c3_crossplatform) / 3.0
        arbitrage = (self.c4_premainstream + self.c5_pricetotrend) / 2.0
        window = (self.c6_category + self.c7_demographic + self.c8_timing) / 3.0
        raw = discovery * 0.30 + arbitrage * 0.40 + window * 0.30
        return round(raw * 100, 1)

    @property
    def camillo_grade(self) -> str:
        s = self.camillo_score
        if s >= 80:
            return "A"
        elif s >= 60:
            return "B"
        elif s >= 40:
            return "C"
        elif s >= 20:
            return "D"
        return "F"


def store_idea(idea: CamilloIdea, db_path: Optional[str] = None) -> int:
    """Store a CamilloIdea in the database. Returns the row ID."""
    conn = _get_conn(db_path)
    try:
        cursor = conn.execute(
            """
            INSERT INTO camillo_ideas
            (instrument_type, ticker, name, stage, signal_source, signal_description,
             signal_date, thesis, narrative, c1_organic, c2_velocity, c3_crossplatform,
             c4_premainstream, c5_pricetotrend, c6_category, c7_demographic, c8_timing,
             camillo_score, camillo_grade, confidence)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                idea.instrument_type, idea.ticker, idea.name, idea.stage,
                idea.signal_source, idea.signal_description, idea.signal_date,
                idea.thesis, idea.narrative,
                idea.c1_organic, idea.c2_velocity, idea.c3_crossplatform,
                idea.c4_premainstream, idea.c5_pricetotrend,
                idea.c6_category, idea.c7_demographic, idea.c8_timing,
                idea.camillo_score, idea.camillo_grade, idea.confidence,
            ),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def get_ideas(
    instrument_type: Optional[str] = None,
    ticker: Optional[str] = None,
    min_grade: Optional[str] = None,
    limit: int = 50,
    db_path: Optional[str] = None,
) -> List[Dict]:
    """Query camillo_ideas with optional filters. Returns list of dicts."""
    conn = _get_conn(db_path)
    try:
        query = "SELECT * FROM camillo_ideas WHERE 1=1"
        params = []
        if instrument_type:
            query += " AND instrument_type = ?"
            params.append(instrument_type)
        if ticker:
            query += " AND ticker = ?"
            params.append(ticker)
        if min_grade:
            grade_map = {"A": 80, "B": 60, "C": 40, "D": 20, "F": 0}
            query += " AND camillo_score >= ?"
            params.append(grade_map.get(min_grade, 0))
        query += " ORDER BY camillo_score DESC LIMIT ?"
        params.append(limit)
        cursor = conn.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def log_scan(
    scan_name: str,
    instrument_type: str,
    searches: int = 0,
    facts_found: int = 0,
    ideas_created: int = 0,
    ideas_updated: int = 0,
    top_signal: str = "",
    summary: str = "",
    db_path: Optional[str] = None,
) -> int:
    """Log a scan run to camillo_scan_log. Returns row ID."""
    conn = _get_conn(db_path)
    try:
        cursor = conn.execute(
            """
            INSERT INTO camillo_scan_log
            (scan_name, instrument_type, searches, facts_found, ideas_created,
             ideas_updated, top_signal, summary)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (scan_name, instrument_type, searches, facts_found,
             ideas_created, ideas_updated, top_signal, summary),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()
