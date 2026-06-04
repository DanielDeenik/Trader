import { useParams, Link } from 'react-router-dom'
import { useState, useMemo } from 'react'
import { useApi } from '../hooks'
import { api } from '../api'
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend,
} from 'recharts'

const LIFECYCLE_STAGES = {
  emerging: { label: 'Emerging', color: '#10b981', bgColor: '#064e3b' },
  validating: { label: 'Validating', color: '#3b82f6', bgColor: '#1e3a8a' },
  confirmed: { label: 'Confirmed', color: '#f59e0b', bgColor: '#78350f' },
  saturated: { label: 'Saturated', color: '#ef4444', bgColor: '#7f1d1d' },
}

export default function MosaicWorkbench() {
  const { symbol } = useParams()
  const { data: result, loading, error, refetch } = useApi(() => api.getEngineOutput(symbol), [symbol])
  const [rerunning, setRerunning] = useState(false)
  const [msg, setMsg] = useState(null)

  const handleRerun = async () => {
    setRerunning(true)
    setMsg(null)
    try {
      await api.runAnalysis({ symbol })
      await refetch()
      setMsg({ type: 'success', text: 'Engines re-run — workbench updated' })
    } catch (err) {
      setMsg({ type: 'error', text: `Failed: ${err.message}` })
    }
    setRerunning(false)
    setTimeout(() => setMsg(null), 5000)
  }

  const handleCreatePosition = async () => {
    try {
      await api.createPosition({ symbol, size: 0.02 })
      setMsg({ type: 'success', text: 'Position created — proceed to portfolio' })
    } catch (err) {
      setMsg({ type: 'error', text: `Failed: ${err.message}` })
    }
    setTimeout(() => setMsg(null), 5000)
  }

  if (loading) return <div className="text-gray-400 text-sm">Loading workbench for {symbol}...</div>
  if (error) return <div className="text-red-400 text-sm">Error: {error.message}</div>

  const engines = result?.engines || result || {}

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center gap-3 flex-wrap">
        <Link to={`/tickers/${symbol}`} className="text-xs text-gray-500 hover:text-gray-300 no-underline">
          &larr; Engine View
        </Link>
        <span className="text-2xl font-bold text-emerald-400 font-mono">{symbol}</span>
        <span className="text-xs px-2 py-0.5 rounded bg-gray-700 text-gray-300">Mosaic Workbench</span>
        <div className="ml-auto flex gap-2 flex-wrap">
          <button
            onClick={handleCreatePosition}
            className="text-xs px-3 py-1.5 rounded bg-emerald-900 hover:bg-emerald-800 text-emerald-400 transition-colors border border-emerald-700"
          >
            + Create Position
          </button>
          <button
            onClick={handleRerun}
            disabled={rerunning}
            className="text-xs px-3 py-1.5 rounded bg-orange-900 hover:bg-orange-800 disabled:bg-gray-700 disabled:text-gray-500 text-orange-400 transition-colors border border-orange-700"
          >
            {rerunning ? 'Running…' : 'Re-run Engines'}
          </button>
          <Link
            to={`/deepdive/${symbol}`}
            className="text-xs px-3 py-1.5 rounded bg-blue-900 hover:bg-blue-800 text-blue-400 no-underline transition-colors border border-blue-700"
          >
            Deep Dive
          </Link>
          <Link
            to={`/lattice/${symbol}`}
            className="text-xs px-3 py-1.5 rounded bg-purple-900 hover:bg-purple-800 text-purple-400 no-underline transition-colors border border-purple-700"
          >
            Lattice
          </Link>
        </div>
      </div>

      {msg && (
        <div className={`text-xs px-3 py-2 rounded ${msg.type === 'success' ? 'bg-emerald-900 text-emerald-400' : 'bg-red-900 text-red-400'}`}>
          {msg.text}
        </div>
      )}

      {/* Gold Rush Stage */}
      {engines.gold_rush_scorer && (
        <GoldRushPanel data={engines.gold_rush_scorer} />
      )}

      {/* Asymmetry Scanner */}
      {engines.asymmetry_scanner && (
        <AsymmetryPanel data={engines.asymmetry_scanner} />
      )}

      {/* Conviction Scorecard */}
      {engines.conviction_scorer && (
        <ConvictionPanel data={engines.conviction_scorer} />
      )}

      {/* Catalyst Timeline */}
      {engines.catalyst_engine?.catalysts?.length > 0 && (
        <CatalystPanel data={engines.catalyst_engine} />
      )}

      {/* Kelly Sizing */}
      {engines.kelly_sizer && (
        <KellySizerPanel data={engines.kelly_sizer} />
      )}
    </div>
  )
}

/* Gold Rush Lifecycle Panel */
function GoldRushPanel({ data }) {
  const stage = data.stage || 'emerging'
  const config = LIFECYCLE_STAGES[stage] || { label: stage, color: '#9ca3af', bgColor: '#374151' }
  const stages = ['emerging', 'validating', 'confirmed', 'saturated']
  const currentIdx = stages.indexOf(stage)

  return (
    <div className="bg-gray-800 border border-gray-700 rounded p-4">
      <h3 className="text-sm font-bold text-gray-200 mb-3">Gold Rush Lifecycle</h3>

      {/* Stage Progression */}
      <div className="flex items-center gap-2 mb-4">
        {stages.map((s, idx) => {
          const c = LIFECYCLE_STAGES[s]
          const isActive = idx === currentIdx
          return (
            <div key={s} className="flex-1">
              <div
                className="rounded py-2 px-1 text-center text-xs font-bold transition-all"
                style={{
                  backgroundColor: isActive ? c.bgColor : idx < currentIdx ? '#1f2937' : '#111827',
                  color: isActive ? c.color : '#6b7280',
                  border: `1px solid ${isActive ? c.color : '#374151'}`,
                }}
              >
                {c.label}
              </div>
            </div>
          )
        })}
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
        {data.confidence != null && (
          <StatBox label="Confidence" value={`${(data.confidence * 100).toFixed(0)}%`} />
        )}
        {data.velocity != null && (
          <StatBox label="Velocity" value={data.velocity.toFixed(2)} />
        )}
        {data.breadth != null && (
          <StatBox label="Breadth" value={data.breadth.toFixed(2)} />
        )}
        {data.acceleration != null && (
          <StatBox label="Accel" value={data.acceleration.toFixed(2)} />
        )}
      </div>
    </div>
  )
}

/* Asymmetry Scanner Panel */
function AsymmetryPanel({ data }) {
  return (
    <div className="bg-gray-800 border border-gray-700 rounded p-4">
      <h3 className="text-sm font-bold text-gray-200 mb-3">Information Asymmetry</h3>

      <div className="grid grid-cols-2 gap-3">
        {data.asymmetry_score != null && (
          <div className="bg-gray-900 rounded p-3 border border-gray-700">
            <div className="text-xs text-gray-400 mb-2">Asymmetry Score</div>
            <div className="text-2xl font-bold text-emerald-400 mb-2">{data.asymmetry_score.toFixed(2)}</div>
            <div className="w-full bg-gray-800 rounded h-1">
              <div
                className="h-1 rounded bg-emerald-500"
                style={{ width: `${Math.min(data.asymmetry_score * 10, 100)}%` }}
              />
            </div>
          </div>
        )}

        {data.gap_pct != null && (
          <div className="bg-gray-900 rounded p-3 border border-gray-700">
            <div className="text-xs text-gray-400 mb-2">Info Gap</div>
            <div className="text-2xl font-bold text-amber-400">{(data.gap_pct * 100).toFixed(1)}%</div>
            <p className="text-xs text-gray-500 mt-1">Retail ahead of market</p>
          </div>
        )}
      </div>
    </div>
  )
}

/* Conviction Scorecard */
function ConvictionPanel({ data }) {
  const total = data.total || 0
  const dims = data.dimensions || {}

  return (
    <div className="bg-gray-800 border border-gray-700 rounded p-4">
      <h3 className="text-sm font-bold text-gray-200 mb-3">Conviction Scorecard</h3>

      <div className="mb-4 pb-4 border-b border-gray-700">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs text-gray-400">Total Conviction</span>
          <span className="text-2xl font-bold text-emerald-400 font-mono">{total.toFixed(1)}</span>
        </div>
        <div className="w-full bg-gray-900 rounded h-2">
          <div
            className="h-2 rounded bg-emerald-500"
            style={{ width: `${Math.min(total, 100)}%` }}
          />
        </div>
      </div>

      {/* Dimension Breakdown */}
      {Object.keys(dims).length > 0 && (
        <div className="space-y-2">
          <div className="text-xs text-gray-500 uppercase tracking-wider mb-2">Dimensions</div>
          {Object.entries(dims).slice(0, 5).map(([key, val]) => (
            <div key={key}>
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs text-gray-400">{key.replace(/_/g, ' ')}</span>
                <span className="text-xs font-mono text-gray-300">
                  {typeof val === 'number' ? val.toFixed(2) : val}
                </span>
              </div>
              {typeof val === 'number' && (
                <div className="w-full bg-gray-900 rounded h-1">
                  <div
                    className="h-1 rounded bg-emerald-500/60"
                    style={{ width: `${Math.min(val * 10, 100)}%` }}
                  />
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

/* Catalyst Timeline */
function CatalystPanel({ data }) {
  const catalysts = data.catalysts || []
  const sorted = useMemo(
    () => [...catalysts].sort((a, b) => (b.confidence || 0) - (a.confidence || 0)),
    [catalysts]
  )

  if (!sorted.length) return null

  return (
    <div className="bg-gray-800 border border-gray-700 rounded p-4">
      <h3 className="text-sm font-bold text-gray-200 mb-3">Catalyst Timeline</h3>

      <div className="space-y-2">
        {sorted.slice(0, 5).map((cat, idx) => (
          <div key={idx} className="bg-gray-900 rounded p-2 border border-gray-700">
            <div className="flex items-start justify-between mb-1">
              <span className="text-xs font-semibold text-emerald-400">{cat.name}</span>
              {cat.confidence != null && (
                <span className="text-xs font-mono text-gray-400">
                  {(cat.confidence * 100).toFixed(0)}%
                </span>
              )}
            </div>
            {cat.date && <div className="text-xs text-gray-500">{cat.date}</div>}
          </div>
        ))}
        {sorted.length > 5 && (
          <div className="text-xs text-gray-600 text-center py-1">+{sorted.length - 5} more catalysts</div>
        )}
      </div>
    </div>
  )
}

/* Kelly Criterion Sizer */
function KellySizerPanel({ data }) {
  return (
    <div className="bg-gray-800 border border-gray-700 rounded p-4">
      <h3 className="text-sm font-bold text-gray-200 mb-3">Kelly Criterion Sizing</h3>

      <div className="grid grid-cols-2 gap-3">
        {data.kelly_fraction != null && (
          <div className="bg-gray-900 rounded p-3 border border-gray-700">
            <div className="text-xs text-gray-400 mb-1">Kelly f*</div>
            <div className="text-xl font-bold text-emerald-400 font-mono">
              {(data.kelly_fraction * 100).toFixed(1)}%
            </div>
          </div>
        )}

        {data.recommended_size != null && (
          <div className="bg-gray-900 rounded p-3 border border-gray-700">
            <div className="text-xs text-gray-400 mb-1">Suggested Size</div>
            <div className="text-xl font-bold text-emerald-400 font-mono">
              {(data.recommended_size * 100).toFixed(1)}%
            </div>
          </div>
        )}

        {data.confidence != null && (
          <div className="bg-gray-900 rounded p-3 border border-gray-700">
            <div className="text-xs text-gray-400 mb-1">Confidence</div>
            <div className="text-xl font-bold text-blue-400 font-mono">
              {data.confidence.toFixed(2)}
            </div>
          </div>
        )}

        {data.sharpe_ratio != null && (
          <div className="bg-gray-900 rounded p-3 border border-gray-700">
            <div className="text-xs text-gray-400 mb-1">Sharpe Ratio</div>
            <div className="text-xl font-bold text-purple-400 font-mono">
              {data.sharpe_ratio.toFixed(2)}
            </div>
          </div>
        )}
      </div>

      {data.notes && (
        <div className="mt-3 pt-3 border-t border-gray-700 text-xs text-gray-400">
          {data.notes}
        </div>
      )}
    </div>
  )
}

/* Utility: Small stat box */
function StatBox({ label, value }) {
  return (
    <div className="bg-gray-900 rounded p-2 border border-gray-700">
      <div className="text-xs text-gray-500 mb-1">{label}</div>
      <div className="text-sm font-bold text-emerald-400 font-mono">{value}</div>
    </div>
  )
}
