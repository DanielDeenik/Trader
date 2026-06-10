# Option B — DuckDB + Parquet Lakehouse on Cloud Run

A two-tier architecture that keeps the operational store for live agent writes
and serves all heavy analytics from DuckDB over columnar Parquet (local dir or
a GCS bucket). No Kubernetes.

```
┌─────────────────────────────────────────────────────────────┐
│ Cloud Run service  (social-arb, min-instances=1)            │
│                                                             │
│  FastAPI + agents ──writes──▶ Operational store (OLTP)      │
│                                  SQLite (vol) | Cloud SQL    │
│                                        │                    │
│  lake-sync (Cloud Run Job, scheduled) ─┘ COPY → Parquet      │
│                                        ▼                    │
│  /trends, /alerts ──reads──▶ DuckDB ──▶ Parquet lake (OLAP) │
│                                          gs://<bucket>/lake  │
└─────────────────────────────────────────────────────────────┘
```

## Why this shape

- **DuckDB is OLAP, single-writer.** It is the *query* engine, not the
  operational DB. Agents keep writing to the operational store; DuckDB only
  reads Parquet snapshots. (See `social_arb/lake/`.)
- **Durability + speed live in the lake.** Parquet on GCS is durable, cheap,
  and columnar — analytical queries (trend scoring, divergence) run set-based
  instead of the old per-symbol N+1. Measured ~2× faster warm at 250 symbols;
  the gap widens with scale and with GCS predicate pushdown.
- **Portable.** Parquet + DuckDB run anywhere (other clouds, a VPS). Staying on
  GCP is convenience, not lock-in.

## Components

| Piece | What | Code / config |
|-------|------|---------------|
| Sync | Operational tables → Parquet | `social_arb/lake/sync.py`, CLI `social-arb lake-sync` |
| Query | DuckDB views over Parquet | `social_arb/lake/query.py` (cached connection) |
| Analytics | Trend engine reads the lake when `LAKE_DIR` is set | `social_arb/engine/trend_scorer.py` |

`LAKE_DIR` toggles the whole thing: unset → operational path (unchanged); set
to a local dir or `gs://bucket/prefix` → DuckDB/Parquet path.

## Operational tier (pick one)

The lake makes *analytics* durable; the operational store still needs to
survive restarts. Both are already supported by `db/adapter.py`:

- **Cloud SQL (Postgres)** — set `DATABASE_URL=postgresql://…`. Recommended for
  durable live state. `lake-sync` reads it via DuckDB's postgres scanner.
- **SQLite on a mounted volume** — simplest; fine at one instance.

## Deploy

```bash
# 1. One-time: create the lake bucket
make lake-bucket                 # gs://<PROJECT>-social-arb-lake

# 2. Deploy the service with the lake wired in (min-instances=1)
make deploy-lake

# 3. Create the scheduled sync job (operational → Parquet every 15 min)
make lake-job

# Manual sync any time (local or against the deployed DB)
make lake-sync                   # or: social-arb lake-sync --lake-dir gs://…
```

## GCS access on Cloud Run (gcsfuse volume)

The bucket is mounted into the container as a Cloud Run **volume** (gcsfuse) at
`/mnt/lake`, and `LAKE_DIR=/mnt/lake`. DuckDB then reads/writes plain local
files — no httpfs extension, no HMAC keys, no `credential_chain`. gcsfuse
authenticates as the Cloud Run service account (which needs
`roles/storage.objectAdmin` on the bucket). Requires the gen2 execution
environment (set by `make deploy-lake` / `make lake-job`).

Off-Cloud-Run (e.g. local against a real bucket) the code path also supports a
direct `gs://` `LAKE_DIR` via DuckDB httpfs + HMAC keys
(`GCS_HMAC_KEY_ID` / `GCS_HMAC_SECRET`).

## Sync cadence

`lake-sync` is incremental-cheap (a few `COPY ... TO parquet` statements).
Default cadence 15 min via Cloud Scheduler → Cloud Run Job. Lower it for
fresher dashboards; the cost is one DuckDB attach + N columnar writes.
