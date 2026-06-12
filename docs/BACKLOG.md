# Social Arb — Backlog

*Prioritized work queue. Mirrored to Notion. Last reviewed: 2026-06-12.*

Priorities: **P0** now · **P1** next · **P2** soon · **P3** later.

---

## ✅ Done (recent)

- **Option B lakehouse** — DuckDB-over-Parquet analytical tier; sync + cached
  query connection; trend path 2× faster warm, parity-tested. (`social_arb/lake/`)
- **Local Docker stack** — Postgres + api + collect/analyze/lake-sync runners +
  shared lake volume; full data flow verified, durable across restarts.
- **Postgres compatibility** — adapter fixes: `?`→`%s`, `RETURNING id`,
  numpy adapters, `NUMERIC`→float, `TIMESTAMP`→ISO-str; seed + auth work.
- **Full component audit (Postgres)** — every frontend→backend endpoint probed;
  16/17 green. Fixed SQLite-only SQL (`GROUP_CONCAT`→`string_agg`,
  `DATE()`/`datetime('now')`→cross-backend), positional `row[0]` access, and
  `trend_scorer` raw-sqlite `_get_conn` → backend-aware. Only `/agents/*`
  remains (agents are SQLite-only — see P1).
- **Cloud Run deploy (Option B)** — gcsfuse lake mount, min-instances=1,
  scheduler off on web tier, scheduled lake-sync job, DuckDB extensions baked.
- **Code review fixes** — `hours=0` 500, break-even log, dead imports,
  trends query validation, `run.sh`→`dev.sh`.

---

## 🔴 P0 — In flight

- [ ] **Provision Cloud SQL + move live Cloud Run onto Postgres.**
  Create Postgres 16 (`db-f1-micro`, ~$9/mo), `DATABASE_URL` in Secret Manager,
  wire service + jobs (`--add-cloudsql-instances` + `--set-secrets`), run
  collect→analyze→lake-sync, verify live `/trends`. *(Blocked only on gcloud
  re-auth.)*

---

## 🟠 P1 — Next

- [ ] **Collectors don't populate `instruments` / `ohlcv`** on a plain `collect`
  run → ticker names default to symbol, sparklines empty. Wire collector output
  to those tables (or a backfill step in the pipeline).
- [ ] **Migrate agents to the DB adapter** (37 raw `sqlite3.connect` sites).
  Currently the autonomous pipeline is SQLite-only and disabled on the web tier;
  adapter migration lets it run on Postgres/cloud.
- [ ] **Cloud access decision** — service is private (org Domain-Restricted-
  Sharing blocks public). Keep private + `gcloud run services proxy` / IAP, or
  override the org policy for a public login. *(Decision pending.)*
- [ ] **Cloud collect job** — scheduled collection on cloud so the live lake
  actually fills (mirror of `lake-job`).

---

## 🟡 P2 — Soon

- [ ] **Dead HITL review queue** — `gatekeeper.py` queries `WHERE decision IS
  NULL` but the column is `NOT NULL`; `lifecycle_stage` not selected → ranking
  always `validating`. Needs the intended "pending" semantics.
- [ ] **0–100 vs 0–1 scale ambiguity** for divergence/coherence (guessy
  `x/100 if x>1` heuristic in 5 spots + context.py dead-band). Confirm canonical
  stored scale, then normalize once.
- [ ] **Operational trend path N+1** — `get_trending_tickers` (non-lake path)
  fires ~250 queries; batch into `WHERE IN`. (Lake path already set-based.)
- [ ] **Test infra** — `httpx 0.28` / `starlette 0.35` `TestClient`
  incompatibility breaks all API tests; pin/bump deps.
- [ ] **Agent concurrency edges** — `base.py` ERROR-state tick stall; duplicate
  event subscriptions on restart; supervisor restart-by-name failure.

---

## 🟢 P3 — Later

- [ ] **auth.py hardening** — works on Postgres now via the adapter, but the
  routes still embed sqlite-style SQL; tidy to `get_placeholder()` for clarity.
- [ ] **Secrets** — move any inline config to Secret Manager across envs.
- [ ] **Observability** — structured request metrics for the lakehouse path
  (cold vs warm, sync freshness).
- [ ] **Frontend** — surface lake freshness + domain filters on the trends view.

---

*Source: this repo + the 2026-06 session work. Keep in sync with
`docs/ARCHITECTURE.md` and the Notion mirror.*
