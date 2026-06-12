import { useParams, useNavigate } from 'react-router-dom'
import { api, ApiError } from '../api'
import { usePolling } from '../hooks'

const DOMAIN_COLORS = { public: '#3b82f6', private: '#a855f7', crypto: '#f59e0b' }
const LIFECYCLE_COLORS = { emerging: '#6366f1', validating: '#f59e0b', confirmed: '#10b981', saturated: '#6b7280' }
const SOURCE_COLORS = {
  reddit: '#f97316', sec_edgar: '#3b82f6', google_trends: '#a855f7',
  github: '#10b981', news: '#6b7280', yfinance: '#eab308',
  coingecko: '#f59e0b', defillama: '#8b5cf6', hiring: '#ec4899',
  patent: '#14b8a6', appstore: '#f43f5e', web_presence: '#06b6d4',
}

function Badge({ label, colorMap }) {
  if (!label) return null
  const color = (colorMap || {})[label] || '#6b7280'
  return (
    <span className="px-1.5 py-0.5 text-[9px] uppercase tracking-wider font-semibold rounded"
      style={{ background: `${color}20`, color }}>{label}</span>
  )
}

function TrendRing({ score, size = 56 }) {
  const radius = (size - 6) / 2
  const circ = 2 * Math.PI * radius
  const offset = circ - (Math.min(score, 100) / 100) * circ
  const color = score >= 60 ? '#10b981' : score >= 30 ? '#f59e0b' : '#6b7280'
  return (
    <div className="relative flex-shrink-0" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size/2} cy={size/2} r={radius} fill="none" stroke="#1f2937" strokeWidth="3" />
        <circle cx={size/2} cy={size/2} r={radius} fill="none" stroke={color} strokeWidth="3"
          strokeDasharray={circ} strokeDashoffset={offset} strokeLinecap="round" />
      </svg>
      <div className="absolute inset-0 flex items-center justify-center">
        <span className="text-xs font-bold" style={{ color }}>{Math.round(score)}</span>
      </div>
    </div>
  )
}

function SourceBar({ label, value, maxVal }) {
  const pct = maxVal > 0 ? (value / maxVal) * 100 : 0
  const color = SOURCE_COLORS[label] || '#6b7280'
  return (
    <div className="flex items-center gap-2">
      <span className="text-[10px] text-gray-500 w-24 truncate">{label}</span>
      <div className="flex-1 h-2 rounded-full bg-gray-800 overflow-hidden">
        <div className="h-full rounded-full transition-all" style={{ width: `${pct}%`, background: color }} />
      </div>
      <span className="text-[10px] text-gray-400 w-6 text-right">{value}</span>
    </div>
  )
}

function SignalTimeline({ data }) {
  if (!data || data.length === 0) return null
  // Collect all source keys
  const allSources = new Set()
  data.forEach(d => Object.keys(d).filter(k => k !== 'date').forEach(s => allSources.add(s)))
  const sources = Array.from(allSources).sort()

  // Stack bars
  const maxTotal = Math.max(...data.map(d => sources.reduce((s, k) => s + (d[k] || 0), 0)), 1)
  const barW = Math.max(Math.floor(600 / Math.max(data.length, 1)) - 4, 8)
  const h = 160

  return (
    <div className="overflow-x-auto">
      <svg width={Math.max(data.length * (barW + 4) + 40, 200)} height={h + 30}>
        {data.map((d, i) => {
          const x = 20 + i * (barW + 4)
          let yOffset = 0
          return (
            <g key={i}>
              {sources.map(src => {
                const val = d[src] || 0
                const barH = (val / maxTotal) * h
                const y = h - yOffset - barH
                yOffset += barH
                return <rect key={src} x={x} y={y} width={barW} height={barH}
                  fill={SOURCE_COLORS[src] || '#6b7280'} rx="1" />
              })}
              {i % Math.max(Math.floor(data.length / 6), 1) === 0 && (
                <text x={x + barW/2} y={h + 16} textAnchor="middle" className="fill-gray-600 text-[8px]">
                  {d.date ? d.date.slice(5) : ''}
                </text>
              )}
            </g>
          )
        })}
      </svg>
      <div className="flex items-center gap-3 mt-2 justify-center flex-wrap">
        {sources.map(s => (
          <div key={s} className="flex items-center gap-1">
            <div className="w-2 h-2 rounded-sm" style={{ background: SOURCE_COLORS[s] || '#6b7280' }} />
            <span className="text-[9px] text-gray-500">{s}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

function SteppsRadar({ stepps }) {
  if (!stepps) return <div className="text-gray-500 text-[11px]">No STEPPS data</div>
  const dims = [
    { key: 'social_currency', label: 'Social Currency' },
    { key: 'triggers', label: 'Triggers' },
    { key: 'emotion', label: 'Emotion' },
    { key: 'public_visibility', label: 'Public' },
    { key: 'practical_value', label: 'Practical' },
    { key: 'stories', label: 'Stories' },
  ]
  const cx = 100, cy = 100, r = 70
  const n = dims.length

  // Radar polygon
  const getPoint = (i, val) => {
    const angle = (Math.PI * 2 * i) / n - Math.PI / 2
    return { x: cx + Math.cos(angle) * r * val, y: cy + Math.sin(angle) * r * val }
  }

  const points = dims.map((d, i) => getPoint(i, stepps[d.key] || 0))
  const polygon = points.map(p => `${p.x},${p.y}`).join(' ')

  return (
    <svg width="200" height="200" className="mx-auto">
      {/* Grid */}
      {[0.25, 0.5, 0.75, 1].map(level => (
        <polygon key={level}
          points={dims.map((_, i) => { const p = getPoint(i, level); return `${p.x},${p.y}` }).join(' ')}
          fill="none" stroke="#1f2937" strokeWidth="0.5" />
      ))}
      {/* Axes */}
      {dims.map((_, i) => {
        const p = getPoint(i, 1)
        return <line key={i} x1={cx} y1={cy} x2={p.x} y2={p.y} stroke="#1f2937" strokeWidth="0.5" />
      })}
      {/* Data */}
      <polygon points={polygon} fill="#10b98133" stroke="#10b981" strokeWidth="1.5" />
      {/* Labels */}
      {dims.map((d, i) => {
        const p = getPoint(i, 1.2)
        return <text key={d.key} x={p.x} y={p.y} textAnchor="middle" dominantBaseline="middle"
          className="fill-gray-500 text-[8px]">{d.label}</text>
      })}
    </svg>
  )
}

// Safe percent: null/undefined/NaN -> '—' (avoids "NaN%" on partial theses).
const pct = (v, digits = 0) => {
  const n = Number(v)
  if (v == null || !Number.isFinite(n)) return '—'
  const p = n * 100
  return `${p > 0 ? '+' : ''}${p.toFixed(digits)}%`
}

export default function TickerTrend() {
  const { symbol } = useParams()
  const navigate = useNavigate()

  // Shared client + polling. 404 -> friendly "no data" message.
  const { data, loading, error: rawError } = usePolling(
    () => api.getTickerTrend(symbol), 30000, [symbol])
  const error = rawError
    ? (rawError instanceof ApiError && rawError.status === 404
        ? `No data found for ${symbol}`
        : (rawError.message || 'Failed to load ticker data'))
    : null

  if (loading && !data) return <div className="flex items-center justify-center h-64 text-gray-500 text-sm">Loading {symbol}...</div>
  if (error && !data) return (
    <div className="bg-[#111827]/80 border border-white/[0.06] rounded-xl p-8 text-center">
      <div className="text-gray-400 text-sm">{error}</div>
      <button onClick={() => navigate('/')} className="mt-3 text-[11px] text-emerald-400 hover:underline">Back to Trend Radar</button>
    </div>
  )
  if (!data) return null

  const sig = data.signals || {}
  const mosaic = data.mosaic || {}
  const thesis = data.thesis || {}
  const hitl = data.hitl || {}
  const sources_str = (sig.sources || []).join(', ')

  // Source breakdown for sidebar
  const sourceCounts = {}
  ;(data.signal_feed || []).forEach(s => { sourceCounts[s.source] = (sourceCounts[s.source] || 0) + 1 })
  const maxSourceCount = Math.max(...Object.values(sourceCounts), 1)

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-4">
          <div className="w-14 h-14 rounded-xl flex items-center justify-center text-lg font-bold"
            style={{ background: `${DOMAIN_COLORS[data.domain] || '#6b7280'}15`, color: DOMAIN_COLORS[data.domain] || '#6b7280' }}>
            {data.symbol.slice(0, 3)}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xl font-bold text-white">{data.symbol}</span>
              <span className="text-sm text-gray-400">{data.name}</span>
              <Badge label={data.domain} colorMap={DOMAIN_COLORS} />
              {thesis.lifecycle && <Badge label={thesis.lifecycle} colorMap={LIFECYCLE_COLORS} />}
            </div>
            <p className="text-[12px] text-gray-400 mt-1 max-w-2xl">{mosaic.narrative || `${sig.total} signals from ${sig.source_count} sources`}</p>
          </div>
        </div>
        <TrendRing score={data.trend_score} />
      </div>

      {/* Key metrics */}
      <div className="grid grid-cols-5 gap-3">
        {[
          { label: 'Signals', value: sig.total || 0, sub: `+${sig.recent_24h || 0} today`, color: 'text-blue-400' },
          { label: 'Coherence', value: mosaic.coherence ? `${Math.round(mosaic.coherence * 100)}%` : '—', color: 'text-emerald-400' },
          { label: 'Divergence', value: mosaic.divergence ? `${Math.round(mosaic.divergence * 100)}%` : '—', color: 'text-amber-400' },
          { label: 'Kelly Size', value: thesis.kelly ? `${(thesis.kelly * 100).toFixed(1)}%` : '—', color: 'text-purple-400' },
          { label: 'Sources', value: sig.source_count || 0, color: 'text-gray-300' },
        ].map(m => (
          <div key={m.label} className="bg-[#111827]/80 border border-white/[0.06] rounded-xl p-3 text-center">
            <div className={`text-lg font-bold ${m.color}`}>{m.value}</div>
            <div className="text-[9px] text-gray-500 uppercase tracking-wider mt-1">{m.label}</div>
            {m.sub && <div className="text-[9px] text-gray-600 mt-0.5">{m.sub}</div>}
          </div>
        ))}
      </div>

      {/* Signal timeline + STEPPS radar */}
      <div className="grid grid-cols-3 gap-4">
        <div className="col-span-2 bg-[#111827]/80 border border-white/[0.06] rounded-xl p-4">
          <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">Signal Volume by Source</h3>
          {data.signal_timeline && data.signal_timeline.length > 0 ? (
            <SignalTimeline data={data.signal_timeline} />
          ) : (
            <div className="text-gray-500 text-[11px] py-8 text-center">No timeline data available</div>
          )}
        </div>
        <div className="bg-[#111827]/80 border border-white/[0.06] rounded-xl p-4">
          <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">STEPPS Virality</h3>
          <SteppsRadar stepps={data.stepps} />
          {data.stepps && (
            <div className="text-center mt-2">
              <span className="text-lg font-bold text-emerald-400">{Math.round(data.stepps.composite * 100)}</span>
              <span className="text-[10px] text-gray-500 ml-1">composite ({data.stepps.sample_size} samples)</span>
            </div>
          )}
        </div>
      </div>

      {/* Signal feed */}
      <div className="bg-[#111827]/80 border border-white/[0.06] rounded-xl p-4">
        <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">Signal Feed</h3>
        {(data.signal_feed || []).length === 0 ? (
          <div className="text-gray-500 text-[11px] py-4 text-center">No recent signals</div>
        ) : (
          <div className="space-y-1 max-h-80 overflow-y-auto">
            {(data.signal_feed || []).map(sig => {
              const srcColor = SOURCE_COLORS[sig.source] || '#6b7280'
              const timeAgo = sig.timestamp ? formatTimeAgo(sig.timestamp) : ''
              return (
                <div key={sig.id} className="flex items-start gap-3 py-2 border-b border-white/[0.03] last:border-0">
                  <span className="text-[10px] text-gray-500 w-16 flex-shrink-0 pt-0.5">{timeAgo}</span>
                  <div className="w-2 h-2 rounded-full mt-1.5 flex-shrink-0" style={{ background: srcColor }} />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-[11px] font-medium text-gray-300">{sig.source}</span>
                      <span className="text-[9px] text-gray-600 uppercase">{sig.signal_type}</span>
                      {sig.direction && <Badge label={sig.direction} colorMap={{
                        bullish: '#10b981', bearish: '#ef4444', neutral: '#6b7280'
                      }} />}
                    </div>
                    <div className="text-[11px] text-gray-400 mt-0.5 truncate">{sig.summary}</div>
                  </div>
                  <div className="flex-shrink-0 w-14">
                    <div className="w-full h-1.5 rounded-full bg-gray-800 overflow-hidden">
                      <div className="h-full rounded-full bg-emerald-500" style={{ width: `${(sig.strength || 0) * 100}%` }} />
                    </div>
                    <div className="text-[8px] text-gray-600 text-right mt-0.5">{Math.round((sig.strength || 0) * 100)}%</div>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>

      {/* Thesis + HITL */}
      <div className="grid grid-cols-2 gap-4">
        {/* Thesis summary */}
        <div className="bg-[#111827]/80 border border-emerald-500/20 rounded-xl p-4">
          <h3 className="text-xs font-semibold text-emerald-400 uppercase tracking-wider mb-3">
            {thesis.status ? 'Active Thesis' : 'No Thesis Yet'}
          </h3>
          {thesis.status ? (
            <div className="space-y-3">
              <div className="flex justify-between text-[11px]">
                <span className="text-gray-500">ROI Range</span>
                <span className="text-gray-300">
                  <span className="text-red-400">{pct(thesis.roi_bear)}</span>
                  {' / '}
                  <span className="text-emerald-400">{pct(thesis.roi_base)}</span>
                  {' / '}
                  <span className="text-emerald-300">{pct(thesis.roi_bull)}</span>
                </span>
              </div>
              <div className="flex justify-between text-[11px]">
                <span className="text-gray-500">Kelly Fraction</span>
                <span className="text-purple-400 font-semibold">{pct(thesis.kelly, 1)}</span>
              </div>
              <div className="flex justify-between text-[11px]">
                <span className="text-gray-500">Lifecycle</span>
                {thesis.lifecycle ? <Badge label={thesis.lifecycle} colorMap={LIFECYCLE_COLORS} /> : <span className="text-gray-600">—</span>}
              </div>
              <div className="flex justify-between text-[11px]">
                <span className="text-gray-500">Status</span>
                <span className="text-gray-300">{thesis.status}</span>
              </div>
            </div>
          ) : (
            <div className="text-[11px] text-gray-500">Run analysis to generate a thesis for this ticker.</div>
          )}
        </div>

        {/* HITL */}
        <div className="bg-[#111827]/80 border border-white/[0.06] rounded-xl p-4">
          <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">HITL Decision</h3>
          {hitl.latest_review && hitl.latest_review.gate ? (
            <div className="space-y-2 mb-4">
              <div className="flex justify-between text-[11px]">
                <span className="text-gray-500">Last Gate</span>
                <span className="text-gray-300">{hitl.latest_review.gate}</span>
              </div>
              <div className="flex justify-between text-[11px]">
                <span className="text-gray-500">Decision</span>
                <span className="text-gray-300">{hitl.latest_review.decision}</span>
              </div>
              {hitl.latest_review.score != null && (
                <div className="flex justify-between text-[11px]">
                  <span className="text-gray-500">Score</span>
                  <span className="text-gray-300">{hitl.latest_review.score} / {hitl.latest_review.threshold}</span>
                </div>
              )}
            </div>
          ) : (
            <div className="text-[11px] text-gray-500 mb-4">No reviews yet for this ticker.</div>
          )}
          <div className="flex gap-2">
            <button onClick={() => navigate(`/gate/review?symbol=${data.symbol}`)}
              className="flex-1 py-2 text-[11px] font-semibold rounded-lg bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30 transition-colors">
              Review
            </button>
            <button onClick={() => navigate(`/mosaic/${data.symbol}`)}
              className="flex-1 py-2 text-[11px] font-semibold rounded-lg bg-white/[0.05] text-gray-400 hover:bg-white/[0.08] transition-colors">
              Mosaic Workbench
            </button>
          </div>
        </div>
      </div>

      {/* Position (if open) */}
      {data.position && (
        <div className="bg-[#111827]/80 border border-blue-500/20 rounded-xl p-4">
          <h3 className="text-xs font-semibold text-blue-400 uppercase tracking-wider mb-3">Open Position</h3>
          <div className="grid grid-cols-4 gap-4 text-[11px]">
            <div><span className="text-gray-500">Direction</span><div className="text-white mt-0.5">{data.position.direction}</div></div>
            <div><span className="text-gray-500">Allocation</span><div className="text-white mt-0.5">{data.position.allocation_pct}%</div></div>
            <div><span className="text-gray-500">Entry Price</span><div className="text-white mt-0.5">${data.position.entry_price}</div></div>
            <div><span className="text-gray-500">PnL</span><div className={`mt-0.5 ${data.position.pnl_pct >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>{data.position.pnl_pct}%</div></div>
          </div>
        </div>
      )}
    </div>
  )
}

function formatTimeAgo(timestamp) {
  try {
    const ts = new Date(timestamp)
    const now = new Date()
    const diffMs = now - ts
    const diffMins = Math.floor(diffMs / 60000)
    if (diffMins < 1) return 'just now'
    if (diffMins < 60) return `${diffMins}m ago`
    const diffHrs = Math.floor(diffMins / 60)
    if (diffHrs < 24) return `${diffHrs}h ago`
    const diffDays = Math.floor(diffHrs / 24)
    return `${diffDays}d ago`
  } catch {
    return ''
  }
}
