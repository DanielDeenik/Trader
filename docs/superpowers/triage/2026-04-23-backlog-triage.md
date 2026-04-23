# Social Arb — Backlog Triage (2026-04-23 Overnight)

Scanned the Social Arb Product Backlog DB (`collection://386c820d-dd57-4e50-9966-3930d1a81d15`) and grouped every non-Done item by whether it **can be speced/drafted without a running stack** (doc-only) or **requires the DB + services + test suite to build** (stack-dependent). The split drives what can happen in a sandbox overnight vs. what must wait for Dan's dev machine.

## Summary

| Bucket | Count | Can move tonight? |
| --- | --- | --- |
| Doc-only (spec / triage / design) | 9 | ✔ yes |
| Stack-dependent (build + test needs real env) | 13 | ✘ no |
| Already Done (reference only) | 4 shown | — |

## A. Doc-only — can be speced overnight

These don't touch `social_arb/` runtime code. A spec doc + Notion registration is the whole deliverable. Ordered by strategic leverage for next attended session.

| # | Item | Priority · Effort · Layer | Doc task |
| --- | --- | --- | --- |
| 1 | **Fiscal.ai Workflow UI Redesign** | — (new parent spec) | ✅ Done tonight — `docs/superpowers/specs/2026-04-23-fiscal-ai-workflow-ui-spec.md` |
| 2 | Commitment Pipeline UI (`33d7772f…4fc`) | P1 · L · Frontend | Refined under fiscal.ai Phase 3 (Pipeline view). Add acceptance-criteria addendum. |
| 3 | Knowledge Graph Visualization (`33d7772f…cd`) | P2 · L · Frontend | Refined under fiscal.ai Phase 5. Needs new backend spec for `/api/v1/graph`. |
| 4 | Event-Driven Run Bus (`33d7772f…06c`) | P1 · L · L0 | **Blocking dependency** for fiscal.ai P7 streaming. Spec the `/api/v1/events/stream` SSE endpoint + event schema tonight. |
| 5 | Commitment Stages Table (`33d7772f…8d`) | P0 · M · Nexus | Schema + migration sketch — doc-only, safe. |
| 6 | Commitment Gate Rules Engine (`33d7772f…8e`) | P0 · L · Nexus | Rule-spec DSL design doc. |
| 7 | Commitment Advisor Agent (`33d7772f…1b`) | (unspec'd P) · M · Nexus | Agent contract + prompt template. |
| 8 | Scheduled Research Agents (`33d7772f…d6`) | P2 · M · L0 | Cron schema + delivery targets. |
| 9 | Commitment Pacing Metrics (`33d7772f…5e`) | P1 · M · Nexus | KPI definitions + formulas. |

## B. Stack-dependent — cannot move overnight

These require any of: running FastAPI, real SQLite DB, collector creds (yfinance/Reddit/CoinGecko/Notion token), test stack installed, Docker running.

| Item | Priority · Effort · Layer | Blocks |
| --- | --- | --- |
| Risk & Portfolio Management (`3317772f…0e`) | P0 · **XL** · L5 | Skip per overnight-ops rule (XL = human review) |
| Commitment Stages Table *implementation* | P0 · M · Nexus | DB + migration runner |
| Commitment Gate Rules Engine *impl* | P0 · L · Nexus | Rules runtime + tests |
| Notion Database Sync (`33d7772f…c1`) | P1 · L · L0 | Notion creds + Nexus DB |
| Performance Analytics Dashboard (`3317772f…3e`) | P1 · L · L5 | Live position data |
| News/RSS Collector (`3317772f…33`) | (P?) · ? · L1 | Collector stack |
| Auth & User Settings (`3317772f…70`) | (P?) · ? · L0 | API + DB |
| Mosaic Workbench Page (`3317772f…b4`) | (P?) · ? · L2 | API + DB |
| Moneybird Invoice Sync (`33d7772f…50`) | P2 · M · L0 | Creds + Nexus DB |
| Plaid Bank Transaction Import (`33d7772f…93`) | (P?) · ? · L0 | Plaid creds |
| MCP Tool Integration (`33d7772f…75`) | P2 · L · L0 | MCP server runtime |
| Hybrid Change Detection (`33d7772f…2d`) | (P?) · ? · L0 | KG rebuild pipeline |
| Live Notes (`33d7772f…a4`) | P2 · M · L2 | KG + storage |

## C. Already Done (not in backlog, shown for context)

- Commitment Config Seeds (P0, S, Nexus)
- MosaicWorkbench Actions (P0, M, L2)
- Position Close/Edit (P0, M, L5)
- Deep Dive Dashboard (P0, L, Frontend)

## D. Recommended ordering for Dan's next attended session

1. **Review the Fiscal.ai UI spec** — approve / adjust / reject.
2. **If approved, spawn Phase 0 as a Notion backlog card:** `Frontend Design System — Tailwind + tokens + primitives` (P1, M, Sprint 2).
3. **Unblock overnight-ops** by running the bootstrap runbook (`docs/superpowers/runbooks/overnight-ops-bootstrap.md`) so future cycles can actually build.
4. **Decide on Nexus P0 implementation order:** Commitment Stages Table → Gate Rules Engine → Advisor Agent. These unblock the Commitment Pipeline UI, which is the largest frontend deliverable from the fiscal.ai redesign.
5. **Spec the two missing backend items** before building: `/api/v1/graph` data endpoint (new) and the Run Bus event contract (refine existing backlog item).

## E. What overnight-ops *would* have picked

If the sandbox had a working test/DB stack, the skill's guardrails (S–M effort, not XL, not hot-path) would have chosen **Commitment Stages Table (M, P0)** as tonight's build. Instead it's deferred until the stack runs, and tonight delivered the fiscal.ai spec + this triage + the bootstrap runbook + the morning brief.
