import { useParams } from 'react-router-dom'
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
}

export default function TickerDetail() {
  const { symbol } = useParams()
  const { data: result, loading, error } = useApi(() => api.getEngineOutput(symbol), [symbol])
  const { data: signals } = useApi(() => api.getSignals({ symbol }), [symbol])

  if (loading) return <div className="text-gray-400 text-sm">Running engines for {symbol}...</div>
  if (error) return <div className="text-red-400 text-sm">Error: {error.message}</div>

  const engines = result?.engines || result || {}

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <span className="text-lg font-bold text-emerald-400 font-mono">{symbol}</span>
        <span className="text-xs text-gray-400">{(signals || []).length} signals</span>
      </div>

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
