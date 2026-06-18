# Decision Log

The canonical decision log lives in **Notion**:

🔗 **[Decision Log database](https://www.notion.so/9af037e68dbb4f5ab2c22b6a795d211c)**

Created 2026-04-26. Lives under the Social Arb Research Hub parent.

## Why Notion, not a `docs/decisions/` directory

Per [DLOG-4 — Notion is the source of truth](https://www.notion.so/34e7772fa7ae81319533c942dd9d3e3b), tickets, decisions, and research all converge in Dan's Founder OS workspace. A markdown directory in this repo would drift from the Notion DB; the user already lives in Notion.

This file (`DECISIONS.md`) exists only to make the Decision Log discoverable from the code side.

## What goes in the Decision Log

Any non-trivial choice that:

- Affects more than one ticket
- Resolves a trade-off where future readers will ask "why this and not the alternative?"
- Sets process or scope (e.g. BMAD adoption, repo-scope rules)
- Picks a technology that's hard to swap later (e.g. Cytoscape for KG)

Routine implementation choices (variable names, file organization within a single feature) do NOT need a decision-log entry — they live in the PR description.

## How agents use it

Per [DLOG-1 BMAD adoption](https://www.notion.so/34e7772fa7ae81179667e1fe0f8d4a58), the Architect persona consults the Decision Log before proposing any design that might re-litigate a settled decision. Spec docs (`docs/specs/<TICKET-ID>.md`) link the relevant decision IDs at the top so reviewers can verify the spec respects past choices.

## Schema

| Property | Type | Notes |
|---|---|---|
| Decision | Title | One-line summary, imperative ("Adopt BMAD process for AI-assisted development") |
| Date | Date | When the decision was made |
| Status | Select | Proposed / Accepted / Superseded / Reverted |
| Layer | Select | Same Layer values as the Backlog DB, plus `Process` for cross-cutting |
| Author | Select | PM / Architect / Dev / Reviewer / User / System |
| DEC ID | Auto-increment | `DLOG-N` prefix |
| Linked Ticket | URL | The Notion ticket this decision arose from (if any) |
| Linked PR | URL | The PR that landed it (if any) |

The decision page body holds: rationale, alternatives considered, trade-offs, follow-ups.

## Reverting a decision

When a previously-Accepted decision is overturned, mark it `Superseded` (or `Reverted` if the change is destructive) and create a new decision entry that references the old one. Don't edit the original beyond the status field — the history matters.
