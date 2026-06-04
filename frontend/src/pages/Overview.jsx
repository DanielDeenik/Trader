import { useState } from 'react'
import { useApi } from '../hooks'
import { api } from '../api'
import { SymbolLink } from '../components/SymbolLink'
import { Link } from 'react-router-dom'

function formatTime(isoString) {
  if (!isoString) return 'Never'
  const date = new Date(isoString)
  return date.toLocaleString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}

function formatDurationHuman(ms) {
  if (!ms) return '—'
  const secs = Math.round(ms / 1000)
  if (secs < 60) return `${secs}s`
  const mins = Math.round(secs / 60)
  if (mins < 60) return `${mins}m`
  const hours = Math.round(mins / 60)
  if (hours < 24) return `${hours}h`
  const days = Math.round(hours / 24)
  return `${days}d`
}

export default function Overview() {
  const [triggeringSchedule, setTriggeringSchedule] = useState(null)
  const [quickAction, setQuickAction] = useState(null)
  const [quickActionMsg, setQuickActionMsg] = useState(null)

  // Fetch all data in parallel
  const { data: health } = useApi(() => api.getHealth())
  const { data: positions } = useApi(() => api.getPositions({ status: 'open' }))
  const { data: signals } = useApi(() => api.getSignals({ limit: 100 }))
  const { data: signalsGrouped } = useApi(() => api.getSignalsGrouped())
  const { data: reviews } = useApi(() => api.getReviews({ limit: 50 }))
  const { data: scheduler } = useApi(() => api.getSchedulerStatus())

  // Calculate pending reviews
  const pendingReviews = (reviews || []).filter(r => r.decision === 'pending' || !r.decision)

  // Get top 10 symbols by signal activity
  const topSymbols = (signalsGrouped || [])
    .sort((a, b) => (b.total || 0) - (a.total || 0))
    .slice(0, 10)

  // Get recent 10 signals
  const recentSignals = (signals || []).slice(0, 10)

  // Count open positions
  const openPositionsCount = (positions || []).length

  // Calculate table counts from health
  const signalCount = health?.table_counts?.signals || 0
  const mosaicCount = health?.table_counts?.mosaics || 0
  const thesisCount = health?.table_counts?.theses || 0

  const handleTriggerSchedule = async (scheduleName) => {
    setTriggeringSchedule(scheduleName)
    try {
      await api.triggerSchedule({ schedule_name: scheduleName })
      setQuickActionMsg({ type: 'success', text: `${scheduleName} triggered` })
      setTimeout(() => setTriggeringSchedule(null), 2000)
    } catch (err) {
      console.error('Trigger failed:', err)
      setQuickActionMsg({ type: 'error', text: `Failed to trigger ${scheduleName}` })
      setTriggeringSchedule(null)
    }
    setTimeout(() => setQuickActionMsg(null), 4000)
  }

  return (
    <div className="space-y-6">
      {/* STATS ROW */}
      <div className="grid grid-cols-4 gap-4">
        {/* Total Signals */}
        <div className="bg-[#111827]/80 border border-white/[0.06] rounded-xl p-5">
          <div className="text-[11px] font-medium text-white/40 uppercase tracking-widest">Total Signals</div>
          <div className="text-2xl font-bold font-mono text-emerald-400 mt-3">{signalCount}</div>
          <div className="text-[13px] text-white/50 mt-2">Latest: {recentSignals.length > 0 ? formatTime(recentSignals[0].timestamp) : '—'}</div>
        </div>

        {/* Active Mosaics */}
        <div className="bg-[#111827]/80 border border-white/[0.06] rounded-xl p-5">
          <div className="text-[11px] font-medium text-white/40 uppercase tracking-widest">Active Mosaics</div>
          <div className="text-2xl font-bold font-mono text-emerald-400 mt-3">{mosaicCount}</div>
          <div className="text-[13px] text-white/50 mt-2">Assembled signals</div>
        </div>

        {/* Open Theses */}
        <div className="bg-[#111827]/80 border border-white/[0.06] rounded-xl p-5">
          <div className="text-[11px] font-medium text-white/40 uppercase tracking-widest">Open Theses</div>
          <div className="text-2xl font-bold font-mono text-emerald-400 mt-3">{thesisCount}</div>
          <div className="text-[13px] text-white/50 mt-2">Investment theses</div>
        </div>

        {/* Open Positions */}
        <div className="bg-[#111827]/80 border border-white/[0.06] rounded-xl p-5">
          <div className="text-[11px] font-medium text-white/40 uppercase tracking-widest">Open Positions</div>
          <div className="text-2xl font-bold font-mono text-emerald-400 mt-3">{openPositionsCount}</div>
          <div className="text-[13px] text-white/50 mt-2">Active trades</div>
        </div>
      </div>

      {/* TOP MOVERS TABLE */}
      {topSymbols.length > 0 && (
        <div className="bg-[#111827]/80 border border-white/[0.06] rounded-xl p-5">
          <div className="text-[11px] font-medium text-white/40 uppercase tracking-widest mb-4">Top Movers by Signal Activity</div>

          <div className="overflow-x-auto">
            <table className="w-full text-[13px]">
              <thead>
                <tr className="border-b border-white/[0.06]">
                  <th className="text-left py-3 px-4 text-white/60 font-mono font-medium">Symbol</th>
                  <th className="text-right py-3 px-4 text-white/60 font-mono font-medium">Total</th>
                  <th className="text-center py-3 px-4 text-white/60 font-mono font-medium">Sentiment</th>
                  <th className="text-right py-3 px-4 text-white/60 font-mono font-medium">Sources</th>
                  <th className="text-left py-3 px-4 text-white/60 font-mono font-medium">Latest</th>
                  <th className="text-center py-3 px-4 text-white/60 font-mono font-medium">Action</th>
                </tr>
              </thead>
              <tbody>
                {topSymbols.map((sym, idx) => {
                  const latest = (signals || [])
                    .filter(s => s.symbol === sym.symbol)
                    .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))[0]

                  const bullishPct = sym.total > 0 ? Math.round((sym.bullish / sym.total) * 100) : 0
                  const bearishPct = sym.total > 0 ? Math.round((sym.bearish / sym.total) * 100) : 0
                  const neutralPct = sym.total > 0 ? Math.round((sym.neutral / sym.total) * 100) : 0

                  return (
                    <tr key={sym.symbol} className="border-b border-white/[0.06] hover:bg-white/[0.02] transition-colors">
                      <td className="py-3 px-4 text-white font-mono font-bold">
                        <SymbolLink symbol={sym.symbol} />
                      </td>
                      <td className="py-3 px-4 text-right font-mono text-white/80">{sym.total}</td>
                      <td className="py-3 px-4">
                        <div className="flex items-center gap-2 justify-center">
                          {bullishPct > 0 && (
                            <div className="flex items-center gap-1">
                              <div className="w-6 h-1 bg-emerald-500/60 rounded-full"></div>
                              <span className="text-[11px] text-emerald-400 font-mono">{bullishPct}%</span>
                            </div>
                          )}
                          {bearishPct > 0 && (
                            <div className="flex items-center gap-1">
                              <div className="w-6 h-1 bg-red-500/60 rounded-full"></div>
                              <span className="text-[11px] text-red-400 font-mono">{bearishPct}%</span>
                            </div>
                          )}
                        </div>
                      </td>
                      <td className="py-3 px-4 text-right font-mono text-white/60">{sym.source_count || (typeof sym.sources === 'string' ? sym.sources.split(',').length : Array.isArray(sym.sources) ? sym.sources.length : 0)}</td>
                      <td className="py-3 px-4 text-[12px] text-white/50">
                        {latest ? formatTime(latest.timestamp) : '—'}
                      </td>
                      <td className="py-3 px-4 text-center">
                        <Link
                          to={`/tickers/${sym.symbol}`}
                          className="inline-block text-[11px] bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30 px-2.5 py-1 rounded-full transition-colors font-mono"
                        >
                          Deep Dive
                        </Link>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* RECENT SIGNALS FEED */}
      {recentSignals.length > 0 && (
        <div className="bg-[#111827]/80 border border-white/[0.06] rounded-xl p-5">
          <div className="text-[11px] font-medium text-white/40 uppercase tracking-widest mb-4">Recent Signals (Last 10)</div>

          <div className="space-y-2">
            {recentSignals.map((signal, idx) => (
              <div key={signal.id} className="flex items-center gap-3 py-2 px-3 bg-white/[0.02] rounded-lg border border-white/[0.05] hover:border-white/[0.10] transition-colors">
                <span className="text-[12px] text-white/40 font-mono min-w-fit">{formatTime(signal.timestamp)}</span>

                <div className="flex-1 flex items-center gap-3">
                  <SymbolLink symbol={signal.symbol} />

                  <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-mono font-medium ${
                    signal.direction === 'bullish'
                      ? 'bg-emerald-500/20 text-emerald-300'
                      : signal.direction === 'bearish'
                      ? 'bg-red-500/20 text-red-300'
                      : 'bg-gray-500/20 text-gray-300'
                  }`}>
                    {signal.direction === 'bullish' ? '↑' : signal.direction === 'bearish' ? '↓' : '→'}
                    {signal.direction}
                  </span>

                  <span className="text-[12px] text-white/40 font-mono">{signal.source}</span>

                  {signal.strength && (
                    <span className="text-[11px] bg-amber-500/10 text-amber-300 px-2 py-0.5 rounded-full font-mono">
                      str: {signal.strength}
                    </span>
                  )}

                  {signal.confidence && (
                    <span className="text-[11px] bg-blue-500/10 text-blue-300 px-2 py-0.5 rounded-full font-mono">
                      conf: {Math.round(signal.confidence * 100)}%
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* SCHEDULER STATUS */}
      {scheduler && scheduler.schedules && (
        <div className="bg-[#111827]/80 border border-white/[0.06] rounded-xl p-5">
          <div className="flex items-center justify-between mb-4">
            <div className="text-[11px] font-medium text-white/40 uppercase tracking-widest">Scheduler Status</div>
            <div className={`px-2.5 py-1 rounded-full text-[11px] font-mono font-medium ${
              scheduler.running
                ? 'bg-emerald-500/20 text-emerald-300'
                : 'bg-amber-500/20 text-amber-300'
            }`}>
              {scheduler.running ? '● Running' : '● Stopped'}
            </div>
          </div>

          <div className="space-y-2">
            {Object.entries(scheduler.schedules || {}).map(([name, info]) => (
              <div key={name} className="flex items-center justify-between py-3 px-3 bg-white/[0.02] rounded-lg border border-white/[0.05] hover:border-white/[0.10] transition-colors">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-1">
                    <span className="font-mono text-[13px] text-white font-medium min-w-24">{name}</span>
                    {info.interval_human && (
                      <span className="text-[11px] bg-white/[0.06] text-white/60 px-2 py-0.5 rounded font-mono">
                        {info.interval_human}
                      </span>
                    )}
                  </div>
                  <div className="text-[11px] text-white/40 font-mono space-x-4">
                    <span>Last: {formatTime(info.last_run)}</span>
                    <span>Next: {formatTime(info.next_run)}</span>
                  </div>
                </div>

                <button
                  onClick={() => handleTriggerSchedule(name)}
                  disabled={triggeringSchedule === name}
                  className="ml-4 px-3 py-1.5 rounded-lg text-[11px] font-mono font-medium bg-emerald-500/20 text-emerald-300 hover:bg-emerald-500/30 disabled:bg-white/[0.05] disabled:text-white/40 transition-colors whitespace-nowrap"
                >
                  {triggeringSchedule === name ? 'Running…' : 'Trigger'}
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* PENDING REVIEWS */}
      {pendingReviews.length > 0 && (
        <div className="bg-[#111827]/80 border border-white/[0.06] rounded-xl p-5">
          <div className="flex items-center justify-between mb-4">
            <div className="text-[11px] font-medium text-white/40 uppercase tracking-widest">Pending Reviews</div>
            <div className="px-2.5 py-1 rounded-full text-[12px] font-mono font-bold bg-amber-500/20 text-amber-300">
              {pendingReviews.length}
            </div>
          </div>

          <div className="space-y-2">
            {pendingReviews.slice(0, 5).map((review) => (
              <div key={review.id} className="flex items-center justify-between py-2 px-3 bg-white/[0.02] rounded-lg border border-white/[0.05]">
                <div className="flex-1 flex items-center gap-3">
                  <SymbolLink symbol={review.symbol} />
                  <span className="text-[11px] text-white/50 font-mono">{review.gate}</span>
                  {review.total_score !== undefined && (
                    <span className="text-[11px] bg-blue-500/10 text-blue-300 px-2 py-0.5 rounded font-mono">
                      Score: {Math.round(review.total_score * 100)}%
                    </span>
                  )}
                </div>
                <Link
                  to={`/decisions?symbol=${review.symbol}`}
                  className="text-[11px] text-emerald-400 hover:text-emerald-300 font-mono underline"
                >
                  Review →
                </Link>
              </div>
            ))}
            {pendingReviews.length > 5 && (
              <Link to="/decisions" className="block mt-3 text-[12px] text-white/50 hover:text-white/70 font-mono">
                View all {pendingReviews.length} pending…
              </Link>
            )}
          </div>
        </div>
      )}

      {/* QUICK ACTIONS */}
      <div className="bg-[#111827]/80 border border-white/[0.06] rounded-xl p-5">
        <div className="text-[11px] font-medium text-white/40 uppercase tracking-widest mb-4">Quick Actions</div>

        <div className="flex flex-wrap gap-3">
          <button
            onClick={async () => {
              setQuickAction('collect')
              try {
                await api.createTask({ task_type: 'collect' })
                setQuickActionMsg({ type: 'success', text: 'Collection started → check Task Queue' })
              } catch (err) {
                setQuickActionMsg({ type: 'error', text: `Failed: ${err.message}` })
              }
              setQuickAction(null)
              setTimeout(() => setQuickActionMsg(null), 5000)
            }}
            disabled={quickAction === 'collect'}
            className="px-4 py-2.5 rounded-lg text-[12px] font-mono font-medium bg-emerald-500/20 text-emerald-300 hover:bg-emerald-500/30 disabled:bg-white/[0.05] disabled:text-white/40 transition-colors"
          >
            {quickAction === 'collect' ? '⟳ Collecting…' : '⬇ Run Collect'}
          </button>

          <button
            onClick={async () => {
              setQuickAction('analyze')
              try {
                await api.createTask({ task_type: 'analyze' })
                setQuickActionMsg({ type: 'success', text: 'Analysis started → check Task Queue' })
              } catch (err) {
                setQuickActionMsg({ type: 'error', text: `Failed: ${err.message}` })
              }
              setQuickAction(null)
              setTimeout(() => setQuickActionMsg(null), 5000)
            }}
            disabled={quickAction === 'analyze'}
            className="px-4 py-2.5 rounded-lg text-[12px] font-mono font-medium bg-blue-500/20 text-blue-300 hover:bg-blue-500/30 disabled:bg-white/[0.05] disabled:text-white/40 transition-colors"
          >
            {quickAction === 'analyze' ? '⟳ Analyzing…' : '⚙ Run Analyze'}
          </button>

          <Link
            to="/instruments"
            className="px-4 py-2.5 rounded-lg text-[12px] font-mono font-medium bg-purple-500/20 text-purple-300 hover:bg-purple-500/30 transition-colors inline-block"
          >
            ➕ Add Instrument
          </Link>

          <Link
            to="/decisions"
            className="px-4 py-2.5 rounded-lg text-[12px] font-mono font-medium bg-white/[0.05] text-white/70 hover:bg-white/[0.10] transition-colors inline-block"
          >
            📋 Review Queue
          </Link>
        </div>

        {quickActionMsg && (
          <div className={`mt-4 px-4 py-3 rounded-lg text-[12px] font-mono ${
            quickActionMsg.type === 'success'
              ? 'bg-emerald-500/10 text-emerald-300 border border-emerald-500/20'
              : 'bg-red-500/10 text-red-300 border border-red-500/20'
          }`}>
            {quickActionMsg.text}
          </div>
        )}
      </div>
    </div>
  )
}
