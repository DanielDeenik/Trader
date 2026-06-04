# Social Arb — Architecture & Solutioning Doc

This is the living solutioning document for Social Arb. Every architectural decision, feature rationale, and integration choice is recorded here so that any future session has full context.

**Last updated:** 2026-04-01

---

## Current System Architecture

Social Arb implements Chris Camillo's 5-layer cognitive architecture as a 6-agent pipeline with 3 shared services, backed by SQLite (23 tables) and served via FastAPI + React 18.

### Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11+, FastAPI, SQLite (23 tables) |
| Frontend | React 18, Vite, Tailwind CSS v4.2.2 |
| Entry Point | `python -m social_arb.main` → :8000 |
| Data | SQLite with public/private/crypto domain classification |
| Agents | 6 autonomous agents with EventBus pub/sub |

---

## 6-Agent Pipeline

Each agent maps to a layer in Camillo's cognitive model. All agents are dynamic and context-aware — they adapt their parameters in real-time based on pipeline conditions.

| Agent | Layer | Role | Adapts |
|---|---|---|---|
| Sentinel | L0 | Collection orchestration, source freshness | tick_interval (120→15s), stale_threshold (6→1.5h) |
| Assembler | L1→L2 | Signal clustering into mosaics | min_signals (5→2) based on eagerness vs backpressure |
| Strategist | L2→L3 | Mosaic→thesis with conviction scoring | min_coherence (0.6→0.3), min_kelly (0.05→0.01) |
| Gatekeeper | L3→L4 | HITL review queue management | auto_promote_threshold (18→10), poll frequency |
| Executor | L4→L5 | Position lifecycle management | max_allocation_pct (5→2%), tick_interval (180→60s) |
| Supervisor | Meta | Pipeline health + knowledge maintenance | health_check_interval 120s, runs decay/expiry |

**Event flow:** SIGNALS_COLLECTED → MOSAICS_ASSEMBLED → THESES_FORGED → HITL_REQUIRED → DECISIONS_MADE → POSITIONS_UPDATED

---

## 3 Shared Services

These services are wired into every agent via `setup.py` and provide the intelligence layer.

### 1. ContextLayer (`context.py`)

Computes 8 real-time pressure metrics from actual DB state with TTL caching (10s):

- **signal_velocity** — rate of new signals (falling = drought)
- **source_diversity** — how many sources are contributing
- **divergence_pressure** — strength of sentiment divergence
- **divergence_velocity** — acceleration of divergence
- **lifecycle_freshness** — ratio of emerging vs saturated signals
- **pipeline_throughput** — signals→mosaics→theses conversion
- **hitl_backlog** — pending review queue pressure
- **portfolio_heat** — current allocation vs capacity

Agents use `adapt(pressure, calm_value, urgent_value)` to interpolate parameters.

### 2. KnowledgeStore (`knowledge.py`)

3 DB tables for persistent inferred connections:

- **entity_links** — discovered relationships between symbols/entities with strength decay
- **narrative_threads** — storylines that evolve over time with velocity/acceleration
- **research_queue** — hypothesis backlog for continuous investigation

### 3. ResearchOrchestrator (`researcher.py`)

Hypothesis-driven continuous research between batch cycles:

- Sentinel generates **gap_fill** hypotheses (missing source coverage)
- Assembler generates **correlation** hypotheses (shared narratives)
- Strategist generates **contradiction** and **entity_discovery** hypotheses
- Gatekeeper generates **reinforcement** hypotheses (confirming evidence)
- Agents claim and investigate hypotheses during idle ticks

---

## Database Schema (23 Tables)

**Core pipeline:** signals, mosaics, theses, reviews, decisions, positions, portfolio_snapshots

**Collection:** collection_runs, scheduler_config

**Knowledge:** entity_links, narrative_threads, research_queue

**Supporting:** trend_scores, mosaic_signals (junction), position_history, daily_pnl

**Config:** app_config

**Domain classification:** Each signal has `data_class` (public/private) and `domain` (freeform, normalized to public/private/crypto in frontend)

---

## API Surface

| Route Group | Key Endpoints |
|---|---|
| `/api/trends` | Trending tickers, divergence alerts, per-symbol details |
| `/api/agents` | Pipeline status, flow graph, health, context metrics, knowledge summary, event history |
| `/api/pipeline` | Run pipeline, context pressure, pipeline status |
| `/api/signals` | CRUD for raw signals |
| `/api/mosaics` | CRUD for assembled mosaics |
| `/api/theses` | CRUD for investment theses |
| `/api/reviews` | HITL review queue management |
| `/api/decisions` | Decision records |
| `/api/positions` | Portfolio positions |

---

## Frontend Pages

| Page | Route | Purpose |
|---|---|---|
| TrendRadar | `/` | Home — trending tickers, divergence alerts (Gummy Search pattern) |
| SimilarTrends | `/similar-trends` | Theme clusters by sector/vertical |
| TickerTrend | `/ticker/:symbol` | Full ticker deep dive with signal timeline, STEPPS radar |
| Pipeline | `/pipeline` | Agent pipeline dashboard with SVG flow diagram |
| Reviews | `/reviews` | HITL review queue |
| Positions | `/positions` | Active portfolio positions |
| Settings | `/settings` | Configuration |

---

## Architectural Decisions Log

### ADR-001: Pure Orchestration, No LLM Dependencies
**Decision:** Agents use rule-based logic with adaptive thresholds, not LLM calls.
**Rationale:** Predictable costs, deterministic behavior, no API latency in the hot path. LLMs can be added later as an optional enrichment layer.

### ADR-002: Context-Aware Agents via Shared ContextLayer
**Decision:** All agents share a single ContextLayer that queries real DB state.
**Rationale:** Agents need to coordinate without direct coupling. The ContextLayer provides a shared view of pipeline pressure that each agent interprets independently.

### ADR-003: Continuous Research Between Batches
**Decision:** Agents generate and investigate hypotheses during idle ticks.
**Rationale:** Camillo's cognitive model requires continuous background processing — not just batch-triggered reactions. The KnowledgeStore accumulates inferred connections that feed back into the next batch cycle.

### ADR-004: Extension-Only Development
**Decision:** New features must extend existing modules. No parallel rewrites.
**Rationale:** Multiple rewrites created fragmentation — orphaned pages, dead API methods, disconnected routes. Quality criteria (`quality/criteria.md`) enforces this as a blocking check.

### ADR-005: Three-Domain Extension
**Decision:** Same 5-layer topology serves public markets, private companies, and crypto.
**Rationale:** The DB schema already supports domain classification via `data_class` and `domain` columns. Extension = new collectors + domain-specific scoring, not new architecture.

### ADR-006: Gummy Search UI Pattern
**Decision:** Frontend follows trend-first discovery (what's trending → why → act).
**Rationale:** Camillo's process starts with peripheral vision, not stock screening. The UI should mirror this: TrendRadar (what) → TickerTrend (why) → Reviews/Positions (act).

---

## Quality Criteria

All work is evaluated against `quality/criteria.md` before completion. 8 categories:

1. **Extension Integrity** (blocking) — no parallel rewrites
2. **Data Contract Consistency** (blocking) — API shapes match frontend expectations
3. **Agent Pipeline Coherence** (blocking) — all agents wired correctly
4. **Frontend-Backend Alignment** (blocking) — every page has working API routes
5. **Memory & Context Persistence** (warning) — auto-memory and Notion updated
6. **No Regression** (blocking) — app starts, endpoints return 200, frontend builds
7. **Code Hygiene** (warning) — no dead imports, no print(), no dead API methods
8. **Documentation Trail** (warning) — docstrings, commit messages, this doc

---

## Known Issues & Tech Debt (as of 2026-04-01)

- ~~18 unused API client methods in `api.js`~~ **FIXED** — cleaned to 28 active methods
- Orphaned `/overview` page not linked in navigation (will be wired to Portfolio tab in Slice 4)
- Some data collectors stale (SEC EDGAR 5d, Twitter 4d, GitHub 2d)
- Duplicate CLAUDE.md content between Social Arb/ and Trader/ roots
- Value normalization inconsistency: DB stores coherence/divergence as both 0-1 and 0-100
- Knowledge tables (entity_links, narrative_threads, research_queue) defined in knowledge.py, not consolidated in schema.py

---

### ADR-007: Knowledge Weaver as 7th Agent
**Decision:** Add Knowledge Weaver as an independent 7th agent for entity extraction, graph construction, and narrative threading.
**Rationale:** Operates orthogonally to the existing 6-agent pipeline. Uses LightRAG incremental approach. Publishes `KNOWLEDGE_UPDATED` events. Extends existing KnowledgeStore tables.

### ADR-008: Hybrid Navigation — Option C
**Decision:** Top tabs (Discover/Investigate/Review/Portfolio) + contextual layer sidebar + slide-out Knowledge Graph panel.
**Rationale:** Balances discovery-first (ADR-006) with power-user pipeline access. HITL Review prominent with live badge. Knowledge Graph accessible from any page.

---

## Roadmap: Vertical Slices (as of 2026-04-01)

Full spec: `Social Arb/DESIGN-SPEC-v1.md`

| Slice | Name | Est. | Dependencies |
|-------|------|------|-------------|
| 1 | Knowledge Weaver Foundation + Knowledge Feed | 2-3 wk | — |
| 2 | Enhanced HITL Review | 1-2 wk | Slice 1 |
| 3 | Reddit Deep + Discord Collector | 1-2 wk | Independent |
| 4 | Hybrid Navigation + Graph Panel | 2-3 wk | Slice 1 |
| 5 | LinkedIn + Investigate Deep Dive | 2 wk | Slices 1, 4 |
| 6 | Containerized Domains (Public/Private/Crypto) | 2 wk | Slice 1 |

**Total: 10-14 weeks solopreneur pace**
