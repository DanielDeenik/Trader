# Kanban ↔ Code Conventions

Notion DB: https://www.notion.so/1fed676f1cff473cb9c92c4c646fe529

## Ticket ID format

`<LAYER-ABBREV>-<NNN>` — e.g. `L4-004`, `FE-021`, `XC-003`.

Use the next sequential number per Layer prefix. Check existing tickets
in Notion before claiming an ID.

## Ticket → branch

`<layer-abbrev>/<NNN>-<short-slug>`

| Notion `Layer` | Branch prefix | Example branch |
|---|---|---|
| L0 Infrastructure | `l0/` | `l0/042-bigquery-export` |
| L1 Signal Radar | `l1/` | `l1/017-reddit-rate-limit` |
| L2 Mosaic Assembly | `l2/` | `l2/008-divergence-coh-fix` |
| L3 Thesis Forge | `l3/` | `l3/011-kelly-clamp` |
| L4 Decisions | `l4/` | `l4/004-hitl-queue` |
| L5 Portfolio | `l5/` | `l5/006-position-export` |
| Frontend | `fe/` | `fe/021-fiscal-ui-shell` |
| Cross-cutting | `xc/` | `xc/003-bmad-bootstrap` |
| Nexus Financial | `nx/` | `nx/002-commit-stages` |

## Ticket → commit prefix

Conventional Commits + ticket ID:

```
<type>(<layer-abbrev>): <message> [TICKET-ID]
```

Types: `feat` · `fix` · `refactor` · `docs` · `test` · `chore` · `perf` · `style`

Examples:
- `feat(l4): add HITL queue table [L4-004]`
- `fix(l1): clamp pytrends batch size [L1-017]`
- `docs(xc): bootstrap BMAD process [XC-003]`

## Ticket → PR title

`[TICKET-ID] <one-line summary>` — e.g. `[L4-004] HITL queue: schema + API`

## Ticket → PR body checklist

The Reviewer persona will check this at the `Review` gate:

```
## Ticket
[TICKET-ID](https://www.notion.so/<page-id>)

## What changed
<concise summary>

## Acceptance criteria
- [ ] <criterion 1 from PRD>
- [ ] <criterion 2 from PRD>
- ...

## Tests
- <list of test files added/modified>

## Demo
<Cloud Run revision URL, local screenshot, or "N/A — non-runnable">

## Trust budget
- Git refs: <branches, commits>
- Cloud resources: <revisions, IAM, registry>
- Notion edits: <page IDs>
- Files changed: <count or list>
```

## Ticket → Status transitions

| From | To | Trigger |
|---|---|---|
| `Backlog` | `Spec` | PM persona starts the PRD |
| `Spec` | `Planned` | PRD + acceptance criteria signed off by user |
| `Planned` | `In Progress` | Branch created (Dev persona engaged) |
| `In Progress` | `Review` | PR opened, demo URL posted, CI green |
| `Review` | `Done` | PR merged + Cloud Run revision serves traffic (or screenshot ack for non-runnable) |
| any | `Blocked` | Card comment with explicit blocker description |
| `Blocked` | (previous) | Blocker resolved, comment posted |

## Field cheat-sheet

| Notion field | Used for | Notes |
|---|---|---|
| `Feature` (title) | PR title basis | Short imperative |
| `Layer` | Branch prefix + commit scope | One value, mandatory |
| `Category` | Tagging only | New Feature / Bug Fix / Tech Debt / etc. |
| `Priority` | Reviewer escalation | P0 → drop everything; P3 → batch with others |
| `Sprint` | Roadmap visibility | Sprint 1–4 / Icebox |
| `Effort` | Velocity tracking | T-shirt size, no story points |
| `Status` | Phase gate (BMAD) | Drives which persona is allowed to act |
| `Date` | Started / due | Set when entering `Spec`; updated on `Done` |
