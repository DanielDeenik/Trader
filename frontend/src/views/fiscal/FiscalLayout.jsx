/**
 * FiscalLayout — fiscal.ai-style application shell (FE-001 V1).
 *
 * 3-column grid: 5-layer left rail + main content + collapsible HITL right rail.
 * Light theme + dense data per DLOG-6. HITL drawer collapsed on first load
 * per DLOG-11. Tokens come from index.html's Tailwind config (DLOG-6).
 *
 * Mock data for now — wired-up data is FE-007+ tickets.
 */
import { useState } from 'react'
import { Link, useLocation } from 'react-router-dom'

const layerNav = [
  { id: 'L0', label: 'Infrastructure', path: '/fiscal/infra', count: null },
  { id: 'L1', label: 'Signal Radar',    path: '/fiscal/signals', count: 480 },
  { id: 'L2', label: 'Mosaic Assembly', path: '/fiscal/mosaics', count: 26 },
  { id: 'L3', label: 'Thesis Forge',    path: '/fiscal/theses', count: 18 },
  { id: 'L4', label: 'Decisions',       path: '/fiscal/decisions', count: 3, urgent: true },
  { id: 'L5', label: 'Portfolio',       path: '/fiscal/portfolio', count: 0 },
]

const workflowNav = [
  { label: 'Pipeline',         path: '/fiscal/pipeline',  icon: '📈' },
  { label: 'Tickers',          path: '/fiscal/tickers',   icon: '🎯' },
  { label: 'HITL Queue',       path: '/fiscal/hitl',      icon: '❓' },
  { label: 'Knowledge Graph',  path: '/fiscal/kg',        icon: '🕸️' },
]

const watchlist = [
  { sym: 'AMD',  delta: '+5.5', color: 'text-positive' },
  { sym: 'SQ',   delta: 'stable', color: 'text-faint' },
  { sym: 'PLTR', delta: '±0',   color: 'text-warning' },
  { sym: 'TSLA', delta: '−2.1', color: 'text-negative' },
  { sym: 'MSFT', delta: '+0.8', color: 'text-positive' },
]

const hitlQueue = [
  {
    sym: 'AMD',  age: '16h', stage: 'Validating',
    question: 'Approve build_thesis · Kelly 0.25?',
    facts: 'div 70.4 · coh 100 · Q1 May 5 T-14',
    primary: 'Approve',
  },
  {
    sym: 'SQ',   age: '12h', stage: 'Validating',
    question: 'Confirm Kelly sizing 0.25?',
    facts: 'div 49.1 · coh 100 · Q1 May 7 T-16',
    primary: 'Approve',
  },
  {
    sym: 'PLTR', age: '5h',  stage: 'Validating',
    question: 'Defer until post-earnings?',
    facts: 'div 48.7 · coh 85 (binary) · Burry vs Trump',
    primary: 'Defer',
  },
]

export function FiscalLayout({ title, children }) {
  // DLOG-11: collapsed by default on first load.
  const [drawerOpen, setDrawerOpen] = useState(false)
  const location = useLocation()
  const isActive = path => location.pathname === path

  return (
    <div className="bg-app text-primary font-sans h-screen overflow-hidden flex flex-col">

      {/* Top bar */}
      <header className="h-12 bg-surface border-b border-borderc flex items-center px-4 gap-4 shrink-0">
        <Link to="/fiscal" className="flex items-center gap-2 w-52 shrink-0 hover:opacity-80">
          <div className="w-7 h-7 rounded-md bg-violet flex items-center justify-center text-white font-bold text-xs">SA</div>
          <div>
            <div className="font-semibold text-sm">Social Arb</div>
          </div>
          <span className="text-xxs text-faint font-mono">v1.0.0</span>
        </Link>

        <div className="flex-1 max-w-md">
          <input
            type="text"
            placeholder="Search ticker, person, sector, mosaic… (⌘K)"
            className="w-full px-3 py-1.5 text-sm border border-borderc rounded-md bg-app placeholder-faint focus:outline-none focus:ring-1 focus:ring-violet"
          />
        </div>
        <div className="flex-1" />

        <div className="flex items-center gap-4 text-sm">
          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-positive animate-pulse" />
            <span className="text-xs text-muted">480 signals · today</span>
          </div>
          <button
            onClick={() => setDrawerOpen(o => !o)}
            className="flex items-center gap-1.5 hover:opacity-80"
            title="Toggle HITL drawer"
          >
            <span className="w-2 h-2 rounded-full bg-warning" />
            <span className="text-xs text-muted">{hitlQueue.length} HITL pending</span>
          </button>
          <div className="w-7 h-7 rounded-full bg-rail border border-borderc flex items-center justify-center text-xs font-mono">DD</div>
        </div>
      </header>

      <div className="flex flex-1 overflow-hidden">

        {/* Left rail */}
        <aside className="w-52 shrink-0 bg-rail border-r border-borderc overflow-y-auto py-3">
          <div className="px-4 mb-4">
            <div className="text-xxs uppercase tracking-wider text-faint font-semibold">Layers</div>
          </div>
          <nav className="px-2 space-y-0.5">
            {layerNav.map(item => (
              <Link
                key={item.id}
                to={item.path}
                className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-sm cursor-pointer ${
                  isActive(item.path)
                    ? 'bg-surface text-primary font-medium'
                    : 'text-muted hover:bg-surface hover:text-primary'
                }`}
                style={isActive(item.path) ? { boxShadow: 'inset 2px 0 0 #7C3AED' } : {}}
              >
                <span className="text-xs text-faint font-mono w-5">{item.id}</span>
                <span>{item.label}</span>
                {item.count !== null && (
                  <span className={`ml-auto text-xxs font-mono ${
                    item.urgent ? 'inline-flex items-center px-1.5 py-0.5 rounded-full bg-warning/15 text-warning' : 'text-muted'
                  }`}>
                    {item.count}
                  </span>
                )}
              </Link>
            ))}
          </nav>

          <div className="px-4 mt-6 mb-2">
            <div className="text-xxs uppercase tracking-wider text-faint font-semibold">Workflow</div>
          </div>
          <nav className="px-2 space-y-0.5">
            {workflowNav.map(item => (
              <Link
                key={item.path}
                to={item.path}
                className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-sm cursor-pointer ${
                  isActive(item.path)
                    ? 'bg-surface text-primary font-medium'
                    : 'text-muted hover:bg-surface hover:text-primary'
                }`}
              >
                <span>{item.icon}</span>
                <span>{item.label}</span>
              </Link>
            ))}
          </nav>

          <div className="px-4 mt-6 mb-2">
            <div className="text-xxs uppercase tracking-wider text-faint font-semibold">Watchlist</div>
          </div>
          <nav className="px-2 space-y-0.5 text-sm font-mono">
            {watchlist.map(t => (
              <div key={t.sym} className="px-3 py-1 text-muted hover:text-primary cursor-pointer flex items-center justify-between">
                <span>{t.sym}</span>
                <span className={`${t.color} text-xs ml-1`}>{t.delta}</span>
              </div>
            ))}
          </nav>

          <div className="px-4 mt-6 pt-4 border-t border-borderc">
            <div className="text-xxs text-muted">Settings · Help</div>
          </div>
        </aside>

        {/* Main */}
        <main className="flex-1 overflow-y-auto bg-app">
          {title && (
            <div className="px-6 py-5 border-b border-borderc bg-surface">
              <div className="flex items-center justify-between">
                <h1 className="text-lg font-semibold">{title}</h1>
              </div>
            </div>
          )}
          <div className="px-6 py-6">{children}</div>
        </main>

        {/* Right rail — HITL queue */}
        <aside
          className={`shrink-0 bg-rail border-l border-borderc transition-all duration-200 overflow-hidden ${
            drawerOpen ? 'w-[360px]' : 'w-12'
          }`}
        >
          {!drawerOpen ? (
            <button
              onClick={() => setDrawerOpen(true)}
              className="h-full w-full flex flex-col items-center pt-3 hover:bg-surface"
              title="Open HITL queue"
            >
              <div className="w-7 h-7 rounded-md bg-warning/15 flex items-center justify-center relative">
                <span className="text-warning text-sm">❓</span>
                <span className="absolute -top-1 -right-1 w-4 h-4 rounded-full bg-warning text-white text-xxs flex items-center justify-center font-bold">{hitlQueue.length}</span>
              </div>
              <div className="text-xxs text-muted mt-2" style={{writingMode:'vertical-rl', transform:'rotate(180deg)'}}>HITL · {hitlQueue.length}</div>
            </button>
          ) : (
            <div className="h-full flex flex-col">
              <div className="h-12 px-4 flex items-center justify-between border-b border-borderc bg-surface">
                <div className="flex items-center gap-2">
                  <div className="text-sm font-semibold">HITL Queue</div>
                  <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xxs font-medium bg-warning/15 text-warning">{hitlQueue.length} pending</span>
                </div>
                <button onClick={() => setDrawerOpen(false)} className="text-faint hover:text-primary text-lg leading-none">→</button>
              </div>
              <div className="p-4 space-y-3 overflow-y-auto flex-1">
                {hitlQueue.map(card => (
                  <div key={card.sym} className="bg-surface border border-borderc rounded-md p-3">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-mono text-sm font-semibold">{card.sym}</span>
                      <span className="inline-flex px-1.5 py-0.5 rounded-full text-xxs bg-warning/10 text-warning">{card.stage}</span>
                      <span className="text-xxs text-faint ml-auto">{card.age}</span>
                    </div>
                    <div className="text-sm font-medium mb-1.5">{card.question}</div>
                    <div className="text-xs text-muted mb-3 font-mono">{card.facts}</div>
                    <div className="flex items-center gap-1.5">
                      <button className={`flex-1 px-2 py-1 rounded text-white text-xs font-medium ${card.primary === 'Approve' ? 'bg-positive' : 'bg-warning'}`}>{card.primary}</button>
                      {card.primary !== 'Approve' && <button className="px-2 py-1 rounded bg-positive/10 text-positive text-xs">Approve</button>}
                      {card.primary !== 'Defer' && <button className="px-2 py-1 rounded bg-warning/10 text-warning text-xs">Defer</button>}
                      <button className="px-2 py-1 rounded bg-negative/10 text-negative text-xs">Reject</button>
                    </div>
                  </div>
                ))}
                <div className="text-xxs text-faint text-center pt-2">{hitlQueue.length} of {hitlQueue.length} · L4 Decisions queue</div>
              </div>
            </div>
          )}
        </aside>

      </div>
    </div>
  )
}
