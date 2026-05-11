"""Notebook + Artifact persistence (NB-002).

Sqlite-backed store sharing the same connection model as NB-001's
SourceStore. Reuses the connection when given (so tests can put
notebooks + sources in the same DB and exercise joins).
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any

from social_arb.notebooks.notebook_models import (
    Artifact,
    ArtifactKind,
    Notebook,
    NotebookListItem,
    NotebookScope,
)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS notebooks (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT,
    scope_ticker TEXT,
    scope_mosaic_id TEXT,
    scope_thesis_id TEXT,
    scope_decision_id TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS notebook_sources (
    notebook_id TEXT NOT NULL,
    source_id TEXT NOT NULL,
    attached_at TEXT NOT NULL,
    PRIMARY KEY (notebook_id, source_id)
);

CREATE TABLE IF NOT EXISTS artifacts (
    id TEXT PRIMARY KEY,
    notebook_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    content TEXT NOT NULL DEFAULT '{}',
    params TEXT NOT NULL DEFAULT '{}',
    content_hash TEXT NOT NULL,
    citations TEXT NOT NULL DEFAULT '[]',
    generator_version TEXT NOT NULL DEFAULT 'v0',
    created_at TEXT NOT NULL,
    UNIQUE(notebook_id, kind, content_hash)
);

CREATE INDEX IF NOT EXISTS idx_notebook_sources_nb ON notebook_sources(notebook_id);
CREATE INDEX IF NOT EXISTS idx_notebook_sources_src ON notebook_sources(source_id);
CREATE INDEX IF NOT EXISTS idx_artifacts_nb ON artifacts(notebook_id);
"""


class NotebookStore:
    """Sqlite-backed CRUD for notebooks, source attachments, artifacts."""

    def __init__(self, db_path: str = ":memory:", conn: sqlite3.Connection | None = None) -> None:
        if conn is not None:
            self._conn = conn
        else:
            # check_same_thread=False so FastAPI handlers (which run in
            # worker threads) can share the connection. Safe because all
            # access goes through this class's serialized methods.
            self._conn = sqlite3.connect(db_path, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    # -- notebook CRUD ------------------------------------------------------ #

    def create(self, notebook: Notebook) -> Notebook:
        cur = self._conn.cursor()
        cur.execute(
            """
            INSERT INTO notebooks
              (id, title, description,
               scope_ticker, scope_mosaic_id, scope_thesis_id, scope_decision_id,
               created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                notebook.id,
                notebook.title,
                notebook.description,
                notebook.scope.ticker,
                notebook.scope.mosaic_id,
                notebook.scope.thesis_id,
                notebook.scope.decision_id,
                notebook.created_at.isoformat(),
                notebook.updated_at.isoformat(),
            ),
        )
        self._conn.commit()
        return notebook

    def get(self, notebook_id: str, *, include_attached: bool = True) -> Notebook | None:
        cur = self._conn.cursor()
        row = cur.execute("SELECT * FROM notebooks WHERE id = ?", (notebook_id,)).fetchone()
        if row is None:
            return None
        nb = self._row_to_notebook(row)
        if include_attached:
            nb.source_ids = [
                r["source_id"]
                for r in cur.execute(
                    "SELECT source_id FROM notebook_sources WHERE notebook_id = ? ORDER BY attached_at",
                    (notebook_id,),
                ).fetchall()
            ]
            nb.artifact_ids = [
                r["id"]
                for r in cur.execute(
                    "SELECT id FROM artifacts WHERE notebook_id = ? ORDER BY created_at",
                    (notebook_id,),
                ).fetchall()
            ]
        return nb

    def list(
        self,
        *,
        ticker: str | None = None,
        mosaic_id: str | None = None,
        thesis_id: str | None = None,
        decision_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[NotebookListItem]:
        clauses: list[str] = []
        params: list[Any] = []
        for col, val in (
            ("scope_ticker", ticker),
            ("scope_mosaic_id", mosaic_id),
            ("scope_thesis_id", thesis_id),
            ("scope_decision_id", decision_id),
        ):
            if val is not None:
                clauses.append(f"n.{col} = ?")
                params.append(val)
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""

        sql = f"""
            SELECT n.*,
                   (SELECT COUNT(*) FROM notebook_sources WHERE notebook_id = n.id) AS source_count,
                   (SELECT COUNT(*) FROM artifacts WHERE notebook_id = n.id) AS artifact_count
            FROM notebooks n
            {where}
            ORDER BY n.created_at DESC
            LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])

        rows = self._conn.cursor().execute(sql, params).fetchall()
        out: list[NotebookListItem] = []
        for r in rows:
            out.append(
                NotebookListItem(
                    id=r["id"],
                    title=r["title"],
                    description=r["description"],
                    scope=NotebookScope(
                        ticker=r["scope_ticker"],
                        mosaic_id=r["scope_mosaic_id"],
                        thesis_id=r["scope_thesis_id"],
                        decision_id=r["scope_decision_id"],
                    ),
                    source_count=r["source_count"] or 0,
                    artifact_count=r["artifact_count"] or 0,
                    created_at=datetime.fromisoformat(r["created_at"]),
                    updated_at=datetime.fromisoformat(r["updated_at"]),
                )
            )
        return out

    def update(
        self,
        notebook_id: str,
        *,
        title: str | None = None,
        description: str | None = None,
        scope: NotebookScope | None = None,
    ) -> Notebook | None:
        cur = self._conn.cursor()
        existing = self.get(notebook_id, include_attached=False)
        if existing is None:
            return None
        new_title = title if title is not None else existing.title
        new_desc = description if description is not None else existing.description
        new_scope = scope if scope is not None else existing.scope
        now = datetime.now(timezone.utc).isoformat()
        cur.execute(
            """
            UPDATE notebooks
            SET title = ?, description = ?,
                scope_ticker = ?, scope_mosaic_id = ?, scope_thesis_id = ?, scope_decision_id = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (
                new_title,
                new_desc,
                new_scope.ticker,
                new_scope.mosaic_id,
                new_scope.thesis_id,
                new_scope.decision_id,
                now,
                notebook_id,
            ),
        )
        self._conn.commit()
        return self.get(notebook_id)

    def delete(self, notebook_id: str) -> bool:
        cur = self._conn.cursor()
        # Cascade: drop attachments + artifacts; Sources themselves are NOT deleted (DLOG-14).
        cur.execute("DELETE FROM notebook_sources WHERE notebook_id = ?", (notebook_id,))
        cur.execute("DELETE FROM artifacts WHERE notebook_id = ?", (notebook_id,))
        cur.execute("DELETE FROM notebooks WHERE id = ?", (notebook_id,))
        deleted = cur.rowcount > 0
        self._conn.commit()
        return deleted

    # -- source attachment -------------------------------------------------- #

    def attach_source(self, notebook_id: str, source_id: str) -> bool:
        """Idempotent attach. Returns True if newly attached, False if already linked."""
        cur = self._conn.cursor()
        try:
            cur.execute(
                "INSERT INTO notebook_sources (notebook_id, source_id, attached_at) VALUES (?, ?, ?)",
                (notebook_id, source_id, datetime.now(timezone.utc).isoformat()),
            )
            self._conn.commit()
            self._touch_notebook(notebook_id)
            return True
        except sqlite3.IntegrityError:
            return False

    def detach_source(self, notebook_id: str, source_id: str) -> bool:
        cur = self._conn.cursor()
        cur.execute(
            "DELETE FROM notebook_sources WHERE notebook_id = ? AND source_id = ?",
            (notebook_id, source_id),
        )
        deleted = cur.rowcount > 0
        if deleted:
            self._touch_notebook(notebook_id)
        self._conn.commit()
        return deleted

    # -- artifacts ---------------------------------------------------------- #

    def save_artifact(self, artifact: Artifact) -> Artifact:
        """Idempotent on (notebook_id, kind, content_hash) — same input → same row."""
        cur = self._conn.cursor()
        try:
            cur.execute(
                """
                INSERT INTO artifacts
                  (id, notebook_id, kind, content, params, content_hash,
                   citations, generator_version, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    artifact.id,
                    artifact.notebook_id,
                    artifact.kind if isinstance(artifact.kind, str) else artifact.kind.value,
                    json.dumps(artifact.content),
                    json.dumps(artifact.params),
                    artifact.content_hash,
                    json.dumps(artifact.citations),
                    artifact.generator_version,
                    artifact.created_at.isoformat(),
                ),
            )
            self._conn.commit()
            return artifact
        except sqlite3.IntegrityError:
            # Cache hit — return the existing artifact.
            row = cur.execute(
                "SELECT * FROM artifacts WHERE notebook_id = ? AND kind = ? AND content_hash = ?",
                (
                    artifact.notebook_id,
                    artifact.kind if isinstance(artifact.kind, str) else artifact.kind.value,
                    artifact.content_hash,
                ),
            ).fetchone()
            return self._row_to_artifact(row)

    def find_artifact_by_hash(
        self,
        notebook_id: str,
        kind: ArtifactKind | str,
        content_hash: str,
    ) -> Artifact | None:
        """Cache lookup for Studio.generate (DLOG-19). Returns the existing
        artifact if (notebook_id, kind, content_hash) already exists."""
        kind_val = kind if isinstance(kind, str) else kind.value
        row = self._conn.cursor().execute(
            "SELECT * FROM artifacts WHERE notebook_id = ? AND kind = ? AND content_hash = ?",
            (notebook_id, kind_val, content_hash),
        ).fetchone()
        return self._row_to_artifact(row) if row else None

    def list_artifacts(self, notebook_id: str) -> list[Artifact]:
        rows = self._conn.cursor().execute(
            "SELECT * FROM artifacts WHERE notebook_id = ? ORDER BY created_at DESC",
            (notebook_id,),
        ).fetchall()
        return [self._row_to_artifact(r) for r in rows]

    def get_artifact(self, artifact_id: str) -> Artifact | None:
        row = self._conn.cursor().execute(
            "SELECT * FROM artifacts WHERE id = ?", (artifact_id,)
        ).fetchone()
        return self._row_to_artifact(row) if row else None

    # -- helpers ----------------------------------------------------------- #

    def _touch_notebook(self, notebook_id: str) -> None:
        self._conn.cursor().execute(
            "UPDATE notebooks SET updated_at = ? WHERE id = ?",
            (datetime.now(timezone.utc).isoformat(), notebook_id),
        )
        self._conn.commit()

    @staticmethod
    def _row_to_notebook(row: sqlite3.Row) -> Notebook:
        return Notebook(
            id=row["id"],
            title=row["title"],
            description=row["description"],
            scope=NotebookScope(
                ticker=row["scope_ticker"],
                mosaic_id=row["scope_mosaic_id"],
                thesis_id=row["scope_thesis_id"],
                decision_id=row["scope_decision_id"],
            ),
            source_ids=[],
            artifact_ids=[],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    @staticmethod
    def _row_to_artifact(row: sqlite3.Row) -> Artifact:
        return Artifact(
            id=row["id"],
            notebook_id=row["notebook_id"],
            kind=ArtifactKind(row["kind"]),
            content=json.loads(row["content"]),
            params=json.loads(row["params"]),
            content_hash=row["content_hash"],
            citations=json.loads(row["citations"]),
            generator_version=row["generator_version"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )
