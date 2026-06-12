import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api'
import { usePolling } from '../hooks'

const DOMAIN_COLORS = { public: '#3b82f6', private: '#a855f7', crypto: '#f59e0b' }
const LIFECYCLE_COLORS = { emerging: '#6366f1', validating: '#f59e0b', confirmed: '#10b981', saturated: '#6b7280' }

function Badge({ label, colorMap }) {
  if (!label) return null
  const color = (colorMap || {})[label] || '#6b7280'
  return (
    <span className="px-1.5 py-0.5 text-[9px] uppercase tracking-wider font-semibold rounded"
      style={{ background: `${color}20`, color }}>{label}</span>
  )
}

function TrendRing({ score, size = 40 }) {
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
        <span className="text-[10px] font-bold" style={{ color }}>{Math.round(score)}</span>
      </div>
    </div>
  )
}

function MiniTimeline({ data }) {
  if (!data || data.length < 2) return null
  const values = data.map(d => d.signals || 0)
  const max = Math.max(...values) || 1
  const w = 192
  const h = 48
  const points = values.map((v, i) => `${(i / (values.length - 1)) * w},${h - (v / max) * h}`).join(' ')
  return (
    <svg width={w} height={h}>
      <defs>
        <linearGradient id="tlGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#10b981" stopOpacity="0.3" />
          <stop offset="100%" stopColor="#10b981" stopOpacity="0" />
        </linearGradient>
      </defs>
      <polygon points={`0,${h} ${points} ${w},${h}`} fill="url(#tlGrad)" />
      <polyline points={points} fill="none" stroke="#10b981" strokeWidth="1.5" strokeLinejoin="round" />
    </svg>
  )
}

export default function SimilarTrends() {
  const navigate = useNavigate()
  const [sortBy, setSortBy] = useState('trend_score')

  // Shared client + polling (was a one-shot direct fetch with no auth/refresh).
  const { data, loading, error, refetch } = usePolling(
    () => api.getThemes({ limit: 20 }), 15000, [])
  const themes = data || []

  const sorted = [...themes].sort((a, b) => {
    if (sortBy === 'divergence') return (b.divergence_avg || 0) - (a.divergence_avg || 0)
    if (sortBy === 'signals') return (b.signal_count || 0) - (a.signal_count || 0)
    return (b.trend_score || 0) - (a.trend_score || 0)
  })

  if (loading && !data) return <div className="flex items-center justify-center h-64 text-gray-500 text-sm">Loading theme clusters...</div>
  if (error && !data) return (
    <div className="flex flex-col items-center justify-center h-64 gap-3 text-sm">
      <div className="text-red-400">Couldn't load theme clusters — {error.message}</div>
      <button onClick={refetch} className="px-3 py-1.5 rounded bg-white/[0.06] hover:bg-white/[0.1] text-gray-300">Retry</button>
    </div>
  )

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold text-white">Theme Clusters</h2>
          <p className="text-[11px] text-gray-500 mt-0.5">Tickers trending together — cross-domain signal amplification</p>
        </div>
        <div className="flex gap-1.5">
          {[
            { key: 'trend_score', label: 'trend score' },
            { key: 'divergence', label: 'divergence' },
            { key: 'signals', label: 'signal count' },
          ].map(s => (
            <button key={s.key} onClick={() => setSortBy(s.key)}
              className={`text-[10px] px-2 py-1 rounded-md transition-colors ${
                sortBy === s.key ? 'bg-white/[0.1] text-white' : 'bg-white/[0.04] text-gray-400 hover:bg-white/[0.08]'
              }`}>{s.label}</button>
          ))}
        </div>
      </div>

      {sorted.length === 0 ? (
        <div className="bg-[#111827]/80 border border-white/[0.06] rounded-xl p-8 text-center">
          <div className="text-gray-500 text-sm">No theme clusters found</div>
          <div className="text-[11px] text-gray-600 mt-1">Clusters form when 2+ tickers in the same sector have recent mosaics</div>
        </div>
      ) : (
        sorted.map(theme => (
          <div key={theme.theme} className="bg-[#111827]/80 border border-white/[0.06] rounded-xl p-5 hover:border-white/[0.12] transition-all">
            {/* Header */}
            <div className="flex items-start justify-between mb-4">
              <div className="flex items-center gap-3 flex-1">
                <TrendRing score={theme.trend_score} />
                <div className="min-w-0">
                  <h3 className="text-base font-semibold text-white">{theme.theme}</h3>
                  <div className="flex items-center gap-2 mt-0.5">
                    {theme.lifecycle && <Badge label={theme.lifecycle} colorMap={LIFECYCLE_COLORS} />}
                    <span className="text-[10px] text-gray-500">
                      {theme.signal_count} signals across {theme.ticker_count} tickers
                    </span>
                  </div>
                </div>
              </div>
              <div className="text-right flex-shrink-0">
                <div className="text-sm font-bold text-amber-400">{Math.round((theme.divergence_avg || 0) * 100)}%</div>
                <div className="text-[9px] text-gray-500">avg divergence</div>
              </div>
            </div>

            {/* Narrative */}
            {theme.narrative && (
              <p className="text-[12px] text-gray-400 leading-relaxed mb-4">{theme.narrative}</p>
            )}

            {/* Tickers + timeline */}
            <div className="flex items-center gap-4">
              <div className="flex-1">
                <div className="text-[9px] text-gray-500 uppercase tracking-wider mb-2">Related Tickers</div>
                <div className="flex flex-wrap gap-1.5">
                  {(theme.tickers || []).map(sym => (
                    <span key={sym} onClick={(e) => { e.stopPropagation(); navigate(`/trend/${sym}`) }}
                      className="px-2 py-1 text-[11px] font-mono font-semibold rounded-md bg-white/[0.06] text-gray-300 hover:bg-white/[0.1] cursor-pointer transition-colors">
                      {sym}
                    </span>
                  ))}
                </div>
              </div>
              {theme.timeline && theme.timeline.length > 1 && (
                <div className="flex-shrink-0">
                  <div className="text-[9px] text-gray-500 uppercase tracking-wider mb-1">Signal Trajectory</div>
                  <MiniTimeline data={theme.timeline} />
                </div>
              )}
            </div>

            {/* Sources */}
            {theme.sources && Object.keys(theme.sources).length > 0 && (
              <div className="flex items-center gap-4 mt-4 pt-3 border-t border-white/[0.04]">
                <div className="text-[9px] text-gray-500 uppercase tracking-wider">Sources:</div>
                {Object.entries(theme.sources).sort((a, b) => b[1] - a[1]).map(([src, count]) => (
                  <div key={src} className="flex items-center gap-1.5">
                    <div className="w-1 h-1 rounded-full bg-gray-500" />
                    <span className="text-[10px] text-gray-400">{src}</span>
                    <span className="text-[10px] text-gray-600">{count}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        ))
      )}
    </div>
  )
}
