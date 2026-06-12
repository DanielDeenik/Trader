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

function TrendRing({ score, size = 48 }) {
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
        <span className="text-[11px] font-bold" style={{ color }}>{Math.round(score)}</span>
      </div>
    </div>
  )
}

function MiniSparkline({ data, color = '#10b981' }) {
  if (!data || data.length < 2) return <div className="w-full h-8" />
  const min = Math.min(...data)
  const max = Math.max(...data)
  const range = max - min || 1
  const w = 96
  const h = 32
  const points = data.map((v, i) => `${(i / (data.length - 1)) * w},${h - ((v - min) / range) * h}`).join(' ')
  return (
    <svg width={w} height={h} className="flex-shrink-0">
      <polyline points={points} fill="none" stroke={color} strokeWidth="1.5" strokeLinejoin="round" />
    </svg>
  )
}

export default function TrendRadar() {
  const navigate = useNavigate()
  const [domainFilter, setDomainFilter] = useState('all')

  // One source, shared client (auth headers + ApiError), shared polling hook.
  const { data, loading, error, refetch } = usePolling(async () => {
    const params = domainFilter !== 'all' ? { domain: domainFilter } : {}
    const [stats, tickers, alerts] = await Promise.all([
      api.getTrendStats(),
      api.getTrendingTickers({ limit: 30, ...params }),
      api.getDivergenceAlerts({ limit: 5 }),
    ])
    return { stats, tickers, alerts }
  }, 15000, [domainFilter])

  const stats = data?.stats
  const tickers = data?.tickers || []
  const alerts = data?.alerts || []

  if (loading && !data) return <div className="flex items-center justify-center h-64 text-gray-500 text-sm">Loading trends...</div>
  if (error && !data) return (
    <div className="flex flex-col items-center justify-center h-64 gap-3 text-sm">
      <div className="text-red-400">Couldn't load trends — {error.message}</div>
      <button onClick={refetch} className="px-3 py-1.5 rounded bg-white/[0.06] hover:bg-white/[0.1] text-gray-300">Retry</button>
    </div>
  )

  return (
    <div className="space-y-5">
      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-4 gap-3">
          {[
            { label: 'Active Signals', value: stats.total_signals, sub: `+${stats.signals_24h} today`, color: 'text-blue-400' },
            { label: 'Trending Tickers', value: stats.trending_symbols, sub: `${stats.active_mosaics} with mosaics`, color: 'text-emerald-400' },
            { label: 'Theme Clusters', value: stats.theme_clusters, color: 'text-purple-400' },
            { label: 'HITL Queue', value: stats.pending_reviews, sub: `${stats.open_positions} positions`, color: 'text-amber-400' },
          ].map(s => (
            <div key={s.label} className="bg-[#111827]/80 border border-white/[0.06] rounded-xl p-4">
              <div className="text-[10px] uppercase tracking-wider text-gray-500 mb-1">{s.label}</div>
              <div className={`text-2xl font-bold ${s.color}`}>{s.value}</div>
              {s.sub && <div className="text-[11px] text-gray-500 mt-1">{s.sub}</div>}
            </div>
          ))}
        </div>
      )}

      {/* Divergence Alerts */}
      {alerts.length > 0 && (
        <div className="bg-[#111827]/80 border border-amber-500/20 rounded-xl p-4">
          <div className="flex items-center gap-2 mb-3">
            <div className="w-2 h-2 rounded-full bg-amber-400 animate-pulse" />
            <h3 className="text-xs font-semibold text-amber-400 uppercase tracking-wider">Divergence Alerts</h3>
            <span className="text-[10px] text-gray-500 ml-auto">Social chatter vs market pricing gap</span>
          </div>
          <div className="space-y-2">
            {alerts.map(t => (
              <div key={t.symbol} onClick={() => navigate(`/trend/${t.symbol}`)}
                className="flex items-center gap-4 p-3 rounded-lg bg-white/[0.02] hover:bg-white/[0.04] cursor-pointer transition-colors">
                <div className="w-10 h-10 rounded-lg flex items-center justify-center text-xs font-bold"
                  style={{ background: `${DOMAIN_COLORS[t.domain] || '#6b7280'}15`, color: DOMAIN_COLORS[t.domain] || '#6b7280' }}>
                  {t.symbol.slice(0, 4)}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-semibold text-white">{t.symbol}</span>
                    <Badge label={t.domain} colorMap={DOMAIN_COLORS} />
                    <Badge label={t.lifecycle} colorMap={LIFECYCLE_COLORS} />
                  </div>
                  <div className="text-[11px] text-gray-400 truncate mt-0.5">{t.narrative || 'No narrative yet'}</div>
                </div>
                <div className="text-right flex-shrink-0">
                  <div className="text-sm font-bold text-amber-400">{Math.round(t.divergence * 100)}%</div>
                  <div className="text-[10px] text-gray-500">divergence</div>
                </div>
                {t.sparkline && t.sparkline.length > 1 && (
                  <div className="flex-shrink-0"><MiniSparkline data={t.sparkline} color="#f59e0b" /></div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Trending Tickers */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Trending Tickers</h3>
          <div className="flex gap-1.5">
            {['all', 'public', 'private', 'crypto'].map(d => (
              <button key={d} onClick={() => setDomainFilter(d)}
                className={`text-[10px] px-2 py-1 rounded-md capitalize transition-colors ${
                  domainFilter === d ? 'bg-white/[0.1] text-white' : 'bg-white/[0.04] text-gray-400 hover:bg-white/[0.08]'
                }`}>{d}</button>
            ))}
          </div>
        </div>

        {tickers.length === 0 ? (
          <div className="bg-[#111827]/80 border border-white/[0.06] rounded-xl p-8 text-center">
            <div className="text-gray-500 text-sm">No trending tickers found</div>
            <div className="text-[11px] text-gray-600 mt-1">Run collection + analysis to populate signals</div>
          </div>
        ) : (
          <div className="space-y-1">
            {tickers.map((t, i) => {
              const sparkColor = t.direction === 'bullish' ? '#10b981' : t.direction === 'bearish' ? '#ef4444' : '#6b7280'
              return (
                <div key={t.symbol} onClick={() => navigate(`/trend/${t.symbol}`)}
                  className="flex items-center gap-4 p-3 rounded-xl bg-[#111827]/80 border border-white/[0.06] hover:border-white/[0.12] cursor-pointer transition-all">
                  <div className="text-gray-600 text-sm font-mono w-5 text-right">{i + 1}</div>
                  <TrendRing score={t.trend_score} />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-semibold text-white">{t.symbol}</span>
                      <span className="text-[11px] text-gray-500">{t.name}</span>
                      <Badge label={t.domain} colorMap={DOMAIN_COLORS} />
                      {t.lifecycle && <Badge label={t.lifecycle} colorMap={LIFECYCLE_COLORS} />}
                    </div>
                    <div className="text-[11px] text-gray-400 truncate mt-0.5">{t.narrative || `${t.signal_count} signals from ${t.source_count} sources`}</div>
                  </div>
                  <div className="flex items-center gap-6 flex-shrink-0">
                    <div className="text-center">
                      <div className="text-sm font-semibold text-white">{t.signal_count}</div>
                      <div className="text-[9px] text-gray-500">signals</div>
                    </div>
                    {t.coherence > 0 && (
                      <div className="text-center">
                        <div className="text-sm font-semibold text-emerald-400">{Math.round(t.coherence * 100)}%</div>
                        <div className="text-[9px] text-gray-500">coherence</div>
                      </div>
                    )}
                    {t.kelly > 0 && (
                      <div className="text-center">
                        <div className="text-sm font-semibold text-purple-400">{(t.kelly * 100).toFixed(1)}%</div>
                        <div className="text-[9px] text-gray-500">kelly</div>
                      </div>
                    )}
                    <div className="text-center w-6">
                      <div className="text-[10px] text-gray-500">{t.source_count}src</div>
                    </div>
                  </div>
                  {t.sparkline && t.sparkline.length > 1 && (
                    <div className="flex-shrink-0"><MiniSparkline data={t.sparkline} color={sparkColor} /></div>
                  )}
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
