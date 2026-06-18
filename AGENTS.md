# Agent Instructions

AI assistants (Claude Code, Cursor, Aider, OpenCode, etc.) reading this
repo: **this is your first-contact protocol.** Do not skip.

`CLAUDE.md` is Dan's personal memory (people, projects, terms). Read it
for context. **This file (`AGENTS.md`) is the operating protocol.**

## On every new session, before anything else

1. **Fetch + identify the truth.**
   ```bash
   git fetch origin
   git log origin/main --oneline -5
   git status
   ```
   If your local `main` is more than a few commits behind `origin/main`,
   stop and ask the user before proceeding. Do **NOT** brainstorm
   against stale state. (This single step would have prevented the
   2026-04-21 client_dashboard incident.)

2. **Read `REPO_CONTEXT.md`.** Know what this repo IS and IS NOT
   before proposing anything.

3. **Read `BMAD.md` and `KANBAN.md`.** Understand which phase you're
   operating in, which persona owns it, and how tickets map to code.

4. **Identify the active ticket.** No work without a ticket.
   - If the user names a ticket ID, fetch it from Notion.
   - If the user describes a feature with no ticket, your first job is
     to create a `Backlog` card and ask which phase to enter.

5. **Pick the right persona.** Check `.claude/agents/` for the persona
   matching the ticket's current Status. You are bound to **one
   persona per turn**. Do not skip phases.

## Hard rules

- **Never edit files outside the scope of the active ticket's persona.**
  PM only writes `docs/specs/`, Dev never edits `docs/specs/`, etc.
- **Never push to `main` directly** — always via PR.
- **Never `git commit --amend` an already-pushed commit.**
- **Never run destructive `git`, `gcloud`, or Notion ops** (force push,
  reset --hard, branch -D, service delete, page delete) **without
  explicit user authorization in the same turn.**
- **Always end your turn with a trust-budget report:**
  - Git refs touched
  - Cloud resources touched (Cloud Run, IAM, Artifact Registry, Cloud SQL)
  - Notion edits (page IDs)
  - Files changed (paths)

## Common pitfalls (lessons logged from past sessions)

| Pitfall | Cause | Prevention |
|---|---|---|
| Working off an orphan local branch | Skipped `git fetch origin` | Step 1 above, mandatory |
| Merging a wrong-repo artefact into `main` | No `REPO_CONTEXT.md` scope check | Step 2 above + Reviewer's scope check |
| Phase skipping ("just make it green") | Convenience under time pressure | Phase gates in `BMAD.md` |
| Silent side-quests / scope creep | No ticket discipline | "No work without a ticket" |
| Surprising the user with damage | No trust-budget reporting | Mandatory end-of-turn report |

## When in doubt

Read `REPO_CONTEXT.md` again, then ask the user. Do not improvise.

## Tooling expectations

This repo's AI workflow assumes:

- **Notion MCP** for Kanban reads/writes
- **Claude Code** (or compatible) for persona invocation
- **VoiceInk** (optional) for Backlog capture from voice
- **gh CLI** for PRs
- **gcloud** for Cloud Run operations

If a tool is missing, say so explicitly — do not silently work around it.
