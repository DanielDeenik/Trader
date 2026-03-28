import { useParams, Link } from 'react-router-dom'
import { useState } from 'react'
import { useApi } from '../hooks'
import { api } from '../api'
import { EngineCard } from '../components/EngineCard'

const ENGINE_LABELS = {
  sentiment_divergence: 'Sentiment Divergence',
  technical_analyzer: 'Technical Analyzer',
  kelly_sizer: 'Kelly Criterion Sizer',
  irr_simulator: 'IRR/MOIC Simulator',
  regulatory_moat: 'Regulatory Moat',
  cross_domain_amplifier: 'Cross-Domain Amplifier',
  stepps_classifier: 'STEPPS Classifier',
  gold_rush_scorer: 'Gold Rush Lifecycle',
  asymmetry_scanner: 'Information Asymmetry',
  catalyst_engine: 'Catalyst Timeline',
  conviction_scorer: 'Conviction Scorecard',
}

export default function TickerDetail() {
  const { symbol } = useParams()
  const { data: result, loading, error, refetch } = useApi(() => api.getEngineOutput(symbol), [symbol])
  const { data: signals } = useApi(() => api.getSignals({ symbol }), [symbol])
  const [rerunning, setRerunning] = useState(false)
  const [msg, setMsg] = useState(null)

  const handleRerun = async () => {
    setRerunning(true)
    setMsg(null)
    try {
      await api.runAnalysis({ symbol })
      await refetch()
      setMsg({ type: 'success', text: 'Engines re-run — results updated' })
    } catch (err) {
      setMsg({ type: 'error', text: `Failed: ${err.message}` })
    }
    setRerunning(false)
    setTimeout(() => setMsg(null), 5000)
  }

  const handleAddWatchlist = async () => {
    try {
      await api.addToWatchlist(symbol)
      setMsg({ type: 'success', text: `${symbol} added to watchlist` })
    } catch (err) {
      setMsg({ type: 'error', text: err.message })
    }
    setTimeout(() => setMsg(null), 5000)
  }

  if (loading) return <div className="text-gray-400 text-sm">Running engines for {symbol}...</div>
  if (error) return <div className="text-red-400 text-sm">Error: {error.message}</div>

  const engines = result?.engines || result || {}

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3 flex-wrap">
        <span className="text-lg font-bold text-emerald-400 font-mono">{symbol}</span>
        <span className="text-xs text-gray-400">{(signals || []).length} signals</span>
        <div className="ml-auto flex gap-2 flex-wrap">
          <button
            onClick={handleRerun}
            disabled={rerunning}
            className="text-xs px-3 py-1 rounded bg-orange-600 hover:bg-orange-500 disabled:bg-gray-700 disabled:text-gray-500 text-white transition-colors"
          >
            {rerunning ? 'Running…' : 'Re-run Engines'}
          </button>
          <button
            onClick={handleAddWatchlist}
            className="text-xs px-3 py-1 rounded bg-yellow-600 hover:bg-yellow-500 text-white transition-colors"
          >
            + Watchlist
          </button>
          <Link
            to={`/mosaic/${symbol}`}
            className="text-xs px-3 py-1 rounded bg-purple-600 hover:bg-purple-500 text-white no-underline transition-colors"
          >
            Mosaic Workbench &rarr;
          </Link>
          <Link
            to={`/deepdive/${symbol}`}
            className="text-xs px-3 py-1 rounded bg-emerald-600 hover:bg-emerald-500 text-white no-underline transition-colors"
          >
            Deep Dive &rarr;
          </Link>
          <Link
            to={`/lattice/${symbol}`}
            className="text-xs px-3 py-1 rounded bg-blue-600 hover:bg-blue-500 text-white no-underline transition-colors"
          >
            Lattice &rarr;
          </Link>
        </div>
      </div>

      {msg && (
        <div className={`text-xs px-3 py-2 rounded ${msg.type === 'success' ? 'bg-emerald-900 text-emerald-400' : 'bg-red-900 text-red-400'}`}>
          {msg.text}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
        {Object.entries(ENGINE_LABELS).map(([key, label]) => (
          <EngineCard
            key={key}
            name={label}
            data={engines[key]}
            error={engines[key]?.error}
          />
        ))}
      </div>
    </div>
  )
}
