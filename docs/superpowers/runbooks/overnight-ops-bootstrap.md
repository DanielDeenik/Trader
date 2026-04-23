# Overnight-Ops Bootstrap Runbook

**Problem:** The overnight-ops skill (`anthropic-skills:overnight-ops`) has been blocked for 11+ consecutive cycles. Root causes observed across sessions:

1. `.git/HEAD.lock` / `.git/index.lock` — sandbox user cannot `rm`, host must clean.
2. Missing dev dependencies — sandbox-Python lacks FastAPI, SQLAlchemy, transformers, vaderSentiment, pytest-asyncio, etc. Bootstrapping them over the network inside the sandbox stalls.
3. Missing runtime data — `data/social_arb.db` is absent; collectors need credentials.
4. Missing MCP server — the `social_arb_run_pipeline` tool (referenced in the skill's Phase 1) is not in Claude's available tools list. Only the generic Notion MCP is present.
5. Branch drift — Claude sessions clone into a worktree rooted on an orphan initial-commit chain, not on `origin/main`.

This runbook is the one-time host-side setup Dan runs so future overnight cycles succeed. Once these boxes are checked, the `anthropic-skills:overnight-ops` skill can run a full 5-phase cycle autonomously from any Claude session with worktree access to a properly-bootstrapped checkout.

---

## Pre-flight — do this **once**, from Dan's host terminal

```bash
# 1. Clear any stale git lockfiles (the 11-cycle blocker)
cd "$HOME/Projects/Trader"   # or wherever the canonical Social Arb checkout lives
rm -f .git/HEAD.lock .git/index.lock .git/refs/heads/*.lock
git status   # must succeed, must print clean/dirty status

# 2. Confirm branch state
git fetch origin
git log --oneline origin/main -5
# expected: 7f861e6e, e87980cb, d6a389b0 near the top

# 3. Verify a clean main exists locally
git checkout main
git pull --ff-only origin main

# 4. Create (or update) a dedicated venv on Python 3.11+
python3.11 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip setuptools wheel
```

---

## Install the full runtime + dev stack

```bash
# 5. Runtime deps from requirements.txt
pip install -r requirements.txt

# 6. Dev / test deps — install beyond requirements.txt
pip install \
    pytest pytest-asyncio pytest-mock \
    fastapi 'uvicorn[standard]' gunicorn \
    sqlalchemy alembic \
    vaderSentiment \
    httpx \
    'transformers>=4.30' 'torch>=2.0'  # optional — needed for FinBERT sentiment tests

# 7. Install the package itself editable-mode (enables `social-arb` CLI + `import social_arb`)
pip install -e .

# 8. Sanity check
which social-arb
python -c "import social_arb; print(social_arb.__file__)"
social-arb --help
```

---

## Seed the database + env

```bash
# 9. Initialise the DB schema (creates data/social_arb.db if missing)
mkdir -p data
python -c "from social_arb.db.schema import init_db; from social_arb.config import config; init_db(config.db_path); print(f'DB ready at {config.db_path}')"

# 10. Create a local .env file from .env.example if present, otherwise populate:
cat > .env <<'EOF'
SOCIAL_ARB_DB=./data/social_arb.db
LOG_LEVEL=info
LOG_FORMAT=json
PORT=8000
WEB_CONCURRENCY=1
CORS_ORIGINS=http://localhost:3000,http://localhost:8000

# Collectors — fill in what you have; absent keys are skipped
REDDIT_CLIENT_ID=
REDDIT_CLIENT_SECRET=
REDDIT_USER_AGENT=social-arb/1.0
COINGECKO_API_KEY=
YF_NO_KEY_NEEDED=true

# Notion (for Daily Brief writeback)
NOTION_TOKEN=
NOTION_ROOT_PAGE_ID=3127772f-a7ae-8164-a661-fb85c6dad3c9

# OpenAI (for agent prompts — optional)
OPENAI_API_KEY=
EOF

# 11. Load it
set -a && source .env && set +a
```

---

## Verify the test suite passes

```bash
# 12. Run the curated offline CI suite first
bash scripts/test-ci.sh
# expected: exits 0, prints "PASSED" for each group

# 13. Run the full suite
python -m pytest tests/ -v --tb=short
# record the baseline: Daily Brief reported 249 passed / 2 skipped on 2026-04-21
```

If step 13 doesn't match the 249/2 baseline, stop and investigate before letting overnight-ops build anything — the skill's guardrails require an equal-or-better post-change count.

---

## Verify the stack runs

```bash
# 14. Start the API in one terminal
bash scripts/run.sh
# expected: "Starting Social Arb API on port 8000"
# then in another terminal:
curl -sS http://localhost:8000/api/v1/health | jq .
# expected: {"status":"ok", …}

# 15. Start the frontend (separate terminal, from repo root)
cd frontend && npm install && npm run dev
# expected: "Local: http://localhost:3000/"
# open it, verify Overview page renders and talks to :8000
```

---

## Wire the Social Arb MCP server (unlocks COLLECT phase)

The overnight-ops skill's Phase 1 wants a tool named `social_arb_run_pipeline`. Today, Claude sessions only see the Notion MCP — so the pipeline is invoked via CLI fallback (`social-arb collect && social-arb analyze`). To enable the direct MCP path, register a local Social Arb MCP server with Claude:

```bash
# 16. If the repo ships an MCP server entry (check for mcp/ or social_arb/mcp/):
ls social_arb/mcp* mcp* 2>/dev/null

# 17. If present, register with Claude's MCP config:
#     ~/.claude.json or ~/Library/Application Support/Claude/claude_desktop_config.json
#     Add under "mcpServers":
#     "social_arb": {
#         "command": "python",
#         "args": ["-m", "social_arb.mcp.server"],
#         "env": { "SOCIAL_ARB_DB": "/absolute/path/to/data/social_arb.db" }
#     }
# Restart Claude. Confirm `social_arb_*` tools appear in the tool list.

# 18. If no MCP server exists yet, file a backlog card:
#     "Social Arb MCP Server — expose run_pipeline/query_signals/query_mosaics via MCP"
#     P1 · M · L0 Infrastructure
# Until shipped, overnight-ops uses the CLI path.
```

---

## Give Claude a worktree rooted on origin/main

The orphan-history problem (this session) happened because a worktree was created off a disjoint local `main` that had never tracked `origin/main`. To prevent recurrence:

```bash
# 19. From the canonical checkout (./Trader on main):
git worktree add -b claude/overnight-YYYY-MM-DD \
    /tmp/trader-claude-overnight-YYYY-MM-DD \
    origin/main

# 20. Start the Claude session in that path. From there:
#     - `git log` shows origin/main's real history
#     - New branches are based on origin/main
#     - PRs open without "unrelated histories"

# 21. When the session ends, discard:
cd "$HOME/Projects/Trader"
git worktree remove /tmp/trader-claude-overnight-YYYY-MM-DD
git branch -D claude/overnight-YYYY-MM-DD   # if you don't want it
```

---

## Green-light checklist (what "ready for overnight-ops" means)

Before asking Claude to "build all night based on the backlog," confirm every box:

- [ ] `git status` clean, no `.lock` files in `.git/`
- [ ] Current checkout is at `origin/main` HEAD (not an orphan)
- [ ] `.venv` active, `which python` points inside it
- [ ] `python -m pytest tests/ -q` reports ≥ 249 passed
- [ ] `scripts/run.sh` starts the API, `/api/v1/health` returns 200
- [ ] `frontend/` builds (`npm run build`)
- [ ] `data/social_arb.db` exists and is populated (at least one scan done)
- [ ] `.env` loaded with at least the Notion token (so Daily Brief can post)
- [ ] Claude session is running in a worktree off `origin/main`
- [ ] (Optional) `social_arb_*` MCP tools visible in Claude's tool list

When all boxes check, launch the `anthropic-skills:overnight-ops` skill. The first full cycle should complete within 2–4 hours and leave behind:
- A morning Daily Brief page under the Social Arb Research Hub.
- One backlog item advanced from Backlog → Done (or → Blocked with reasons).
- One optimization commit on the `overnight/YYYY-MM-DD-*` branch, opened as a PR.
- Zero modifications to `main` until a PR is reviewed.

---

## Known gaps to close (ticket these)

1. **Add `requirements-dev.txt`** (or `pyproject.toml` `[project.optional-dependencies].dev`) that pins all test/dev deps. Eliminates the ad-hoc pip list above.
2. **Ship the Social Arb MCP server** (backlog item exists: `33d7772f-a7ae-8193-bf24-d4c985d83e75` — *MCP Tool Integration*, P2, L, Sprint 3).
3. **Automate the green-light check** as `make overnight-ready` so Dan runs one command before handoff.
4. **`.env.example`** — commit a redacted template so new checkouts don't guess at var names.
5. **Document the worktree launch** in CLAUDE.md so future sessions default to the correct path.
