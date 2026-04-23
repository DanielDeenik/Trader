# Client Dashboard

A Dash-based "Sustainability Dashboard" (LensIQ project family). Runs
locally against Docker Compose and deploys to Google Cloud Run.

The app is a pure layout with placeholder tab content. It has **no
external API integrations** — no OpenAI, no Airtable, no secrets. The
container needs only the `PORT` variable (Cloud Run provides it).

> **⚠ Rotation still required.** Earlier commits in this branch's
> history contained live OpenAI and Airtable keys in `config/config.yaml`.
> Those have been removed from the working tree, but they remain in
> git history and must be treated as compromised. Rotate them in the
> OpenAI + Airtable dashboards regardless of whether this code uses them.

---

## Run locally

```bash
# Option A — docker-compose (recommended)
docker compose up --build
# → http://localhost:8080

# Option B — direct Python (no container)
pip install -r requirements.txt
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
  --allow-unauthenticated
```

**Flags explained:**

- `--source` — builds the container from the given directory using
  Google Cloud Build. No local Docker push needed.
- `--region` — override to match your data residency policy.
- `--allow-unauthenticated` — public URL. Drop this flag to require
  IAM-based auth and use `gcloud run services proxy` or put it behind
  Identity-Aware Proxy.

No `--set-env-vars` or `--set-secrets` needed — the app takes no
runtime config beyond `PORT`, which Cloud Run sets automatically.

---

## Smoke test

After deploy, open the Cloud Run URL and verify:

1. The **Sustainability Dashboard** heading renders.
2. All four tabs (Regulatory / Insights / Project Plan / Your
   Sustainability Story) switch and show the placeholder copy.

If both pass, the container is healthy. Real visualizations are
tracked as a follow-up in
`docs/superpowers/specs/2026-04-21-client-dashboard-cloud-run-deploy.md`.

---

## Known follow-ups (deferred from this deploy)

- Wire real visualizations into the four tabs.
- Redesign nav + layout to a fiscal.ai-style workflow UI — own spec.
- Dynamic mermaid / ERD / ERM / knowledge-graph views — own spec.
