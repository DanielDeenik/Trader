# Client Dashboard

A Dash-based "Sustainability Dashboard" (LensIQ project family). Runs
locally against Docker Compose and deploys to Google Cloud Run.

---

## Configuration

All secrets come from environment variables. There is **no** runtime
YAML loading. See `config/config.yaml.example` for the schema.

| Variable            | Required | Notes                                    |
| ------------------- | :------: | ---------------------------------------- |
| `OPENAI_API_KEY`    |    ✔    | `sk-…` from the OpenAI dashboard          |
| `AIRTABLE_API_KEY`  |    ✔    | `pat…` personal access token              |
| `AIRTABLE_BASE_ID`  |    ✔    | `app…` — the Sustainability base ID       |
| `PORT`              |    ✘    | Set by Cloud Run. Defaults to `8080`.     |

> **⚠ Rotate-first note:** If you pulled an older revision of this
> repo, the `config/config.yaml` in history contained live keys.
> Rotate both keys in the OpenAI + Airtable dashboards before deploying.

---

## Run locally

```bash
# Option A — docker-compose (recommended)
export OPENAI_API_KEY=...
export AIRTABLE_API_KEY=...
export AIRTABLE_BASE_ID=...
docker compose up --build
# → http://localhost:8080

# Option B — direct Python (no container)
pip install -r requirements.txt
OPENAI_API_KEY=... AIRTABLE_API_KEY=... AIRTABLE_BASE_ID=... \
  PORT=8050 python -m app.app
# → http://localhost:8050
```

---

## Deploy to Cloud Run

From the repo root:

```bash
gcloud run deploy client-dashboard \
  --source Documents/Projects/client_dashboard \
  --region europe-west1 \
  --allow-unauthenticated \
  --set-env-vars "OPENAI_API_KEY=$OPENAI_API_KEY,\
AIRTABLE_API_KEY=$AIRTABLE_API_KEY,\
AIRTABLE_BASE_ID=$AIRTABLE_BASE_ID"
```

**Flags explained:**

- `--source` — builds the container from the given directory using
  Google Cloud Build. No local Docker push needed.
- `--region` — override to match your data residency policy.
- `--allow-unauthenticated` — public URL. Drop this flag to require
  IAM-based auth and use `gcloud run services proxy` or put it behind
  Identity-Aware Proxy.
- `--set-env-vars` — Cloud Run reads these at boot. For production,
  prefer `--set-secrets` backed by Secret Manager (follow-up).

**Promote to Secret Manager (recommended next step):**

```bash
# One-time — create secrets
echo -n "$OPENAI_API_KEY"   | gcloud secrets create openai-api-key   --data-file=-
echo -n "$AIRTABLE_API_KEY" | gcloud secrets create airtable-api-key --data-file=-

# Redeploy referencing them
gcloud run deploy client-dashboard \
  --source Documents/Projects/client_dashboard \
  --region europe-west1 \
  --allow-unauthenticated \
  --set-secrets "OPENAI_API_KEY=openai-api-key:latest,\
AIRTABLE_API_KEY=airtable-api-key:latest" \
  --set-env-vars "AIRTABLE_BASE_ID=$AIRTABLE_BASE_ID"
```

---

## Smoke test

After deploy, open the Cloud Run URL and verify:

1. The **Sustainability Dashboard** heading renders.
2. All four tabs (Regulatory / Insights / Project Plan / Your
   Sustainability Story) switch and show the placeholder copy.
3. Typing a question into the assistant and clicking **Send** either
   returns an OpenAI reply or the graceful error string. Either
   outcome confirms the container is healthy — the visualization
   implementations and the SDK-v1 migration are tracked as follow-ups
   in `docs/superpowers/specs/2026-04-21-client-dashboard-cloud-run-deploy.md`.

---

## Known follow-ups (deferred from this deploy)

- Migrate OpenAI calls to the v1 client (`openai>=1.0`).
- Swap `airtable-python-wrapper` (archived) → `pyairtable`.
- Wire real visualizations into the four tabs.
- Move to `--set-secrets` + Secret Manager.
- Redesign nav + layout to a fiscal.ai-style workflow UI — own spec.
- Dynamic mermaid / ERD / ERM / knowledge-graph views — own spec.
