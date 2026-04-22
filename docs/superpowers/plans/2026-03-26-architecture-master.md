# Social Arb v2 — Master Architecture

> **For agentic workers:** This is the master architecture document. Each phase has its own implementation plan. Use superpowers:subagent-driven-development or superpowers:executing-plans to implement each phase.

**Goal:** Transform Social Arb from a CLI+Streamlit prototype into a production FastAPI+Next.js application with full ML pipeline, queue-based resilience, and dynamic ticker management.

**Architecture:** FastAPI backend exposes REST endpoints that orchestrate all 6 existing engines + new STEPPS ML pipeline. Next.js frontend provides the interactive HITL workflow (not a dashboard). Python asyncio+threading handles background collection and ML training. SQLite for dev, PostgreSQL for production — no change to the existing dual-backend adapter.

**Tech Stack:** FastAPI, Next.js 14 (App Router), Tailwind CSS, Plotly.js, SQLite/PostgreSQL, scikit-learn, asyncio, existing 6 collectors + 6 engines

---

## What Exists Today (Inventory)

### Backend — PRODUCTION READY
| Component | Status | Files |
|-----------|--------|-------|
| 5-layer topology engine | Complete | `core/topology.py` (489 lines) |
| Protocol interfaces (7 protocols) | Complete | `core/protocols.py` (346 lines) |
| 12-table schema (SQLite + PostgreSQL) | Complete | `db/schema.py` (452 lines) |
| Dual-backend adapter | Complete | `db/adapter.py` (159 lines) |
| Data store (all CRUD) | Complete | `db/store.py` (473 lines) |
| Sentiment divergence engine | Complete, wired into pipeline | `engine/sentiment_divergence.py` |
| Kelly criterion sizer | Complete, wired into pipeline | `engine/kelly_sizer.py` |
| IRR/MOIC simulator | Complete, **NOT wired** | `engine/irr_simulator.py` |
| Regulatory moat scorer | Complete, **NOT wired** | `engine/regulatory_moat.py` |
| Technical analyzer (7 indicators) | Complete, **NOT wired** | `engine/technical_analyzer.py` |
| Cross-domain amplifier | Complete, **NOT wired** | `engine/cross_domain_amplifier.py` |
| Batch pipeline (signals→mosaics→theses) | Complete | `pipeline.py` (250 lines) |
| CLI (collect, analyze, review, status, backfill) | Complete | `cli.py` (436 lines) |

### Collectors — ALL REAL DATA, NO STUBS
| Collector | Source | Mapped Entities | Auth |
|-----------|--------|----------------|------|
| YFinance | Market data + OHLCV | All public tickers | None |
| Reddit | Social sentiment | 7 subreddits | None (JSON API) |
| SEC EDGAR | Institutional filings | 10 CIKs hardcoded | None |
| Google Trends | Search interest | Any keyword | None (pytrends) |
| GitHub | Engineering velocity | 10 orgs mapped | Optional token |
| CoinGecko | Crypto prices + market data | 10 tokens mapped | None (rate-limited) |
| DeFi Llama | Protocol TVL | 10 protocols mapped | None |

### Database State (current)
- 114 signals, 10 mosaics, 7 theses, 2,326 OHLCV bars, 1 scan
- 0 reviews, 0 positions, 0 decisions (HITL gates not yet used)

---

## Architecture: What Changes

```
CURRENT                         TARGET
───────                         ──────
CLI → pipeline.py → DB          FastAPI → orchestrator → engines → DB
Streamlit → DB (direct)         Next.js → FastAPI REST API → DB
No background tasks             asyncio task queue + worker threads
2 engines wired                 All 6 engines + STEPPS auto-run
Hardcoded ticker lists          Dynamic instruments table + UI CRUD
No error recovery               Queue-based retry + staleness tracking
No ML                           STEPPS classifier + LLM seeding
```

### System Diagram

```
┌─────────────────────────────────────────────────────────┐
│                    NEXT.JS FRONTEND                      │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐│
│  │Ticker│ │Signal│ │Mosaic│ │Thesis│ │Decide│ │Portfo││
│  │Mgmt  │ │Radar │ │Cards │ │Forge │ │Gates │ │lio   ││
│  └──┬───┘ └──┬───┘ └──┬───┘ └──┬───┘ └──┬───┘ └──┬───┘│
└─────┼────────┼────────┼────────┼────────┼────────┼─────┘
      │        │        │        │        │        │
      ▼        ▼        ▼        ▼        ▼        ▼
┌─────────────────────────────────────────────────────────┐
│                    FASTAPI BACKEND                        │
│                                                          │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────┐ │
│  │ REST API     │  │ Orchestrator │  │ Task Queue     │ │
│  │ /api/v1/...  │  │ (auto-stack) │  │ (asyncio)      │ │
│  └──────┬──────┘  └──────┬───────┘  └───────┬────────┘ │
│         │                │                    │          │
│  ┌──────┴────────────────┴────────────────────┴───────┐ │
│  │                    ENGINE LAYER                      │ │
│  │  sentiment │ kelly │ irr │ moat │ tech │ xdomain   │ │
│  │  divergence│ sizer │ sim │ scorer│ anal │ amplifier │ │
│  │            │       │     │      │      │           │ │
│  │  ┌─────────────────────────────────────┐           │ │
│  │  │ STEPPS ML (NEW)                     │           │ │
│  │  │ LLM seed → classifier → HITL refine │           │ │
│  │  └─────────────────────────────────────┘           │ │
│  └────────────────────────┬───────────────────────────┘ │
│                           │                              │
│  ┌────────────────────────┴───────────────────────────┐ │
│  │                 COLLECTOR LAYER                      │ │
│  │  yfinance│reddit│sec_edgar│trends│github│coingecko │ │
│  │  defillama│ (NEW: crunchbase, linkedin, patents)    │ │
│  └────────────────────────┬───────────────────────────┘ │
│                           │                              │
│  ┌────────────────────────┴───────────────────────────┐ │
│  │               DB LAYER (unchanged)                  │ │
│  │  adapter.py → schema.py → store.py                  │ │
│  │  SQLite (dev) │ PostgreSQL (prod)                   │ │
│  └────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

---

## Phase Breakdown

### Phase 1: FastAPI Backend + Full Engine Wiring
**Depends on:** Nothing (foundation)
**Produces:** REST API that the frontend (or any client) can call
**Key deliverables:**
- FastAPI app with versioned REST endpoints (`/api/v1/`)
- Orchestrator that auto-runs ALL 6 engines when a signal is promoted
- Dynamic instrument management (CRUD on instruments table)
- Data freshness tracking per source per ticker
- All existing CLI commands exposed as API endpoints
- Proper error responses with structured error types

### Phase 2: Next.js Frontend Shell
**Depends on:** Phase 1 (API endpoints)
**Produces:** Interactive HITL workflow application (NOT a dashboard)
**Key deliverables:**
- Next.js 14 App Router project in `frontend/`
- Ticker management page (add/remove/search)
- Per-ticker deep dive with all engine outputs
- HITL gate pages with scoring + narrative
- Real-time data freshness indicators
- Dark theme matching current design system

### Phase 3: Task Queue + Collector Resilience
**Depends on:** Phase 1 (API structure)
**Produces:** Background workers, retry logic, staleness tracking
**Key deliverables:**
- asyncio task queue with worker threads
- Job types: collect, analyze, backfill, train_ml
- Exponential backoff retry (3 attempts per job)
- Per-source health status (green/yellow/red)
- Scheduled collection intervals
- Task status API for frontend polling

### Phase 4: STEPPS ML Pipeline
**Depends on:** Phase 1 (engine layer), Phase 3 (task queue for training)
**Produces:** Automated STEPPS scoring on every signal
**Key deliverables:**
- STEPPS schema extension (6 dimensions per signal)
- LLM seeding endpoint (Claude API labels first N signals)
- scikit-learn multi-output classifier
- Training pipeline (triggered by task queue)
- HITL correction loop (your gate scores feed back as training data)
- Weekly auto-retrain on accumulated corrections

### Phase 5: Private Company Intelligence Stack
**Depends on:** Phase 1 (collector architecture)
**Produces:** Full signal coverage for private companies
**Key deliverables:**
- Hiring velocity collector (job board scraping)
- Patent filing collector (USPTO/EPO)
- Web traffic proxy (SimilarWeb or similar)
- App store ranking collector
- News/PR monitoring collector
- Glassdoor sentiment collector
- Extended GitHub collector (commit frequency, contributor growth)

### Phase 6: Production Hardening
**Depends on:** All prior phases
**Produces:** Deployable, monitored, tested application
**Key deliverables:**
- Docker Compose for local dev (API + frontend + DB)
- GCP Cloud Run deployment (API) + Vercel (frontend)
- Comprehensive test suite (unit + integration + E2E)
- Monitoring: structured logging, error tracking, health checks
- Rate limiting on API endpoints
- API authentication (JWT for future multi-user)

---

## Design Decisions

### 1. Keep the existing DB layer unchanged
The `adapter.py` + `schema.py` + `store.py` stack works. FastAPI will import and call these functions directly. No ORM. No migration tool. Just SQL.

### 2. Orchestrator pattern, not microservices
Single FastAPI process. The orchestrator is a Python class that chains engine calls in sequence. No message bus, no separate services. Solopreneur stack.

### 3. Frontend fetches, backend computes
Next.js makes REST calls. All computation happens in FastAPI. The frontend is purely presentation + HITL input collection. No business logic in JS.

### 4. STEPPS is a first-class engine
STEPPS gets the same protocol interface as the other 6 engines. It plugs into the orchestrator identically. The only difference: it has a training loop.

### 5. Dynamic tickers via instruments table
The `instruments` table already exists but is empty. Phase 1 populates it from config.py defaults and exposes CRUD. Auto-lookup for CIK (SEC), CoinGecko ID, GitHub org when adding a ticker.

### 6. CLI stays
The CLI continues to work alongside FastAPI. Both call the same store/pipeline/engine functions. The CLI is your escape hatch when the UI is down.

---

## File Structure (New + Modified)

```
social_arb/
├── api/                          # NEW — FastAPI application
│   ├── __init__.py
│   ├── main.py                   # FastAPI app factory, middleware, CORS
│   ├── deps.py                   # Dependency injection (db, config)
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── instruments.py        # CRUD for ticker universe
│   │   ├── signals.py            # Signal queries + collection triggers
│   │   ├── mosaics.py            # Mosaic queries
│   │   ├── theses.py             # Thesis queries + engine outputs
│   │   ├── reviews.py            # HITL gate submissions
│   │   ├── positions.py          # Portfolio management
│   │   ├── tasks.py              # Task queue status + triggers
│   │   └── health.py             # Health checks + data freshness
│   ├── orchestrator.py           # NEW — auto-stack engine runner
│   └── schemas.py                # Pydantic request/response models
│
├── engine/
│   ├── stepps_classifier.py      # NEW — STEPPS ML pipeline
│   └── (existing engines unchanged)
│
├── collectors/
│   ├── hiring_collector.py       # NEW (Phase 5)
│   ├── patent_collector.py       # NEW (Phase 5)
│   └── (existing collectors unchanged)
│
├── tasks/                        # NEW — async task queue
│   ├── __init__.py
│   ├── queue.py                  # Task table + worker loop
│   ├── workers.py                # Job handlers (collect, analyze, train)
│   └── scheduler.py              # Interval-based task creation
│
├── core/                         # UNCHANGED
├── db/                           # UNCHANGED (schema gets instruments seed)
├── app/                          # DEPRECATED (Streamlit — kept for reference)
├── cli.py                        # UNCHANGED (still works)
├── config.py                     # MINOR: add API_PORT, CORS_ORIGINS
└── pipeline.py                   # MODIFIED: call all 6 engines

frontend/                         # NEW — Next.js 14 application
├── package.json
├── next.config.js
├── tailwind.config.js
├── app/
│   ├── layout.tsx                # Root layout + sidebar nav
│   ├── page.tsx                  # Overview
│   ├── tickers/
│   │   ├── page.tsx              # Ticker universe management
│   │   └── [symbol]/page.tsx     # Per-ticker deep dive
│   ├── signals/page.tsx          # L1 Signal Radar
│   ├── gates/
│   │   ├── triage/page.tsx       # Gate 1→2
│   │   ├── validation/page.tsx   # Gate 2→3
│   │   └── conviction/page.tsx   # Gate 3→4
│   ├── mosaics/page.tsx          # L2 Mosaic Assembly
│   ├── theses/page.tsx           # L3 Thesis Forge
│   ├── decisions/page.tsx        # L4 Decision Log
│   ├── portfolio/page.tsx        # L5 Portfolio
│   └── tasks/page.tsx            # Task queue status
├── components/
│   ├── charts/                   # Plotly.js chart components
│   ├── gates/                    # HITL scoring + narrative forms
│   └── layout/                   # Sidebar, header, status bar
└── lib/
    └── api.ts                    # Typed API client
```

---

## Implementation Order

```
Phase 1 ──────────────────────────────────────────►
         FastAPI + engine wiring + instruments CRUD
         ├── Plan: 2026-03-26-phase1-fastapi-backend.md

Phase 2 ─────────────────────────────────────────►
         Next.js frontend (depends on Phase 1 API)
         ├── Plan: TBD

Phase 3 ──────────────────────────────►
         Task queue + resilience
         ├── Plan: TBD

Phase 4 ─────────────────────►
         STEPPS ML pipeline
         ├── Plan: TBD

Phase 5 ─────────────────────────────────►
         Private company collectors
         ├── Plan: TBD

Phase 6 ─────────────────►
         Production hardening
         ├── Plan: TBD
```

Phase 1 is the critical path. Everything else depends on it.
