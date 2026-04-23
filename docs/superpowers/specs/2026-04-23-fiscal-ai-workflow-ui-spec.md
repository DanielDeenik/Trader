# Social Arb — Fiscal.ai-Style Workflow UI Redesign

**Date:** 2026-04-23
**Owner:** Dan Deenik
**Status:** Draft — awaiting approval before implementation
**Repo:** `danieldeenik/Trader`, branch `overnight/2026-04-23-backlog`
**Related backlog items (already queued):**
- `33d7772f-a7ae-812d-8f1c-dac0ff4b34fc` — **Commitment Pipeline UI — Visual funnel showing decisions at each stage with gate controls** (P1, L, Frontend)
- `33d7772f-a7ae-8167-989a-f897ba78a1cd` — **Knowledge Graph Visualization — Bloomberg UI** (P2, L, Frontend)
- `33d7772f-a7ae-81f9-a675-fe1a8231906c` — **Event-Driven Run Bus — Pub-sub for agent coordination + UI streaming** (L0, backend dependency)
- `33d7772f-a7ae-81e0-ae89-cb9ca876215e` — **Commitment Pacing Metrics — Velocity / burn / exposure dashboards**
- `3317772f-a7ae-81cb-b0d3-e4160e32e367` — **Code Splitting & Bundle Optimization**
- `3317772f-a7ae-81da-b3ec-ea06876fb618` — **Mobile Responsive UI**

---

## 1. Context — what already exists

### Stack (`frontend/package.json`)
- React 18 + Vite 5 + React Router 6
- `@xyflow/react` 12 (already installed — node/edge graph viz for workflow + KG)
- `recharts` 2 (ticker trends, pacing, signal charts)
- **No** Tailwind, shadcn, or design system. Plain CSS with CSS variables in `frontend/src/styles/index.css`.
- **Inconsistency:** Multiple `.jsx` files use `className="flex items-center …"` as if Tailwind were installed. Those classes are currently **dead** — they render as literal strings with no matching stylesheet. This must be fixed as part of this redesign (either add Tailwind or replace with CSS module classes).

### Routing (`frontend/src/App.jsx`) — 5-layer skeleton already exists

| Route | Page | Maps to |
| --- | --- | --- |
| `/` | `Overview` | Dashboard home |
| `/tickers` | `Tickers` | Symbol list |
| `/tickers/:symbol` | `TickerDetail` | Per-ticker summary |
| `/deepdive/:symbol` | `DeepDive` | 4-panel research view (backlog item marked Done) |
| `/lattice/:symbol` | `LatticeGraph` | Per-ticker knowledge graph |
| `/mosaic/:symbol` | `MosaicWorkbench` | Per-ticker mosaic assembly |
| `/signals` | `SignalRadar` | **L1 Peripheral Vision** |
| `/mosaics` | `MosaicCards` | **L2 Mosaic Assembly** |
| `/theses` | `ThesisForge` | **L3 Asymmetry Filter** |
| `/gate/review` | `GateReview` | **HITL gate** |
| `/decisions` | `Decisions` | **L4 Timing Calibration** |
| `/positions` | `Positions` | **L5 Conviction Sizing** |
| `/tasks` | `TaskQueue` | Agent task list |
| `/settings` | `Settings` | Config |

### Existing components
`AlertBell`, `AlertToast`, `DecisionButton`, `EngineCard`, `Header`, `Layout`, `ScoreSlider`, `Sidebar`, `StatusBar`, `SymbolLink`.

### Existing CSS variables (`frontend/src/styles/index.css`)
```css
--color-bg-primary: #111827   (near-black slate)
--color-bg-secondary: #1f2937
--color-bg-tertiary: #374151
--color-text-primary: #f9fafb
--color-text-secondary: #d1d5db
--color-accent-success: #10b981
--color-accent-warning: #f59e0b
--color-accent-error: #ef4444
--color-accent-info: #3b82f6
body: ui-monospace stack
```

### Existing API surface (`social_arb/api/` routes)
`/alerts`, `/alerts/thresholds`, `/auth/*`, `/auth/watchlist`, `/signals`, `/signals/grouped`, `/reviews`, `/tasks`, `/source-health`, `/analyze`. No streaming endpoint yet — the Run Bus backlog item will add it.

---

## 2. Goals

What "fiscal.ai + ticker trends + workflow UI" means, concretely:

1. **Fiscal.ai aesthetic** — clean, dense, fast. Dark base, single accent, Inter + JetBrains Mono. Ubiquitous ticker chips with hover sparklines. `Cmd+K` command palette for symbol search. Tabbed deep-ticker pages.
2. **Ticker trends** — every page that cares about a symbol renders a recharts sparkline/chart. The symbol → its signal divergence → its thesis → its lifecycle stage is traceable in one click.
3. **Workflow-based** — a first-class **Pipeline** view showing the L1→L5 cognitive topology as a live `@xyflow/react` graph. Cards move between stages in real time, powered by the Run Bus event stream. Agents appear as animated nodes; signals flow as edges.
4. **HITL-first** — the Gate Review page is promoted from "operations" sub-nav to a top-level queue with a **badge count** in the sidebar and a **`g h` keyboard shortcut**. When Claude-in-the-loop asks a question, it shows as a modal-style card with accept / defer / escalate buttons, full context on the card (mosaic, thesis, divergence, coherence, lifecycle), and a decision journal entry on action.
5. **Knowledge graph** — per-symbol and global graph views using `@xyflow/react`, bound to the Entity Network from the KG Visualization backlog item. Clickable nodes drill into entity pages.
6. **One design language** everywhere. Fix the dead Tailwind classes. Establish tokens. Every new page uses the same `<PageHeader>`, `<Panel>`, `<MetricTile>`, `<TickerChip>`, `<TimeScope>` primitives.

---

## 3. Non-goals (defer to later specs)

- **Mobile responsive layout** — already a backlog item (`3317772f-a7ae-81da-b3ec-ea06876fb618`). Desktop-first in this spec.
- **Real-time sub-second updates.** Phase 1 polls `/api/v1/*` every 30s; Phase 3 swaps to SSE/WebSocket **after** the Run Bus ships.
- **Authenticated collaboration features** (comments, @-mentions on theses).
- **Theming switcher** (light mode) — dark only in v1.
- **Chart annotations beyond event markers** — start with clean recharts.
- **Moving to Next.js / SSR** — Vite SPA stays.

---

## 4. Design decisions

### D1. Add Tailwind 3 + tokens
The current codebase already uses Tailwind-style class strings — they just don't render. Rather than rip every `className` out, install `tailwindcss` + `postcss` + `autoprefixer` and configure `tailwind.config.js` to extend the existing CSS variables. This makes the dead classes live and preserves existing work.

Tokens (`tailwind.config.js → theme.extend`):
```
colors:
  surface:    { 0: #0a0e17, 1: #111827, 2: #1f2937, 3: #374151 }
  text:       { primary: #f9fafb, secondary: #d1d5db, muted: #9ca3af }
  accent:
    success: #10b981  warn: #f59e0b  error: #ef4444  info: #3b82f6
  signal:   (per-source) reddit #ff4500 / google #4285f4 / yf #7c3aed / sec #10b981 / crypto #f59e0b
fontFamily:
  sans: Inter, ui-sans-serif
  mono: JetBrains Mono, ui-monospace
borderRadius: xl: 0.75rem, 2xl: 1rem
boxShadow: panel: 0 1px 0 0 rgba(255,255,255,0.04) inset, 0 0 0 1px rgba(255,255,255,0.06)
```
Keep the existing `--color-*` CSS variables as fallbacks for non-Tailwind spots. New color `surface-0 #0a0e17` is the Bloomberg-aligned "deepest black" from the KG Visualization backlog item.

### D2. New primitive components (`frontend/src/components/ui/`)
- `<PageHeader>` — title + subtitle + right-aligned actions + breadcrumbs.
- `<Panel>` — bordered surface card with header slot, body, footer. The spine of every page.
- `<MetricTile>` — big number + delta + sparkline + label. Used on Overview, Positions, Pacing.
- `<TickerChip>` — symbol pill with hover sparkline + click-through. Replaces `SymbolLink`.
- `<TimeScope>` — compact period selector (1D / 1W / 1M / 3M / 1Y / MAX). Controls chart queries.
- `<StatusDot>` — small colored dot with tooltip. Used on source-health, gate status, position state.
- `<KBD>` — styled keycap hint (`⌘ K`).
- `<CommandPalette>` — global `Cmd+K` modal with fuzzy ticker/page/action search.
- `<LiveFeedCard>` — a workflow node wrapper for xyflow nodes (shows last event, count, status dot).

Every page is rewritten to compose these primitives. No bespoke layout in pages.

### D3. Navigation
Sidebar keeps three sections but renames + adds one item:

| Section | Items |
| --- | --- |
| **Workspace** | Overview · Tickers · **Pipeline** (new) · **Knowledge Graph** (new) |
| **Cognitive Layers** | L1 Signals · L2 Mosaics · L3 Theses · L4 Decisions · L5 Portfolio |
| **Operations** | **HITL Queue** (renamed from "HITL Gate", badge count) · Tasks · Source Health (new) · Settings |

Global keyboard shortcuts:
- `g h` → HITL Queue
- `g p` → Pipeline
- `g t` → Tickers
- `g g` → Knowledge Graph
- `g o` → Overview
- `Cmd+K` → Command palette
- `?` → Shortcut cheat sheet

### D4. Pipeline (new top-level page — the "workflow UI")
Route: `/pipeline`

A full-viewport `@xyflow/react` graph rendered in landscape. Five vertical swim-lanes (L1 → L5) plus two HITL gate columns between L3↔L4 and L4↔L5. Nodes are `<LiveFeedCard>`s; edges are signal flows.

- **L1 Lane:** one node per configured source (Reddit / Google Trends / Amazon / Ad Library / yfinance / SEC EDGAR / CoinGecko / DeFiLlama). Each node shows: last-run timestamp, signal count last 24h, status dot (green/yellow/red) tied to `/source-health`. Click → Source Health page filtered to that source.
- **L2 Lane:** divergence calculator + STEPPS scorer + Mosaic Card Builder, as three stacked nodes. Each shows: items processed in current window + "biggest divergence" preview.
- **L3 Lane:** Vulnerability Scanner + 10X Simulator + Thesis Forge, stacked. Click → `/theses` filtered to a symbol.
- **HITL Gate 1** (between L3 and L4): shows pending decisions count. Click → `/gate/review`. If there are pending items, the gate glows pulsing amber.
- **L4 Lane:** Lifecycle Monitor + Gold Rush Tracker + Entry Signal. Shows top 3 symbols by divergence with their lifecycle stage.
- **HITL Gate 2** (between L4 and L5): "Size & enter?" gate. Same pattern.
- **L5 Lane:** Position Sizer + Decision Journal + Portfolio View. Shows open positions count + P&L delta.

**Data source in v1:** poll each endpoint (`/signals/grouped`, `/tasks`, `/source-health`, `/reviews`, `/positions`) every 30 seconds, compose into the graph. In v3 (after Run Bus lands), swap polls for SSE subscriptions and animate signal flow on events.

**Interaction:** clicking any node opens a **side drawer** with full context (recent events, filter controls, jump-to-layer-page button). Preserves focus — doesn't navigate away.

### D5. Ticker deep-page — unify fragmented views
Today, TickerDetail + DeepDive + LatticeGraph + MosaicWorkbench are **four separate pages** for one symbol. Fiscal.ai-style unifies them into **one page with tabs**:

Route: `/tickers/:symbol` (the existing route, now expanded)

Header: `<PageHeader>` with symbol ticker + price + 1D delta + watchlist star.
Tabs (sticky, scrollspy):
1. **Overview** — current TickerDetail: headline metrics + latest thesis + next event + key links.
2. **Signals** — 4-panel DeepDive: signal trends chart, source breakdown, STEPPS radar, news feed.
3. **Mosaic** — current MosaicWorkbench: divergence / coherence / vulnerability / 10X sim.
4. **Thesis** — thesis text + confidence + supporting signals + HITL decision history.
5. **Lifecycle** — gold-rush stage + days-in-stage + entry-window diagram.
6. **Knowledge Graph** — current LatticeGraph: per-symbol ego graph (xyflow).
7. **Journal** — all decision-journal entries tagged with this symbol.

`/deepdive/:symbol` and `/lattice/:symbol` and `/mosaic/:symbol` stay as **deep-linkable tab URLs** (`/tickers/:symbol/signals`, `/tickers/:symbol/graph`, etc.) for backwards compat, but the UI is one page.

### D6. HITL Queue (promoted, renamed)
Current `GateReview` becomes **`/gate`** (kept) with:
- Queue list on the left: each row = a pending decision with symbol chip + gate type (L3→L4 or L4→L5) + age + divergence/coherence scores + a colored urgency dot.
- Context pane on the right: full mosaic card, thesis text, relevant signals sparkline, risk flags, last similar decision outcome.
- Action bar: **Approve** (green) · **Defer N days** (amber) · **Escalate / Ask** (blue — writes a comment-back to the run bus) · **Reject** (red). All four write to Decision Journal.
- Keyboard: `j`/`k` move selection, `a` approve, `d` defer, `e` escalate, `x` reject.
- Sidebar badge: count of `pending_review` theses from `/reviews`.

### D7. Knowledge Graph (new top-level + existing per-ticker)
Route: `/graph` (global) and `/tickers/:symbol/graph` (ego, per existing Lattice page).

Powered by `@xyflow/react`. Node types: Company, Person, Sector, Signal-Source, Topic, Event. Edge types: signals, mentions, competitors, supplier-of, influences. Colors per D1.

v1: static positions from backend (when the KG endpoint ships per the KG Visualization backlog item). v2: force-directed layout option.

### D8. Ticker trends / signal charts
All charts use `recharts` with a shared `<Chart>` wrapper that applies token colors + grid + tooltips. `<TimeScope>` is the single control that drives `?from=…&to=…` query params on the parent component's API calls. No bespoke per-page chart styling.

### D9. Polling strategy v1 → streaming v3
- **Phase 1 / 2:** each page uses the existing `useApi` hook to poll at 30 s intervals. The data layer stays the same.
- **Phase 3:** after the **Event-Driven Run Bus** backlog item ships, introduce `useEventStream(topic)` that consumes SSE from `/api/v1/stream?topic=…` and invalidates the relevant `useApi` caches. No UI rewrite required because the data flow is hidden behind the hooks.

### D10. Performance budgets
- Initial JS bundle (main chunk) ≤ 180 KB gzipped. Enforced by Vite plugin `vite-plugin-bundle-visualizer` CI check.
- First contentful paint ≤ 1.2 s on a mid-tier laptop over localhost.
- No layout shift on route transitions — reserve layout dimensions in `<Layout>`.
- Pipeline page must render 60 nodes without frame drop at 60 fps — xyflow handles this, but the poll interval stays at 30 s, not lower, until Run Bus.

---

## 5. Phase breakdown

Each phase = its own Notion backlog card (S–L effort), its own PR, its own deploy.

| Phase | Scope | Effort | Depends on |
| --- | --- | --- | --- |
| **P0: Design system** | Install Tailwind + tokens, build `<PageHeader>`, `<Panel>`, `<MetricTile>`, `<TickerChip>`, `<TimeScope>`, `<StatusDot>`, `<KBD>`. Rewrite `Layout` + `Sidebar` + `Header` + `StatusBar` to use them. Fix dead `className`s across the app. | M | — |
| **P1: Command palette + shortcuts** | `<CommandPalette>` with `Cmd+K`. Global `useHotkeys` hook. `?` cheat sheet. Wire `g h` / `g p` / `g t` / `g g` / `g o`. | S | P0 |
| **P2: Ticker deep-page unification** | Consolidate TickerDetail + DeepDive + MosaicWorkbench + LatticeGraph into tabbed `/tickers/:symbol`. Keep old URLs as tab-aliases. | L | P0 |
| **P3: Pipeline workflow view** | New `/pipeline` page. Build `<LiveFeedCard>`. xyflow graph with 5 lanes + 2 HITL gates. Polling-based data source. | L | P0, P2, **Run Bus backend item** (read-only status) |
| **P4: HITL Queue promotion** | Rewrite `GateReview` to queue + context + action bar + keyboard. Sidebar badge count. Decision Journal integration. | M | P0, P1 |
| **P5: Knowledge Graph (global)** | New `/graph` page. Port existing `LatticeGraph` to shared xyflow wrapper. | M | P0, **KG backend data endpoint** |
| **P6: Ticker chips + sparklines everywhere** | Swap every `SymbolLink` for `<TickerChip>` with hover sparkline. Adopt `<TimeScope>` on all chart pages. | S | P0 |
| **P7: Streaming (after Run Bus)** | `useEventStream`, swap Pipeline + HITL Queue to SSE, animate edges on signal flow events. | M | Run Bus backend shipped |
| **P8: Performance & a11y** | Code splitting per route (matches existing "Code Splitting" backlog item), bundle budgets enforced, focus management, ARIA on xyflow. | M | P0–P6 |

Parallel-safe: P1 and P6 can run alongside P2. P4 needs P1 for keyboard. P7 waits for backend. Total sequential critical path ≈ P0 → P2 → P3, roughly 3–4 weeks full-time.

---

## 6. Acceptance criteria (per phase)

**P0 (Design system)**
- [ ] `tailwind.config.js` extends tokens from `index.css`; `npm run build` succeeds.
- [ ] Eight primitives exist under `components/ui/` with Storybook-style usage examples in `docs/ui/`.
- [ ] Zero `className` strings in the codebase that don't resolve to a defined class (enforced via a one-shot grep script in CI).
- [ ] Visual smoke test: login → overview → tickers → settings round-trip looks consistent (no orphan fonts, no layout jumps).

**P3 (Pipeline)**
- [ ] `/pipeline` renders the 5 lanes with at least one node per lane + two HITL gates.
- [ ] Each node pulls real data from the existing endpoints and shows last-updated timestamp.
- [ ] Click node → side drawer with full context.
- [ ] 30 s poll → UI reflects signal count deltas within 1 poll cycle.
- [ ] Zero hardcoded ticker/source lists — everything from API.

**P4 (HITL)**
- [ ] Pending `pending_review` theses surface as queue rows within 30 s of creation.
- [ ] Each action writes to Decision Journal and removes the row.
- [ ] Keyboard shortcuts work and don't collide with browser defaults.
- [ ] Sidebar badge count matches queue length.

(Full acceptance per phase in each phase's Notion card.)

---

## 7. Backend dependencies (separate specs, non-frontend)

These are listed in the existing backlog and must be delivered in parallel — the UI spec is useless without them.

1. **Run Bus** (`33d7772f-a7ae-81f9-a675-fe1a8231906c`) — enables Phase 7 streaming. Until then, polls.
2. **`/api/v1/graph`** — KG data endpoint. Blocks P5. Not in backlog yet — add as a new P1 card.
3. **`/api/v1/events/stream` (SSE)** — Blocks P7. Part of Run Bus.
4. **`/api/v1/source-health`** — already exists. ✓
5. **`/api/v1/reviews`** (gate queue) — already exists. ✓

---

## 8. Registration

- This spec is committed to the repo at `docs/superpowers/specs/2026-04-23-fiscal-ai-workflow-ui-spec.md`.
- A Notion page will be created under **Social Arb Research Hub** titled "Fiscal.ai Workflow UI Redesign — Spec (2026-04-23)" with a link to this file and phase-by-phase backlog-card candidates.
- Once approved, P0 becomes a Notion backlog card (New Feature · Frontend · P1 · M · Sprint 2) and execution begins.

---

## 9. Open questions (for Dan's morning review)

1. **Tailwind v3 vs zero-dep CSS Modules?** I recommend Tailwind because the codebase already uses its class strings. Confirm or reject.
2. **Route migration for `/deepdive/:symbol` etc.** — redirect to the unified page, or keep as 301? Recommend 301 redirect in routing for link durability.
3. **Command palette scope** — just navigation + tickers, or also actions (approve gate, trigger pipeline)? I recommend starting with nav + tickers and adding actions in P4.
4. **Bloomberg surface-0 (`#0a0e17`)** — adopt as primary background, or keep the current `#111827`? Bloomberg-style is darker; recommend adopting for the Pipeline + Graph pages only, keep `#111827` elsewhere, to differentiate "live operational" pages from standard pages.
5. **Phase 0 timing** — can Dan allocate a 2-week window to ship the design system before any other feature work? Trying to rebuild individual pages without P0 first will create churn.

---

## 10. What this spec deliberately does **not** commit to

- Specific pixel dimensions / Figma mocks — those come after approval, as part of P0 execution.
- Choice of icon library (Lucide vs. Heroicons vs. a bespoke monospace pictogram set). Decide in P0.
- Analytics / telemetry wiring. Separate spec.
- Admin / multi-user features. Separate spec.
