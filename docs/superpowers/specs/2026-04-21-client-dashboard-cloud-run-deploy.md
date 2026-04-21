# Client Dashboard — Cloud Run Deploy (2026-04-21)

**Status:** Approved for execution (brainstorming gate passed 2026-04-21). Spec-review loop skipped — scope is cleanup + containerization, not new functionality.
**Owner:** Dan Deenik
**Repo:** `danieldeenik/Trader`
**App path:** `Documents/Projects/client_dashboard/`

## Context

Dan has several in-flight projects. Two are relevant here:

1. **Social Arb** (mosaic-theory info-arb engine) — the primary project, tracked in the "Social Arb — Product Backlog" Notion DB. Has an active backlog card **☁️ GCP Cloud Deployment** (Sprint 4 Scale, P1, Status = Blocked on IAM). Code is **not in this repo** — `Social_Arb/` is untracked here. Unblocking IAM and deploying Social Arb is a separate track Dan runs from the host (`gcloud` console).
2. **Client Dashboard** (a Dash "Sustainability Dashboard" — OpenAI + Airtable `sustainability_requirements`). Code is present in this repo under `Documents/Projects/client_dashboard/` (byte-identical duplicate at `Documents/GitHub/client_dashboard/`). Has a Dockerfile but is not deploy-ready. No active Notion backlog item.

**This spec covers #2 only.** Dan picked "C. Both" in brainstorming but Social Arb is out-of-reach from this worktree, so we narrow today's PR to client_dashboard.

## Goals

- Ship a Cloud Run–deployable image of `client_dashboard` with no live secrets in the image or repo.
- Remove redundancy and dead code that would confuse a reviewer or a future deploy.
- Register all design decisions in Notion under the Sustainability Platform lineage so this session's work is traceable and not a "new direction."
- Document the exact `gcloud run deploy` command for Dan to run.

## Non-goals (explicitly deferred)

- **Social Arb IAM unblock** — Dan runs `gcloud projects add-iam-policy-binding` himself (noted on the existing Notion card).
- **fiscal.ai-style workflow UI redesign** — own spec, own session. Needs mockups and a data contract for the HITL question queue.
- **Dynamic mermaid / ERD / ERM / knowledge-graph views** — own spec, own session. Viz subsystem needs its own data binding layer.
- **OpenAI SDK v1 migration** — current code uses deprecated `openai.Completion.create()` with `text-davinci-003`. Not called at startup, so doesn't block container launch. Deferred to a follow-up so this PR stays focused.
- **pyairtable migration** — `airtable-python-wrapper` is archived but works. Same rationale as OpenAI.
- **Secret Manager integration** — for today, env vars on the Cloud Run service. Secret Manager wiring is a follow-up.

## Design decisions

### D1. Canonical copy = `Documents/Projects/client_dashboard/`
`Documents/GitHub/client_dashboard/` is byte-for-byte identical (verified with `diff -r`). Delete the `GitHub/` copy.

### D2. Canonical entry point = `app/app.py`
`app/main.py` is a broken duplicate — it has lines 1–36 repeated at 37–71, an incorrect import path (`from services.openai_service` vs `from app.services.openai_service`), and calls an undefined `load_api_keys()`. It's unused. Delete it.

### D3. Secrets never in repo, env vars on Cloud Run
- `config/config.yaml` (currently contains live OpenAI + Airtable keys) is **deleted from the working tree and added to `.gitignore`**.
- A committed `config/config.yaml.example` shows the schema.
- Services read from `os.environ[...]` directly. No YAML loading in production.
- **Dan must rotate both keys manually** — they are already in git history (commit `d6a90d7b` and earlier). This spec cannot un-leak them; it prevents further leakage.

### D4. Production server = gunicorn, binding `0.0.0.0:$PORT`
Cloud Run sends traffic to whatever the container listens on via the `$PORT` env var (default 8080). The existing `CMD ["python", "app/app.py"]` runs Dash's dev server on `localhost:8050` — Cloud Run health checks will fail. New CMD:
```
exec gunicorn --bind 0.0.0.0:${PORT:-8080} --workers 2 --threads 4 --timeout 120 app.app:server
```
`server = app.server` is already exposed at `app/app.py:61`.

### D5. Python 3.11-slim base
Bump from 3.9. No code depends on 3.9 specifics; 3.11 is faster and has security patches 3.9 is losing.

### D6. Pin sanity, not full upgrade
- Add: `gunicorn>=21.2.0`
- Bump critical-CVE pins: `werkzeug>=3.0.0` (CVE-2023-25577), `dash>=2.17.0`, `plotly>=5.17.0`.
- Leave `openai`, `airtable-python-wrapper`, `scikit-learn` as-is for this PR (deferred upgrades — see non-goals).

### D7. `.dockerignore` enforces a clean image
Exclude: `.git`, `__pycache__`, `*.pyc`, `.DS_Store`, `docs/`, `config/config.yaml`, `.env`, `.venv`, `src/` (empty anyway after D8), `app/oil_and_gas/` (empty after D8).

### D8. Delete dead code in one pass
- `src/dash1.py`, `src/dash2.py`, `src/dash3.py`, `src/dash4.py`, `src/const.py` — all 0 bytes, referenced only from commented-out imports.
- `app/oil_and_gas/` — empty stub, never imported.
- In `app/app.py`: lines 10–50 (commented validation block + commented imports), lines 115–149 (dead callback calling non-existent `generate_visualizations{1..4}()`).

### D9. `docker-compose.yml` kept + fixed
Current file has literal `\n` escape sequences on line 1 that break YAML. Fix to a clean single-service compose for local dev. Not used by Cloud Run.

### D10. Deploy procedure = `gcloud run deploy` from source
No Cloud Build trigger for this PR. Dan runs:
```
gcloud run deploy client-dashboard \
  --source Documents/Projects/client_dashboard \
  --region europe-west1 \
  --allow-unauthenticated \
  --set-env-vars "OPENAI_API_KEY=…,AIRTABLE_API_KEY=…,AIRTABLE_BASE_ID=…"
```
Region and auth policy are placeholders Dan can override. CI-driven deploys are a follow-up.

## Change list (this PR)

Commits, in order:

1. **docs: add Cloud Run deploy spec** — this file.
2. **security: remove leaked config.yaml + gitignore + example template**
3. **chore: delete byte-identical duplicate at Documents/GitHub/client_dashboard/**
4. **refactor: remove dead code (src/, oil_and_gas/, main.py, commented blocks in app.py)**
5. **deploy: Cloud Run-ready Dockerfile + gunicorn + .dockerignore + fixed docker-compose**
6. **refactor: load config from env vars (drop yaml dependency at runtime)**
7. **docs: add deploy README with gcloud command**

## Open items / risks

- **Keys in git history:** rotation is on Dan. This PR cannot remove history without a rewrite, which is out of scope and risky on `main`.
- **OpenAI Completion API removed:** user-triggered callbacks that hit OpenAI will 404 at runtime. Dashboard still boots. SDK migration tracked as a follow-up.
- **Airtable wrapper archived:** same — works today, migrate later.
- **No tests:** the repo has no test suite. Post-deploy smoke test = load the Cloud Run URL and confirm the Dash layout renders.

## Notion registration

- **Update** the existing `☁️ GCP Cloud Deployment` card (Social Arb backlog) with a 2026-04-21 status note: still Blocked on IAM, exact `gcloud` commands for Dan to unblock on the host. Status stays Blocked.
- **Create** a child page under the Sustainability Platform v1.1 Business Model Canvas titled "Client Dashboard — Cloud Run Deploy (2026-04-21)" containing: design decisions D1–D10, deferred items, PR link, key-rotation reminder.

No new top-level pages. No new databases. No forked direction.

## References

- Brainstorming transcript: this session, 2026-04-21.
- Codebase audit: performed by Explore subagent, 2026-04-21.
- Notion: `☁️ GCP Cloud Deployment` card `3317772f-a7ae-810e-aa10-f8ec5c3f0a61`.
- Notion: Sustainability Platform v1.1 `2c57772f-a7ae-8081-bcbb-f4ef682c7030`.
