# Trader / Social Arb — Repo Context

> **Read this first. Every AI agent MUST read this before any other action.**

## What this repo IS
- The **Social Arb** mosaic-theory information arbitrage engine.
- A FastAPI service (`social_arb/`) + React/Vite frontend (`frontend/`),
  deployed to Cloud Run as service `social-arb` in project
  `delphi-449908`, region `europe-west1`.
- Ground truth for the 5-layer cognitive topology (L0–L5) and the
  Kanban-tracked backlog at
  https://www.notion.so/1fed676f1cff473cb9c92c4c646fe529 .

## What this repo IS NOT
- **NOT LensIQ** (Sustainability Data Platform). LensIQ has its own
  lineage in Notion under "Version 1.x Business Model Canvas
  Sustainability Data Platform" and should live in its own repo
  when revived.
- **NOT a monorepo.** Do not add unrelated apps as subdirectories.
- **NOT the Trader experimental scripts** in `~/Social_Arb/` on Dan's
  laptop — those are untracked drafts, not canonical.
- **NOT DropArb** — that is a separate repo (`DanielDeenik/DropArb`),
  e-commerce arbitrage engine, completely separate codebase.

## Where things live in this repo
| Path | Purpose |
|---|---|
| `social_arb/` | FastAPI app + the 5-layer cognitive engine |
| `frontend/` | React/Vite UI, built into `social_arb/static/` at deploy time |
| `deploy/cloudbuild.yaml` | Cloud Build config for `make deploy` |
| `deploy/cloud-run-service.yaml` | Cloud Run service manifest |
| `Dockerfile` | Multi-stage: frontend build → Python image |
| `Makefile` | One-command targets: `make deploy`, `make logs`, `make url` |
| `pyproject.toml` | Python deps + `[cloud]` extras |
| `tests/` | Pytest suite |
| `docs/specs/` | One-page PRDs per BMAD ticket (created by the PM persona) |
| `.claude/agents/` | BMAD persona definitions (PM / Architect / Dev / Reviewer) |

## Deploy
- `make deploy` from repo root → builds via Cloud Build, deploys to
  Cloud Run service `social-arb`.
- See `Makefile` and `deploy/cloudbuild.yaml` for the wired pipeline.
- Org policy on `delphi-449908` blocks `allUsers` invoker bindings.
  Add specific users with:
  ```
  gcloud run services add-iam-policy-binding social-arb \
    --region=europe-west1 \
    --member="user:<email>" \
    --role=roles/run.invoker
  ```

## Hard rules
1. **Every change traces to a Notion Kanban ticket.** No untracked work.
2. **`git fetch origin` and read this file before brainstorming.** This
   single rule would have prevented the 2026-04-21 client_dashboard
   incident in which an unrelated LensIQ artefact was merged into this
   repo because the agent worked off stale local state.
3. **New top-level subdirectories require an explicit Architect ADR.**
4. **If something doesn't fit Social Arb, it goes in a different repo.**

## Companion docs
- `CLAUDE.md` — Dan's personal memory (people, projects, terms). Read
  for context, do not edit.
- `BMAD.md` — process: which BMAD phase maps to which Kanban column.
- `KANBAN.md` — Kanban-field-to-code conventions.
- `AGENTS.md` — first-contact protocol for AI assistants.
