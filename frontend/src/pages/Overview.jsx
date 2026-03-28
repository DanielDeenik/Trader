import { useState } from 'react'
import { useApi } from '../hooks'
import { api } from '../api'
import { SymbolLink } from '../components/SymbolLink'

function formatTime(isoString) {
  if (!isoString) return 'Never'
  const date = new Date(isoString)
  return date.toLocaleString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}

function formatDuration(ms) {
  if (!ms) return '—'
  const secs = Math.round(ms / 1000)
  if (secs < 60) return `${secs}s`
  const mins = Math.round(secs / 60)
  if (mins < 60) return `${mins}m`
  const hours = Math.round(mins / 60)
  return `${hours}h`
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

  // Calculate last 24h active signals
  const now = new Date()
  const oneDayAgo = new Date(now.getTime() - 24 * 60 * 60 * 1000)
  const recentSignals = (signals || []).filter(s => new Date(s.timestamp) > oneDayAgo)

  // Calculate pending reviews
  const pendingReviews = (reviews || []).filter(r => r.decision === 'pending' || !r.decision)

  // Get top 5 symbols by signal activity
  const topSymbols = (signalsGrouped || [])
    .sort((a, b) => (b.total || 0) - (a.total || 0))
    .slice(0, 5)

  // Build heatmap data
  const sources = ['reddit', 'news', 'sec_edgar', 'google_trends', 'yfinance']
  const heatmapData = {}

  topSymbols.forEach(sym => {
    heatmapData[sym.symbol] = {}
    sources.forEach(src => {
      // Count signals from this source for this symbol
      const count = (signals || []).filter(
        s => s.symbol === sym.symbol && s.source === src
      ).length
      heatmapData[sym.symbol][src] = count
    })
  })

  // Combine signals + reviews + decisions into activity feed (last 10)
  const activity = [
    ...(signals || []).map(s => ({
      type: 'signal',
      symbol: s.symbol,
      text: `Signal from ${s.source}`,
      direction: s.direction,
      timestamp: s.timestamp,
      id: `signal-${s.id}`,
    })),
    ...(reviews || []).map(r => ({
      type: 'review',
      symbol: r.symbol,
      text: `Review: ${r.gate} → ${r.decision}`,
      timestamp: r.created_at,
      id: `review-${r.id}`,
    })),
  ]
    .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))
    .slice(0, 10)

  const handleTriggerSchedule = async (scheduleName) => {
    setTriggeringSchedule(scheduleName)
    try {
      await api.triggerSchedule({ schedule_name: scheduleName })
      setTimeout(() => setTriggeringSchedule(null), 2000)
    } catch (err) {
      console.error('Trigger failed:', err)
      setTriggeringSchedule(null)
    }
  }

  // Calculate total position value
  const totalPositionValue = (positions || []).reduce((sum, p) => sum + (p.value || 0), 0)

  return (
    <div className="space-y-6">
      {/* Portfolio Summary Row */}
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-gray-800 border border-gray-700 rounded p-4">
          <div className="text-xs font-bold text-gray-400 uppercase tracking-wider">Total Position Value</div>
          <div className="text-2xl font-bold text-emerald-400 mt-2">
            ${totalPositionValue.toFixed(0)}
          </div>
          <div className="text-xs text-gray-500 mt-1">{(positions || []).length} open positions</div>
        </div>

        <div className="bg-gray-800 border border-gray-700 rounded p-4">
          <div className="text-xs font-bold text-gray-400 uppercase tracking-wider">Active Signals (24h)</div>
          <div className="text-2xl font-bold text-emerald-400 mt-2">
            {recentSignals.length}
          </div>
          <div className="text-xs text-gray-500 mt-1">out of {(signals || []).length} total</div>
        </div>

        <div className="bg-gray-800 border border-gray-700 rounded p-4">
          <div className="text-xs font-bold text-gray-400 uppercase tracking-wider">Pending Reviews</div>
          <div className={`text-2xl font-bold mt-2 ${pendingReviews.length > 0 ? 'text-yellow-400' : 'text-emerald-400'}`}>
            {pendingReviews.length}
          </div>
          <div className="text-xs text-gray-500 mt-1">{(reviews || []).length} reviewed</div>
        </div>
      </div>

      {/* Top Movers */}
      {topSymbols.length > 0 && (
        <div className="bg-gray-800 border border-gray-700 rounded p-4">
          <div className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-4">Top Movers (by signal activity)</div>
          <div className="space-y-2">
            {topSymbols.map(sym => {
              const latest = (signals || [])
                .filter(s => s.symbol === sym.symbol)
                .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))[0]

              return (
                <div key={sym.symbol} className="flex items-center justify-between bg-gray-700/30 rounded px-3 py-2 border border-gray-700/50">
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <SymbolLink symbol={sym.symbol} />
                      <span className="text-xs bg-gray-700 text-gray-300 px-2 py-0.5 rounded">
                        {sym.total} signals
                      </span>
                      {latest && (
                        <span className={`text-xs px-2 py-0.5 rounded ${
                          latest.direction === 'bullish' ? 'bg-emerald-900 text-emerald-300' :
                          latest.direction === 'bearish' ? 'bg-red-900 text-red-300' :
                          'bg-gray-700 text-gray-300'
                        }`}>
                          {latest.direction}
                        </span>
                      )}
                    </div>
                    <div className="text-xs text-gray-500 mt-1">
                      {sym.bullish} bullish, {sym.bearish} bearish, {sym.neutral} neutral
                    </div>
                  </div>
                  <div className="flex gap-1">
                    <a href={`/tickers/${sym.symbol}`} className="text-xs bg-emerald-700 hover:bg-emerald-600 text-white px-2 py-1 rounded">
                      Deep Dive
                    </a>
                    <a href={`/lattice/${sym.symbol}`} className="text-xs bg-blue-700 hover:bg-blue-600 text-white px-2 py-1 rounded">
                      Lattice
                    </a>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Signals Heatmap */}
      {topSymbols.length > 0 && (
        <div className="bg-gray-800 border border-gray-700 rounded p-4">
          <div className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-4">Signal Heatmap (sources × symbols)</div>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr>
                  <th className="text-left py-2 px-2 text-gray-400">Source</th>
                  {topSymbols.map(sym => (
                    <th key={sym.symbol} className="text-center py-2 px-2 text-gray-400 font-mono">
                      {sym.symbol}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {sources.map(src => (
                  <tr key={src} className="border-t border-gray-700">
                    <td className="text-left py-2 px-2 text-gray-400 font-mono">{src}</td>
                    {topSymbols.map(sym => {
                      const count = heatmapData[sym.symbol]?.[src] || 0
                      const maxCount = Math.max(...topSymbols.map(s => heatmapData[s.symbol]?.[src] || 0))
                      const intensity = maxCount > 0 ? count / maxCount : 0
                      const baseColor = src === 'reddit' ? 'emerald' : src === 'news' ? 'blue' : 'amber'
                      const bgOpacity = count === 0 ? 0.1 : Math.max(0.3, intensity * 0.8)
                      const bgClass = `bg-${baseColor}-900 opacity-${Math.round(bgOpacity * 100)}`

                      return (
                        <td
                          key={`${sym.symbol}-${src}`}
                          className={`text-center py-2 px-2 font-mono text-sm ${
                            count > 0 ? `bg-${baseColor}-900 text-${baseColor}-200` : 'bg-gray-700/30 text-gray-500'
                          }`}
                          style={{
                            backgroundColor: count > 0
                              ? `hsl(${baseColor === 'emerald' ? 160 : baseColor === 'blue' ? 210 : 45}, 70%, ${40 - intensity * 20}%)`
                              : 'transparent',
                          }}
                        >
                          {count > 0 ? count : '—'}
                        </td>
                      )
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Scheduler Status */}
      {scheduler && (
        <div className="bg-gray-800 border border-gray-700 rounded p-4">
          <div className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-4">Scheduler Status</div>
          <div className="space-y-2">
            {(scheduler.schedules || []).map(sched => (
              <div key={sched.name} className="flex items-center justify-between bg-gray-700/30 rounded px-3 py-2 border border-gray-700/50">
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-sm text-gray-300">{sched.name}</span>
                    <span className={`text-xs px-2 py-0.5 rounded ${
                      sched.enabled ? 'bg-emerald-900 text-emerald-300' : 'bg-gray-700 text-gray-400'
                    }`}>
                      {sched.enabled ? 'Enabled' : 'Disabled'}
                    </span>
                  </div>
                  <div className="text-xs text-gray-500 mt-1">
                    Interval: {sched.interval || sched.cron || '—'} | Last: {formatTime(sched.last_run_at)} | Next: {formatTime(sched.next_run_at)}
                  </div>
                </div>
                <button
                  onClick={() => handleTriggerSchedule(sched.name)}
                  disabled={triggeringSchedule === sched.name}
                  className="text-xs bg-blue-700 hover:bg-blue-600 disabled:bg-gray-700 text-white px-2 py-1 rounded whitespace-nowrap"
                >
                  {triggeringSchedule === sched.name ? 'Running…' : 'Trigger'}
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recent Activity Feed */}
      {activity.length > 0 && (
        <div className="bg-gray-800 border border-gray-700 rounded p-4">
          <div className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-4">Recent Activity</div>
          <div className="space-y-1">
            {activity.map(item => (
              <div key={item.id} className="flex items-center gap-2 text-xs py-1 border-b border-gray-700/50 last:border-0">
                <span className="text-gray-500">{formatTime(item.timestamp)}</span>
                {item.type === 'signal' && (
                  <>
                    <span className={`px-1.5 py-0.5 rounded text-xs font-mono ${
                      item.direction === 'bullish' ? 'bg-emerald-900 text-emerald-300' :
                      item.direction === 'bearish' ? 'bg-red-900 text-red-300' :
                      'bg-gray-700 text-gray-300'
                    }`}>
                      {item.direction}
                    </span>
                    <SymbolLink symbol={item.symbol} />
                    <span className="text-gray-500">{item.text}</span>
                  </>
                )}
                {item.type === 'review' && (
                  <>
                    <span className="bg-blue-900 text-blue-300 px-1.5 py-0.5 rounded text-xs font-mono">Review</span>
                    <SymbolLink symbol={item.symbol} />
                    <span className="text-gray-500">{item.text}</span>
                  </>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Quick Actions Bar */}
      <div className="bg-gray-800 border border-gray-700 rounded p-4">
        <div className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-4">Quick Actions</div>
        <div className="flex gap-2 flex-wrap">
          <button
            onClick={async () => {
              setQuickAction('collect')
              setQuickActionMsg(null)
              try {
                await api.createTask({ task_type: 'collect' })
                setQuickActionMsg({ type: 'success', text: 'Collection started — check Task Queue for progress' })
              } catch (err) {
                setQuickActionMsg({ type: 'error', text: `Failed: ${err.message}` })
              }
              setQuickAction(null)
              setTimeout(() => setQuickActionMsg(null), 5000)
            }}
            disabled={quickAction === 'collect'}
            className="text-sm bg-emerald-700 hover:bg-emerald-600 disabled:bg-gray-700 disabled:text-gray-500 text-white px-4 py-2 rounded font-mono"
          >
            {quickAction === 'collect' ? 'Starting…' : '→ Run Collect'}
          </button>
          <button
            onClick={async () => {
              setQuickAction('analyze')
              setQuickActionMsg(null)
              try {
                await api.createTask({ task_type: 'analyze' })
                setQuickActionMsg({ type: 'success', text: 'Analysis started — check Task Queue for progress' })
              } catch (err) {
                setQuickActionMsg({ type: 'error', text: `Failed: ${err.message}` })
              }
              setQuickAction(null)
              setTimeout(() => setQuickActionMsg(null), 5000)
            }}
            disabled={quickAction === 'analyze'}
            className="text-sm bg-blue-700 hover:bg-blue-600 disabled:bg-gray-700 disabled:text-gray-500 text-white px-4 py-2 rounded font-mono"
          >
            {quickAction === 'analyze' ? 'Starting…' : '⚙ Run Analyze'}
          </button>
          <a
            href="/instruments"
            className="text-sm bg-purple-700 hover:bg-purple-600 text-white px-4 py-2 rounded font-mono inline-block"
          >
            + Add Instrument
          </a>
        </div>
        {quickActionMsg && (
          <div className={`mt-3 text-xs px-3 py-2 rounded ${quickActionMsg.type === 'success' ? 'bg-emerald-900 text-emerald-400' : 'bg-red-900 text-red-400'}`}>
            {quickActionMsg.text}
          </div>
        )}
      </div>
    </div>
  )
}
