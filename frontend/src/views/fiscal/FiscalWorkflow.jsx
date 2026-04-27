/**
 * FiscalWorkflow — V2 Workflow Pipeline view (FE-001 V2).
 *
 * 5 stage cards (L1..L5) showing today's throughput, sparklines, agent
 * pulse, and last-update times. Plus an L1 source health table and
 * activity feed. Mock data shaped from the 2026-04-21 daily brief.
 */
import { FiscalLayout } from './FiscalLayout'

const stages = [
  {
    id: 'L1', label: 'Signal Radar',
    count: '480', sub: 'signals collected · 5 sources',
    spark: '0,28 25,22 50,18 75,24 100,14 125,20 150,12 175,16 200,10',
    color: 'text-info',
    pulse: 'positive', pulseLabel: 'active', age: '14m ago',
  },
  {
    id: 'L2', label: 'Mosaic Assembly',
    count: '26', sub: 'mosaics built · STEPPS scored',
    spark: '0,26 25,24 50,20 75,18 100,16 125,12 150,14 175,10 200,8',
    color: 'text-violet',
    pulse: 'positive', pulseLabel: 'active', age: '8m ago',
  },
  {
    id: 'L3', label: 'Thesis Forge',
    count: '18', sub: 'theses · all pending HITL',
    spark: '0,30 25,28 50,24 75,22 100,18 125,16 150,14 175,12 200,8',
    color: 'text-warning',
    pulse: 'warning', pulseLabel: 'awaiting HITL', age: '5m ago',
  },
  {
    id: 'L4', label: 'Decisions',
    count: '3', countSub: '/ 18',
    sub: 'HITL gate · 3 escalated',
    spark: '0,30 50,28 100,28 150,30 200,28',
    color: 'text-warning',
    pulse: 'warning', pulseLabel: 'user input needed', urgent: true, age: 'now',
  },
  {
    id: 'L5', label: 'Portfolio',
    count: '0', sub: 'open positions · waiting on L4',
    spark: '0,28 200,28',
    color: 'text-faint',
    pulse: 'faint', pulseLabel: 'idle', age: '—',
  },
]

const sources = [
  { name: 'yfinance',      signals: 273, status: '✓ healthy',         tone: 'text-positive' },
  { name: 'reddit',        signals: 103, status: '✓ healthy',         tone: 'text-positive' },
  { name: 'sec_edgar',     signals: 100, status: '✓ healthy',         tone: 'text-positive' },
  { name: 'coingecko',     signals:   2, status: '⚠ rate-limited 10+', tone: 'text-warning' },
  { name: 'defillama',     signals:   2, status: '⚠ map gap 21/26',   tone: 'text-warning' },
  { name: 'google_trends', signals:   0, status: '✗ no signals',      tone: 'text-negative' },
]

const activity = [
  { t: '06:36', l: 'L4', msg: 'BLOCKED · git lockfiles persist · 11th consecutive cycle' },
  { t: '06:30', l: 'L3', msg: 'Forged 18 theses · all pending_review' },
  { t: '06:18', l: 'L2', msg: 'Built 26 mosaics · top: AMD div 70.4 (#1)' },
  { t: '06:00', l: 'L1', msg: 'Cycle started · 5 sources · 480 signals collected' },
]

const pulseColor = {
  positive: 'bg-positive animate-pulse',
  warning:  'bg-warning',
  faint:    'bg-faint',
}

export function FiscalWorkflow() {
  return (
    <FiscalLayout title="Workflow Pipeline">
      <p className="text-sm text-muted mb-6 -mt-2">Live view of the 5-layer cognitive topology. Each stage shows current activity, throughput, and any blockers.</p>

      {/* 5 stage cards */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-3 items-stretch">
        {stages.map(s => (
          <div
            key={s.id}
            className={`bg-surface rounded-lg p-5 flex flex-col border ${s.urgent ? 'border-warning/40' : 'border-borderc'}`}
            style={{ boxShadow: '0 1px 2px rgba(16,24,40,.06)' }}
          >
            <div className="flex items-center gap-2 mb-3">
              <div className="text-xs font-mono text-violet font-semibold">{s.id}</div>
              <div className="text-sm font-semibold">{s.label}</div>
            </div>
            <div className="font-mono text-xl font-bold">
              {s.count}{s.countSub && <span className="text-sm text-warning ml-1">{s.countSub}</span>}
            </div>
            <div className="text-xxs text-muted mb-3">{s.sub}</div>
            <svg width="100%" height="32" viewBox="0 0 200 32" className={`${s.color} mb-2`}>
              <polyline points={s.spark} fill="none" stroke="currentColor" strokeWidth="1.5" />
            </svg>
            <div className="mt-auto pt-2 border-t border-borderc flex items-center justify-between text-xxs">
              <span className="flex items-center gap-1">
                <span className={`w-1.5 h-1.5 rounded-full ${pulseColor[s.pulse]}`} />
                <span className={s.urgent ? 'text-warning font-medium' : 'text-muted'}>{s.pulseLabel}</span>
              </span>
              <span className="text-faint font-mono">{s.age}</span>
            </div>
          </div>
        ))}
      </div>

      {/* Source health */}
      <h2 className="text-md font-semibold mt-10 mb-3">L1 source health · last cycle</h2>
      <div className="bg-surface border border-borderc rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-rail text-xxs uppercase tracking-wider text-muted">
            <tr>
              <th className="text-left py-2 px-4 font-medium">Source</th>
              <th className="text-right py-2 px-4 font-medium">Signals</th>
              <th className="text-left py-2 px-4 font-medium">Status</th>
              <th className="text-right py-2 px-4 font-medium">Last run</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-borderc">
            {sources.map(s => (
              <tr key={s.name}>
                <td className="py-2 px-4">{s.name}</td>
                <td className="py-2 px-4 text-right font-mono">{s.signals}</td>
                <td className="py-2 px-4"><span className={`inline-flex items-center gap-1 ${s.tone} text-xs`}>{s.status}</span></td>
                <td className="py-2 px-4 text-right text-xs text-muted font-mono">14m ago</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Activity feed */}
      <h2 className="text-md font-semibold mt-10 mb-3">Today's activity</h2>
      <div className="bg-surface border border-borderc rounded-lg p-4 space-y-2 text-sm">
        {activity.map((a, i) => (
          <div key={i} className="flex items-start gap-3">
            <span className="text-xxs text-faint font-mono w-12 shrink-0 pt-0.5">{a.t}</span>
            <span className="text-xs font-mono text-violet w-8 shrink-0 pt-0.5">{a.l}</span>
            <span>{a.msg}</span>
          </div>
        ))}
      </div>
    </FiscalLayout>
  )
}
