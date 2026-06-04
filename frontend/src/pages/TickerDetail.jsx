import { useParams, Link } from 'react-router-dom'
import { useState } from 'react'
import { useApi } from '../hooks'
import { api } from '../api'

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
      {/* Header */}
      <div className="flex items-center gap-3 flex-wrap">
        <span className="text-2xl font-bold text-emerald-400 font-mono">{symbol}</span>
        <span className="text-xs text-gray-400">{(signals || []).length} signals</span>
        <div className="ml-auto flex gap-2 flex-wrap">
          <button
            onClick={handleRerun}
            disabled={rerunning}
            className="text-xs px-3 py-1.5 rounded bg-orange-900 hover:bg-orange-800 disabled:bg-gray-700 disabled:text-gray-500 text-orange-400 transition-colors border border-orange-700"
          >
            {rerunning ? 'Running…' : 'Re-run Engines'}
          </button>
          <button
            onClick={handleAddWatchlist}
            className="text-xs px-3 py-1.5 rounded bg-yellow-900 hover:bg-yellow-800 text-yellow-400 transition-colors border border-yellow-700"
          >
            + Watchlist
          </button>
          <Link
            to={`/mosaic/${symbol}`}
            className="text-xs px-3 py-1.5 rounded bg-purple-900 hover:bg-purple-800 text-purple-400 no-underline transition-colors border border-purple-700"
          >
            Mosaic Workbench
          </Link>
          <Link
            to={`/deepdive/${symbol}`}
            className="text-xs px-3 py-1.5 rounded bg-emerald-900 hover:bg-emerald-800 text-emerald-400 no-underline transition-colors border border-emerald-700"
          >
            Deep Dive
          </Link>
          <Link
            to={`/lattice/${symbol}`}
            className="text-xs px-3 py-1.5 rounded bg-blue-900 hover:bg-blue-800 text-blue-400 no-underline transition-colors border border-blue-700"
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

      {/* Engine Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
        {engines.sentiment_divergence && (
          <EnginePanel title="Sentiment Divergence" icon="∆">
            {engines.sentiment_divergence.social_growth != null && (
              <MetricRow label="Social Growth" value={`${(engines.sentiment_divergence.social_growth * 100).toFixed(1)}%`} />
            )}
            {engines.sentiment_divergence.market_expectation != null && (
              <MetricRow label="Market Expected" value={`${(engines.sentiment_divergence.market_expectation * 100).toFixed(1)}%`} />
            )}
            {engines.sentiment_divergence.divergence_score != null && (
              <MetricRow label="Divergence" value={engines.sentiment_divergence.divergence_score.toFixed(2)} highlight={Math.abs(engines.sentiment_divergence.divergence_score) > 0.3} />
            )}
          </EnginePanel>
        )}

        {engines.technical_analyzer && (
          <EnginePanel title="Technical Analyzer" icon="📊">
            {engines.technical_analyzer.trend && (
              <MetricRow label="Trend" value={engines.technical_analyzer.trend} />
            )}
            {engines.technical_analyzer.rsi != null && (
              <MetricRow label="RSI(14)" value={engines.technical_analyzer.rsi.toFixed(1)} />
            )}
            {engines.technical_analyzer.signal_strength != null && (
              <MetricRow label="Strength" value={engines.technical_analyzer.signal_strength.toFixed(2)} />
            )}
          </EnginePanel>
        )}

        {engines.kelly_sizer && (
          <EnginePanel title="Kelly Criterion" icon="📐">
            {engines.kelly_sizer.kelly_fraction != null && (
              <MetricRow label="Fraction" value={`${(engines.kelly_sizer.kelly_fraction * 100).toFixed(1)}%`} highlight={true} />
            )}
            {engines.kelly_sizer.recommended_size != null && (
              <MetricRow label="Size" value={`${(engines.kelly_sizer.recommended_size * 100).toFixed(1)}%`} />
            )}
            {engines.kelly_sizer.confidence != null && (
              <MetricRow label="Confidence" value={engines.kelly_sizer.confidence.toFixed(2)} />
            )}
          </EnginePanel>
        )}

        {engines.irr_simulator && (
          <EnginePanel title="IRR/MOIC Simulator" icon="📈">
            {engines.irr_simulator.base_case_irr != null && (
              <MetricRow label="Base IRR" value={`${(engines.irr_simulator.base_case_irr * 100).toFixed(1)}%`} />
            )}
            {engines.irr_simulator.bull_case_irr != null && (
              <MetricRow label="Bull IRR" value={`${(engines.irr_simulator.bull_case_irr * 100).toFixed(1)}%`} highlight={true} />
            )}
            {engines.irr_simulator.bear_case_irr != null && (
              <MetricRow label="Bear IRR" value={`${(engines.irr_simulator.bear_case_irr * 100).toFixed(1)}%`} />
            )}
          </EnginePanel>
        )}

        {engines.regulatory_moat && (
          <EnginePanel title="Regulatory Moat" icon="🛡️">
            {engines.regulatory_moat.moat_strength != null && (
              <MetricRow label="Strength" value={engines.regulatory_moat.moat_strength.toFixed(2)} highlight={true} />
            )}
            {engines.regulatory_moat.competitive_advantage && (
              <MetricRow label="Advantage" value={engines.regulatory_moat.competitive_advantage} />
            )}
            {engines.regulatory_moat.enforcement_risk != null && (
              <MetricRow label="Enforcement Risk" value={`${(engines.regulatory_moat.enforcement_risk * 100).toFixed(1)}%`} />
            )}
          </EnginePanel>
        )}

        {engines.cross_domain_amplifier && (
          <EnginePanel title="Cross-Domain Amplifier" icon="🔗">
            {engines.cross_domain_amplifier.amplification_factor != null && (
              <MetricRow label="Amplification" value={`${engines.cross_domain_amplifier.amplification_factor.toFixed(2)}x`} highlight={true} />
            )}
            {engines.cross_domain_amplifier.domains_connected != null && (
              <MetricRow label="Domains" value={engines.cross_domain_amplifier.domains_connected} />
            )}
          </EnginePanel>
        )}

        {engines.stepps_classifier && (
          <EnginePanel title="STEPPS Classifier" icon="📡">
            {engines.stepps_classifier.primary_dimension && (
              <MetricRow label="Primary" value={engines.stepps_classifier.primary_dimension} />
            )}
            {engines.stepps_classifier.virality_score != null && (
              <MetricRow label="Virality" value={engines.stepps_classifier.virality_score.toFixed(2)} highlight={true} />
            )}
          </EnginePanel>
        )}

        {engines.gold_rush_scorer && (
          <EnginePanel title="Gold Rush Lifecycle" icon="💰">
            {engines.gold_rush_scorer.stage && (
              <MetricRow label="Stage" value={engines.gold_rush_scorer.stage} highlight={true} />
            )}
            {engines.gold_rush_scorer.confidence != null && (
              <MetricRow label="Confidence" value={`${(engines.gold_rush_scorer.confidence * 100).toFixed(1)}%`} />
            )}
          </EnginePanel>
        )}

        {engines.asymmetry_scanner && (
          <EnginePanel title="Asymmetry Scanner" icon="⚖️">
            {engines.asymmetry_scanner.asymmetry_score != null && (
              <MetricRow label="Score" value={engines.asymmetry_scanner.asymmetry_score.toFixed(2)} highlight={true} />
            )}
            {engines.asymmetry_scanner.gap_pct != null && (
              <MetricRow label="Gap" value={`${(engines.asymmetry_scanner.gap_pct * 100).toFixed(1)}%`} />
            )}
          </EnginePanel>
        )}

        {engines.catalyst_engine?.catalysts?.length > 0 && (
          <EnginePanel title="Catalyst Engine" icon="🚀">
            <div className="space-y-2">
              {engines.catalyst_engine.catalysts.slice(0, 3).map((cat, idx) => (
                <div key={idx} className="text-xs pb-1 border-b border-white/[0.06]">
                  <div className="text-emerald-400">{cat.name}</div>
                  <div className="text-gray-500 text-[10px]">{cat.date}</div>
                </div>
              ))}
              {engines.catalyst_engine.catalysts.length > 3 && (
                <div className="text-xs text-gray-600">+{engines.catalyst_engine.catalysts.length - 3} more</div>
              )}
            </div>
          </EnginePanel>
        )}

        {engines.conviction_scorer && (
          <EnginePanel title="Conviction Scorecard" icon="⭐">
            {engines.conviction_scorer.total != null && (
              <MetricRow label="Total" value={engines.conviction_scorer.total.toFixed(2)} highlight={true} />
            )}
            {engines.conviction_scorer.dimensions && (
              <div className="text-xs mt-2 pt-2 border-t border-white/[0.06] space-y-1">
                {Object.entries(engines.conviction_scorer.dimensions).slice(0, 3).map(([key, val]) => (
                  <MetricRow key={key} label={key.replace(/_/g, ' ')} value={typeof val === 'number' ? val.toFixed(2) : val} />
                ))}
              </div>
            )}
          </EnginePanel>
        )}
      </div>

      {/* Signals Summary */}
      <div className="bg-gray-800 border border-gray-700 rounded p-4">
        <h3 className="text-xs font-bold text-gray-300 mb-3 uppercase tracking-wider">Signals ({signals?.length || 0})</h3>
        {signals && signals.length > 0 ? (
          <div className="space-y-2 max-h-80 overflow-y-auto">
            {signals.slice(0, 15).map((sig, idx) => (
              <div key={idx} className="flex justify-between items-start text-xs pb-2 border-b border-gray-700">
                <div>
                  <div className="text-gray-200">{sig.source}</div>
                  <div className="text-gray-500 text-[11px]">{new Date(sig.created_at || sig.timestamp).toLocaleDateString()}</div>
                </div>
                <div className={`px-2 py-0.5 rounded text-xs font-mono ${
                  sig.direction === 'bullish' ? 'bg-emerald-900/40 text-emerald-400' :
                  sig.direction === 'bearish' ? 'bg-red-900/40 text-red-400' :
                  'bg-gray-700 text-gray-300'
                }`}>
                  {sig.direction}
                </div>
              </div>
            ))}
            {signals.length > 15 && (
              <div className="text-xs text-gray-500 pt-2">+{signals.length - 15} more signals</div>
            )}
          </div>
        ) : (
          <div className="text-xs text-gray-500">No signals yet for {symbol}</div>
        )}
      </div>
    </div>
  )
}

function EnginePanel({ title, icon, children }) {
  return (
    <div className="bg-gray-800 border border-gray-700 rounded p-3">
      <h3 className="text-xs font-bold text-gray-300 mb-2 flex items-center gap-1">
        <span>{icon}</span> {title}
      </h3>
      <div className="space-y-1.5 text-xs">
        {children}
      </div>
    </div>
  )
}

function MetricRow({ label, value, highlight = false }) {
  return (
    <div className="flex justify-between items-center">
      <span className="text-gray-500">{label}</span>
      <span className={`font-mono ${highlight ? 'text-emerald-400 font-semibold' : 'text-gray-300'}`}>{value}</span>
    </div>
  )
}
