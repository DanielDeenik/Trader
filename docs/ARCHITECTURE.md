# Social Arb — Architecture

*Information-arbitrage platform (Camillo mosaic theory). This document is the
source of truth for the system shape and is mirrored to Notion.*

Last reviewed: 2026-06-12.

---

## 1. One-paragraph summary

Social Arb collects weak signals from many sources, assembles them into mosaics,
forges investment theses, and surfaces trending tickers — across public, private,
and crypto domains. It runs as a **FastAPI + React** app backed by a **two-tier
lakehouse (Option B)**: a transactional operational store for live writes, and a
**DuckDB-over-Parquet** analytical tier for the dashboards. The same containers
run locally (Docker Compose + Postgres) and in the cloud (Cloud Run + Cloud SQL),
so promotion is config-only.

---

## 2. Cognitive topology (5 layers)

The pipeline mirrors Camillo's cognitive architecture; each layer is an agent
tier that publishes events to the next (see `social_arb/agents/`):

| Layer | Agent | Role |
|-------|-------|------|
| L0 | Sentinel | Keep raw signals fresh; orchestrate collection |
| L1 | Assembler | Group signals into mosaics (coherence, divergence) |
| L2 | Strategist | Forge theses (Kelly sizing, ROI scenarios, lifecycle) |
| L3 | Gatekeeper | HITL review gates; auto-promote on trust |
| L4 | Executor | Position lifecycle (open/close, PnL) |
| — | Supervisor / Registry / Knowledge | Lifecycle, health, narrative memory |

> **Note:** the agent tier currently uses raw `sqlite3` (37 call sites) and is
> *not* Postgres-aware — it is disabled on the served web tier. The CLI
> collect/analyze path (`store.py`) is fully adapter-clean and is what feeds the
> cloud lakehouse today. Migrating the agents to the adapter is a backlog item.

---

## 3. Option B — the two-tier lakehouse

```
                    ┌─────────────────────────────────────────┐
   writes           │  Operational tier (OLTP)                │
  ───────────────▶  │  SQLite (local file) | Postgres/Cloud SQL│
  collect/analyze   │  social_arb/db/store.py (adapter-clean) │
                    └───────────────┬─────────────────────────┘
                                    │ lake-sync (DuckDB ATTACH + COPY)
                                    ▼
                    ┌─────────────────────────────────────────┐
   reads            │  Analytical tier (OLAP)                 │
  ◀───────────────  │  Parquet lake (local dir | GCS bucket)  │
  /trends /alerts   │  DuckDB cached connection, views over   │
                    │  read_parquet  (social_arb/lake/)       │
                    └─────────────────────────────────────────┘
```

- **Why split:** DuckDB is single-writer OLAP — the *query* engine, not the
  operational DB. Agents/collectors keep writing to the operational store;
  DuckDB only reads Parquet snapshots. Durability + analytical speed live in the
  lake; the operational store handles concurrent writes.
- **Toggle:** `LAKE_DIR` unset → operational query path (unchanged). Set to a
  local dir or `gs://…`/mount → DuckDB-over-Parquet path. Output is identical
  (both call `_compute_ticker_row`); warm lakehouse path is ~2× faster and
  replaces per-symbol N+1 with set-based queries.
- **Sync:** `social-arb lake-sync` (CLI) / a scheduled job. DuckDB attaches the
  operational store (sqlite or postgres scanner) and `COPY`s each table to
  Parquet — no pandas glue.

Code: `social_arb/lake/{sync,query}.py`, `social_arb/engine/trend_scorer.py`.

---

## 4. Backend adapter (SQLite ⇄ Postgres)

`social_arb/db/adapter.py` is the compatibility layer, selected by `DATABASE_URL`:

- `?` placeholders → `%s` for psycopg2 (call sites may also use `get_placeholder()`).
- INSERTs auto-append `RETURNING id` so `cursor.lastrowid` works on Postgres.
- numpy scalars (float64/int64/bool_) registered as psycopg2 adapters.
- `NUMERIC` → `float` on read (psycopg2 returns `Decimal`; the engine does float math).

These five fixes were shaken out by the first real Postgres run and are required
for Cloud SQL.

---

## 5. Deployment

| | Local (Docker Compose) | Cloud (GCP) |
|---|---|---|
| Operational store | `db` = Postgres 16 (volume) | Cloud SQL Postgres |
| App | `api` (FastAPI, gunicorn) | Cloud Run service, min-instances=1 |
| Lake | shared `lake` volume (Parquet) | GCS bucket via gcsfuse mount (`/mnt/lake`) |
| Runners | `collect`/`analyze`/`lake-sync` (`docker compose run`) | Cloud Run Jobs (scheduled) |
| Auth/access | open localhost | private (org Domain-Restricted-Sharing); proxy / IAP |

- Local: `docker compose up -d db api`, then `run --rm collect|analyze|lake-sync`.
- Cloud: `make lake-bucket` → `make deploy-lake` → `make lake-job` (see
  `deploy/OPTION_B.md`). Image bakes DuckDB httpfs/sqlite/postgres extensions.
- Project `delphi-449908`, region `europe-west1`, service `social-arb`.

---

## 6. Data flow (end-to-end, verified locally)

```
collect (yfinance/…) ──▶ Postgres signals (696)
analyze              ──▶ Postgres mosaics (29) / theses
lake-sync            ──▶ Parquet lake
/trends              ──▶ DuckDB over Parquet ──▶ scored tickers (~30ms warm)
```

Health: `/api/v1/health` reports backend + table counts. `unhealthy` simply
means zero rows (empty DB), not a fault.

---

## 7. Source map

| Area | Path |
|------|------|
| API + routes | `social_arb/api/` |
| Agents (5-layer) | `social_arb/agents/` |
| Collectors | `social_arb/collectors/` |
| Engines (trend, kelly, conviction, gold-rush, …) | `social_arb/engine/` |
| DB adapter + schema + store | `social_arb/db/` |
| Lakehouse | `social_arb/lake/` |
| Frontend (React/Vite) | `frontend/` |
| Deploy (Cloud Run, Option B) | `deploy/`, `Makefile`, `Dockerfile`, `docker-compose.yml` |
| CLI | `social_arb/cli.py` (collect/analyze/review/status/lake-sync) |
