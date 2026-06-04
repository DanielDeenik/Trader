# Social Arb — Quality Criteria

Every task must be evaluated against these criteria before marking complete.
Severity levels: **blocking** (must fix) and **warning** (should fix, can defer with rationale).

---

## 1. Extension Integrity (blocking)

- [ ] New feature extends existing modules — no parallel rewrites of working code
- [ ] Existing API routes, DB tables, and frontend pages remain functional after changes
- [ ] No orphaned files created (unused components, dead imports, disconnected routes)
- [ ] Import paths resolve correctly across the full dependency chain

## 2. Data Contract Consistency (blocking)

- [ ] API response shapes match what the frontend expects (check `api.js` client methods)
- [ ] DB column names used in queries match actual schema (run `PRAGMA table_info`)
- [ ] Value ranges are consistent: coherence/divergence normalized to 0–1 before frontend display
- [ ] Domain normalization applied: DB domains mapped to `public` / `private` / `crypto` for frontend

## 3. Agent Pipeline Coherence (blocking)

- [ ] All 6 agents initialize in `setup.py` with `.ctx`, `.knowledge`, `.researcher` wired
- [ ] EventBus subscriptions match published event types (no orphaned listeners)
- [ ] `adapt_params()` stores result in `self.metrics.last_adapted_params`
- [ ] Research mode (hypothesis generation/investigation) runs only during idle ticks, not during batch processing

## 4. Frontend–Backend Alignment (blocking)

- [ ] Every frontend page has corresponding API routes that return data
- [ ] No hardcoded mock data in production components
- [ ] Loading and error states handled for every API call
- [ ] Route definitions in `App.jsx` match sidebar navigation links

## 5. Memory & Context Persistence (warning)

- [ ] Auto-memory updated when new architectural decisions are made
- [ ] CLAUDE.md terms table updated when new domain concepts are introduced
- [ ] Notion product solutioning doc updated with feature rationale and decisions
- [ ] No duplicated context across CLAUDE.md files (Social Arb vs Trader)

## 6. No Regression (blocking)

- [ ] Application starts without errors: `python -m social_arb.main` serves at :8000
- [ ] All existing API endpoints return 200 (spot-check: `/api/trends`, `/api/agents/status`, `/api/pipeline/context`)
- [ ] Frontend builds without warnings: `npm run build` exits 0
- [ ] SQLite DB initializes all tables on fresh start (no missing table errors)

## 7. Code Hygiene (warning)

- [ ] No unused imports in modified files
- [ ] No `print()` statements left in production code (use `logger`)
- [ ] API client methods in `api.js` match actual backend routes (no dead methods)
- [ ] Config values have sensible defaults and can be overridden via environment variables

## 8. Documentation Trail (warning)

- [ ] New endpoints documented in route file docstrings
- [ ] Agent behavior changes reflected in module-level docstrings
- [ ] Breaking changes noted in commit message
- [ ] Product decisions traceable to Notion solutioning doc

---

## How to Use

Before marking any task complete:

1. Run through each **blocking** criterion relevant to the change
2. Fix any blocking failures before proceeding
3. Log any **warning** items as follow-up tasks if not addressed immediately
4. Reference this file in commit messages when relevant: `quality: checked against criteria.md`
