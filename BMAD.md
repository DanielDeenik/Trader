# BMAD Process — Trader / Social Arb

This repo follows the BMAD method (Breakthrough Method for Agile
AI-Driven Development). Every feature flows through four phases,
mapped to the Notion Kanban columns at
https://www.notion.so/1fed676f1cff473cb9c92c4c646fe529 .

## Phase ↔ column ↔ persona ↔ artifact

| BMAD phase | Notion column | Persona | Artifact |
|---|---|---|---|
| **B**rief / Analysis | `Spec` | PM (`.claude/agents/pm.md`) | One-page PRD at `docs/specs/<TICKET-ID>.md` |
| **M**ap / Planning | `Planned` | PM (acts as Scrum Master) | User stories + acceptance criteria, same file |
| **A**ct / Solutioning | `In Progress` | Architect (`.claude/agents/architect.md`) | Architecture sketch in PR description |
| **A**ct / Implementation | `In Progress` | Dev (`.claude/agents/dev.md`) | Code + tests on a branch |
| **D**emo / Review | `Review` | Reviewer (`.claude/agents/reviewer.md`) | Demo URL + acceptance-criteria checklist |

Floating: `Blocked` — used at any phase when an external dependency
holds the ticket. Final: `Done` — set on PR merge + Cloud Run deploy.

## Phase gates (no skipping)

A ticket cannot move to:
- `Planned` without an approved PRD with explicit goals + non-goals.
- `In Progress` without acceptance criteria and an architecture sketch.
- `Review` without a demo URL or screenshot AND green CI.
- `Done` without all acceptance criteria verifiably checked AND
  Cloud Run revision serving traffic (or local screenshot for
  non-deployable tickets).

## Trust budget (mandatory)

Every AI agent acting on a ticket MUST end its turn with a trust-budget
report listing:

- **Git refs touched:** branches created, commits made, pushes done
- **Cloud resources touched:** Cloud Run revisions, IAM bindings,
  Artifact Registry images, Cloud Build invocations, Cloud SQL changes
- **Notion edits:** which page IDs, what was changed
- **Files changed:** paths added/modified/deleted

This rule exists because of the 2026-04-21 client_dashboard incident
where an entire LensIQ artefact was merged into this repo without a
clear trail. With trust budgets, the user can audit cheaply at every
turn instead of doing forensics at the end.

## How to start a ticket

1. Create a card in the Notion Kanban with:
   - **Feature** (title) — short imperative ("Add HITL queue API")
   - **Layer** — pick from the 5 cognitive layers or Frontend/Cross-cutting
   - **Category** — New Feature / Bug Fix / Improvement / etc.
   - **Priority** — P0–P3
   - **Sprint** — current or Icebox
   - **Effort** — XS–XL guess
   - **Status** — `Backlog`
2. Assign a ticket ID using `KANBAN.md` conventions (e.g. `L4-004`).
3. Move to `Spec`. The PM persona takes over.

## Voice capture (VoiceInk)

Voice-captured ideas land as bare cards in `Backlog` via a small bridge
script (planned: `scripts/voiceink-to-notion.py`). The PM persona
fleshes them into PRDs when promoted to `Spec`.

## Anti-patterns this process exists to prevent

- **Stale-state brainstorming** — fixed by the `git fetch origin` rule
  in `AGENTS.md`.
- **Wrong-repo merges** — fixed by the `REPO_CONTEXT.md` first-read
  rule plus the Reviewer's scope check.
- **Phase skipping** — fixed by hard gates above.
- **Untracked side quests** — fixed by "no work without a ticket."
- **Silent damage** — fixed by mandatory trust budgets.
