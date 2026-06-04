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
  Legend,
  CartesianGrid,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  BarChart,
  Bar,
} from 'recharts'

const SOURCE_COLORS = {
  reddit: '#ff6b35',
  news: '#4da6ff',
  sec_edgar: '#ffd700',
  google_trends: '#34d399',
  yfinance: '#a78bfa',
}
const STEPPS_COLOR = '#34d399'
const BULLISH_COLOR = '#34d399'
const BEARISH_COLOR = '#f87171'
const NEUTRAL_COLOR = '#9ca3af'

/* Signal Timeline — Organized chronologically */
function SignalTimeline({ signals }) {
  const sorted = useMemo(() => {
    return (signals || []).sort((a, b) =>
      new Date(b.created_at || b.timestamp) - new Date(a.created_at || a.timestamp)
    )
  }, [signals])

  if (!sorted.length) return <EmptyPanel label="No signal data yet" />

  return (
    <div className="bg-gray-800 border border-gray-700 rounded p-4">
      <h3 className="text-sm font-bold text-gray-200 mb-3">Signal Timeline</h3>
      <div className="space-y-2 max-h-96 overflow-y-auto">
        {sorted.slice(0, 20).map((sig, idx) => (
          <div key={idx} className="flex gap-3 pb-2 border-b border-gray-700 last:border-0">
            <div className={`w-1 rounded-full flex-shrink-0 ${
              sig.direction === 'bullish' ? 'bg-emerald-400' :
              sig.direction === 'bearish' ? 'bg-red-400' :
              'bg-gray-500'
            }`} />
            <div className="flex-1 min-w-0">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <div className="text-xs font-semibold text-gray-200">{sig.source}</div>
                  <div className="text-xs text-gray-500">{new Date(sig.created_at || sig.timestamp).toLocaleDateString()}</div>
                </div>
                <div className={`px-2 py-0.5 rounded text-xs font-mono flex-shrink-0 ${
                  sig.direction === 'bullish' ? 'bg-emerald-900/40 text-emerald-400' :
                  sig.direction === 'bearish' ? 'bg-red-900/40 text-red-400' :
                  'bg-gray-700 text-gray-300'
                }`}>
                  {sig.direction}
                </div>
              </div>
              {sig.summary && <p className="text-xs text-gray-400 mt-1 line-clamp-2">{sig.summary}</p>}
            </div>
          </div>
        ))}
        {sorted.length > 20 && (
          <div className="text-xs text-gray-500 text-center py-2">+{sorted.length - 20} more signals</div>
        )}
      </div>
    </div>
  )
}

/* Source Breakdown — Horizontal bars */
function SourceBreakdown({ signals }) {
  const breakdown = useMemo(() => {
    const map = {}
    for (const sig of signals || []) {
      const src = sig.source || 'unknown'
      map[src] = (map[src] || 0) + 1
    }
    return Object.entries(map)
      .sort((a, b) => b[1] - a[1])
      .map(([source, count]) => ({ source, count }))
  }, [signals])

  const total = breakdown.reduce((s, x) => s + x.count, 0)

  if (!breakdown.length) return <EmptyPanel label="No source data" />

  return (
    <div className="bg-gray-800 border border-gray-700 rounded p-4">
      <h3 className="text-sm font-bold text-gray-200 mb-3">Source Distribution</h3>
      <div className="space-y-2">
        {breakdown.map(({ source, count }) => {
          const pct = total > 0 ? (count / total) * 100 : 0
          return (
            <div key={source}>
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs text-gray-400">{source}</span>
                <span className="text-xs font-mono text-gray-300">{count}</span>
              </div>
              <div className="w-full bg-gray-900 rounded h-2">
                <div
                  className="h-2 rounded bg-emerald-500/60"
                  style={{ width: `${pct}%` }}
                />
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

/* Sentiment Summary — Bullish/bearish/neutral counts */
function SentimentSummary({ signals, engineData }) {
  const sentDiv = engineData?.sentiment_divergence || {}

  const stats = useMemo(() => {
    if (!signals || !signals.length) return null
    let bullish = 0, bearish = 0, neutral = 0, total = 0
    for (const s of signals) {
      const sent = s.nlp_sentiment || s.sentiment
      if (!sent) continue
      total++
      const dir = sent.direction || sent.sentiment_direction
      if (dir === 'bullish') bullish++
      else if (dir === 'bearish') bearish++
      else neutral++
    }
    return total > 0 ? { bullish, bearish, neutral, total } : null
  }, [signals])

  if (!stats) return <EmptyPanel label="No sentiment data" />

  return (
    <div className="bg-gray-800 border border-gray-700 rounded p-4">
      <h3 className="text-sm font-bold text-gray-200 mb-3">Sentiment Summary</h3>

      {sentDiv.divergence_score != null && (
        <div className="mb-3 pb-3 border-b border-gray-700">
          <div className="flex items-center justify-between">
            <span className="text-xs text-gray-400">Divergence Score</span>
            <span className={`font-mono text-sm ${sentDiv.divergence_score > 0 ? 'text-emerald-400' : 'text-red-400'}`}>
              {sentDiv.divergence_score.toFixed(2)}
            </span>
          </div>
        </div>
      )}

      <div className="space-y-2">
        {['bullish', 'neutral', 'bearish'].map(sentiment => {
          const count = stats[sentiment]
          const pct = (count / stats.total) * 100
          const color = sentiment === 'bullish' ? BULLISH_COLOR : sentiment === 'bearish' ? BEARISH_COLOR : NEUTRAL_COLOR
          return (
            <div key={sentiment}>
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs text-gray-400 capitalize">{sentiment}</span>
                <span className="text-xs font-mono" style={{ color }}>{count}</span>
              </div>
              <div className="w-full bg-gray-900 rounded h-2">
                <div
                  className="h-2 rounded"
                  style={{ width: `${pct}%`, backgroundColor: color }}
                />
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

/* STEPPS Dimensions — 6-factor breakdown */
const STEPPS_DIMS = ['social_currency', 'triggers', 'emotion', 'public_visibility', 'practical_value', 'stories']
const STEPPS_LABELS = {
  social_currency: 'Social Currency',
  triggers: 'Triggers',
  emotion: 'Emotion',
  public_visibility: 'Public',
  practical_value: 'Practical Value',
  stories: 'Stories',
}

function SteppsDimensions({ steppsData, engineData }) {
  const steppsEngine = engineData?.stepps_classifier || {}

  const scores = useMemo(() => {
    if (steppsData && steppsData.length) {
      const latest = steppsData[0]
      const dims = latest.dimension_scores || latest.scores || latest
      return STEPPS_DIMS.map((d) => ({
        key: d,
        label: STEPPS_LABELS[d],
        score: dims[d] ?? 0,
      }))
    }
    const dims = steppsEngine.dimension_scores || steppsEngine.scores || steppsEngine
    if (dims && typeof dims === 'object') {
      const mapped = STEPPS_DIMS.map((d) => ({
        key: d,
        label: STEPPS_LABELS[d],
        score: dims[d] ?? 0,
      }))
      if (mapped.some((m) => m.score > 0)) return mapped
    }
    return null
  }, [steppsData, steppsEngine])

  const virality = steppsEngine.virality_score ?? steppsData?.[0]?.virality_score ?? null

  if (!scores) return <EmptyPanel label="No STEPPS data" />

  return (
    <div className="bg-gray-800 border border-gray-700 rounded p-4">
      <h3 className="text-sm font-bold text-gray-200 mb-3">STEPPS Dimensions</h3>
      {virality != null && (
        <div className="mb-3 pb-3 border-b border-gray-700">
          <div className="flex items-center justify-between">
            <span className="text-xs text-gray-400">Virality Score</span>
            <span className="text-xs font-mono text-emerald-400">{Number(virality).toFixed(2)}</span>
          </div>
        </div>
      )}
      <div className="space-y-2">
        {scores.map(({ key, label, score }) => (
          <div key={key}>
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs text-gray-400">{label}</span>
              <span className="text-xs font-mono text-gray-300">{score.toFixed(2)}</span>
            </div>
            <div className="w-full bg-gray-900 rounded h-2">
              <div
                className="h-2 rounded bg-emerald-500/60"
                style={{ width: `${Math.min(score * 100, 100)}%` }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

/* OLD Radar kept for reference but not used
function SteppsRadar({ steppsData, engineData }) {
  const steppsEngine = engineData?.stepps_classifier || {}
  const scores = useMemo(() => {
    if (steppsData && steppsData.length) {
      const latest = steppsData[0]
      const dims = latest.dimension_scores || latest.scores || latest
      return STEPPS_DIMS.map((d) => ({
        dimension: STEPPS_LABELS[d],
        score: dims[d] ?? 0,
        fullMark: 1,
      }))
    }
    const dims = steppsEngine.dimension_scores || steppsEngine.scores || steppsEngine
    if (dims && typeof dims === 'object') {
      const mapped = STEPPS_DIMS.map((d) => ({
        dimension: STEPPS_LABELS[d],
        score: dims[d] ?? 0,
        fullMark: 1,
      }))
      if (mapped.some((m) => m.score > 0)) return mapped
    }
    return null
  }, [steppsData, steppsEngine])

  const virality = steppsEngine.virality_score ?? steppsData?.[0]?.virality_score ?? null
  if (!scores) return <EmptyPanel label="No STEPPS data yet" />

  return (
    <div className="bg-gray-800 border border-gray-700 rounded p-4">
      <h3 className="text-sm font-bold text-gray-200 mb-1">STEPPS Virality Radar</h3>
      {virality != null && (
        <div className="text-xs text-gray-400 mb-2">
          Virality score: <span className="text-emerald-400 font-mono">{Number(virality).toFixed(2)}</span>
        </div>
      )}
      <ResponsiveContainer width="100%" height={280}>
        <RadarChart data={scores} cx="50%" cy="50%" outerRadius="70%">
          <PolarGrid stroke="#374151" />
          <PolarAngleAxis dataKey="dimension" tick={{ fill: '#d1d5db', fontSize: 10 }} />
          <PolarRadiusAxis angle={30} domain={[0, 1]} tick={{ fill: '#6b7280', fontSize: 9 }} />
          <Radar
            name="STEPPS"
            dataKey="score"
            stroke={STEPPS_COLOR}
            fill={STEPPS_COLOR}
            fillOpacity={0.25}
            strokeWidth={2}
          />
          <Tooltip
            contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: 4 }}
            itemStyle={{ fontSize: 11 }}
          />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  )
}

/* ──────────────────────────────────────────────
   Panel 4 — Mosaic & Thesis Summary
   ────────────────────────────────────────────── */
function MosaicThesisSummary({ mosaics, theses, engineData }) {
  const kelly = engineData?.kelly_sizer || {}
  const irr = engineData?.irr_simulator || {}
  const crossDomain = engineData?.cross_domain_amplifier || {}
  const regMoat = engineData?.regulatory_moat || {}

  const latestMosaic = mosaics && mosaics.length ? mosaics[0] : null
  const latestThesis = theses && theses.length ? theses[0] : null

  return (
    <div className="bg-gray-800 border border-gray-700 rounded p-4">
      <h3 className="text-sm font-bold text-gray-200 mb-3">Mosaic & Thesis Summary</h3>

      {/* Mosaic */}
      {latestMosaic ? (
        <div className="mb-3 border-b border-gray-700 pb-3">
          <div className="text-xs font-semibold text-emerald-400 mb-1">Mosaic Card</div>
          <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
            <KV label="Coherence" value={latestMosaic.coherence_score?.toFixed(2)} />
            <KV label="Signal Count" value={latestMosaic.signal_count} />
            <KV label="Sources" value={latestMosaic.source_count || latestMosaic.sources?.length} />
            <KV label="Lifecycle" value={latestMosaic.lifecycle_stage || latestMosaic.gold_rush_stage} />
          </div>
          {latestMosaic.summary && (
            <p className="text-xs text-gray-400 mt-2 leading-relaxed">{latestMosaic.summary}</p>
          )}
        </div>
      ) : (
        <p className="text-xs text-gray-500 mb-3">No mosaic assembled yet.</p>
      )}

      {/* Thesis */}
      {latestThesis ? (
        <div className="mb-3 border-b border-gray-700 pb-3">
          <div className="text-xs font-semibold text-emerald-400 mb-1">Investment Thesis</div>
          <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
            <KV label="Direction" value={latestThesis.direction} />
            <KV label="Conviction" value={latestThesis.conviction?.toFixed ? latestThesis.conviction.toFixed(2) : latestThesis.conviction} />
            <KV label="Timeframe" value={latestThesis.timeframe} />
            <KV label="ROI Target" value={latestThesis.expected_roi != null ? `${(latestThesis.expected_roi * 100).toFixed(1)}%` : '—'} />
          </div>
          {latestThesis.rationale && (
            <p className="text-xs text-gray-400 mt-2 leading-relaxed">{latestThesis.rationale}</p>
          )}
        </div>
      ) : (
        <p className="text-xs text-gray-500 mb-3">No thesis forged yet.</p>
      )}

      {/* Engine metrics */}
      <div className="space-y-2">
        {kelly.fraction != null && (
          <div className="flex gap-3">
            <MetricBadge label="Kelly f*" value={kelly.fraction?.toFixed(3)} color="#a78bfa" />
            <MetricBadge label="Suggested Size" value={kelly.suggested_size || '—'} />
          </div>
        )}
        {irr.expected_irr != null && (
          <div className="flex gap-3">
            <MetricBadge label="Expected IRR" value={`${(irr.expected_irr * 100).toFixed(1)}%`} />
            <MetricBadge label="MOIC" value={irr.expected_moic?.toFixed(2)} />
          </div>
        )}
        {crossDomain.amplification_score != null && (
          <MetricBadge label="Cross-Domain Amp" value={crossDomain.amplification_score?.toFixed(2)} color="#fbbf24" />
        )}
        {regMoat.moat_score != null && (
          <MetricBadge label="Regulatory Moat" value={regMoat.moat_score?.toFixed(2)} color="#60a5fa" />
        )}
      </div>
    </div>
  )
}

/* ──────────────────────────────────────────────
   Shared small components
   ────────────────────────────────────────────── */
function EmptyPanel({ label }) {
  return (
    <div className="bg-gray-800 border border-gray-700 rounded p-4 flex items-center justify-center min-h-[200px]">
      <p className="text-xs text-gray-500">{label}</p>
    </div>
  )
}

function MetricBadge({ label, value, color = '#9ca3af' }) {
  return (
    <div className="text-xs">
      <span className="text-gray-500">{label}: </span>
      <span className="font-mono" style={{ color }}>{value ?? '—'}</span>
    </div>
  )
}

function StatPill({ label, count, color, total }) {
  const pct = total > 0 ? ((count / total) * 100).toFixed(0) : 0
  return (
    <div className="flex-1 rounded bg-gray-900 border border-gray-700 p-2 text-center">
      <div className="text-lg font-bold font-mono" style={{ color }}>{count}</div>
      <div className="text-xs text-gray-500">{label} ({pct}%)</div>
    </div>
  )
}

function KV({ label, value }) {
  return (
    <>
      <span className="text-gray-500">{label}</span>
      <span className="text-gray-300 font-mono">{value ?? '—'}</span>
    </>
  )
}

/* ──────────────────────────────────────────────
   Main Deep Dive Page
   ────────────────────────────────────────────── */
export default function DeepDive() {
  const { symbol } = useParams()
  const [activeTab, setActiveTab] = useState('all')
  const [actionMsg, setActionMsg] = useState(null)
  const [showThesisForm, setShowThesisForm] = useState(false)
  const [thesisForm, setThesisForm] = useState({ direction: 'bullish', timeframe: 'medium', expected_roi: '', rationale: '' })
  const [thesisSubmitting, setThesisSubmitting] = useState(false)

  const handleCreateThesis = async (e) => {
    e.preventDefault()
    setThesisSubmitting(true)
    try {
      await api.createThesis({
        symbol,
        domain: 'public',
        thesis_type: 'directional',
        direction: thesisForm.direction,
        timeframe: thesisForm.timeframe,
        expected_roi: parseFloat(thesisForm.expected_roi) / 100,
        rationale: thesisForm.rationale,
        lifecycle_stage: engines?.gold_rush_scorer?.stage || 'emerging',
      })
      setActionMsg({ type: 'success', text: 'Thesis created from deep dive insights' })
      setShowThesisForm(false)
      setThesisForm({ direction: 'bullish', timeframe: 'medium', expected_roi: '', rationale: '' })
    } catch (err) {
      setActionMsg({ type: 'error', text: `Failed: ${err.message}` })
    }
    setThesisSubmitting(false)
    setTimeout(() => setActionMsg(null), 5000)
  }

  const handleRunAnalysis = async () => {
    setActionMsg(null)
    try {
      await api.runAnalysis({ symbol })
      setActionMsg({ type: 'success', text: 'Analysis triggered — refresh to see updated results' })
    } catch (err) {
      setActionMsg({ type: 'error', text: `Failed: ${err.message}` })
    }
    setTimeout(() => setActionMsg(null), 5000)
  }

  // Fetch all data in parallel
  const { data: signals, loading: sigLoad } = useApi(() => api.getSignals({ symbol, limit: 500 }), [symbol])
  const { data: engineData, loading: engLoad } = useApi(() => api.getEngineOutput(symbol), [symbol])
  const { data: mosaics } = useApi(() => api.getMosaics({ symbol }), [symbol])
  const { data: theses } = useApi(() => api.getTheses({ symbol }), [symbol])
  const { data: steppsData } = useApi(() => api.getSteppsScores({ symbol }), [symbol])

  const loading = sigLoad || engLoad
  const engines = engineData?.engines || engineData || {}

  const tabs = [
    { id: 'all', label: 'All Panels' },
    { id: 'signals', label: 'Signals' },
    { id: 'sentiment', label: 'Sentiment' },
    { id: 'stepps', label: 'STEPPS' },
    { id: 'thesis', label: 'Mosaic / Thesis' },
  ]

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-3">
          <Link to={`/tickers/${symbol}`} className="text-xs text-gray-500 hover:text-gray-300 no-underline">
            &larr; Engine View
          </Link>
          <span className="text-lg font-bold text-emerald-400 font-mono">{symbol}</span>
          <span className="text-xs px-2 py-0.5 rounded bg-gray-700 text-gray-300">Deep Dive</span>
        </div>
        <div className="flex gap-2 flex-wrap">
          <button
            onClick={() => setShowThesisForm(!showThesisForm)}
            className={`text-xs px-3 py-1 rounded transition-colors ${showThesisForm ? 'bg-yellow-800 text-yellow-300' : 'bg-yellow-600 hover:bg-yellow-500 text-white'}`}
          >
            {showThesisForm ? 'Cancel' : '+ Create Thesis'}
          </button>
          <button
            onClick={handleRunAnalysis}
            className="text-xs px-3 py-1 rounded bg-orange-600 hover:bg-orange-500 text-white transition-colors"
          >
            Re-run Engines
          </button>
          <Link
            to={`/mosaic/${symbol}`}
            className="text-xs px-3 py-1 rounded bg-emerald-600 hover:bg-emerald-500 text-white no-underline transition-colors"
          >
            Mosaic Workbench &rarr;
          </Link>
          <Link
            to={`/lattice/${symbol}`}
            className="text-xs px-3 py-1 rounded bg-purple-600 hover:bg-purple-500 text-white no-underline transition-colors"
          >
            Build Lattice &rarr;
          </Link>
        </div>
      </div>

      {/* Action Feedback */}
      {actionMsg && (
        <div className={`text-xs px-3 py-2 rounded ${actionMsg.type === 'success' ? 'bg-emerald-900 text-emerald-400' : 'bg-red-900 text-red-400'}`}>
          {actionMsg.text}
        </div>
      )}

      {/* Inline Thesis Form */}
      {showThesisForm && (
        <div className="bg-gray-800 border border-gray-700 rounded p-4">
          <h3 className="text-sm font-bold text-gray-200 mb-3">Create Thesis from Deep Dive</h3>
          <form onSubmit={handleCreateThesis} className="flex gap-3 items-end flex-wrap">
            <div>
              <label className="text-xs text-gray-400 block mb-1">Direction</label>
              <select value={thesisForm.direction} onChange={e => setThesisForm({...thesisForm, direction: e.target.value})} className="bg-gray-900 border border-gray-600 rounded px-2 py-1 text-sm text-gray-200">
                <option value="bullish">Bullish</option>
                <option value="bearish">Bearish</option>
                <option value="neutral">Neutral</option>
              </select>
            </div>
            <div>
              <label className="text-xs text-gray-400 block mb-1">Timeframe</label>
              <select value={thesisForm.timeframe} onChange={e => setThesisForm({...thesisForm, timeframe: e.target.value})} className="bg-gray-900 border border-gray-600 rounded px-2 py-1 text-sm text-gray-200">
                <option value="short">Short (days)</option>
                <option value="medium">Medium (weeks)</option>
                <option value="long">Long (months)</option>
              </select>
            </div>
            <div>
              <label className="text-xs text-gray-400 block mb-1">Expected ROI %</label>
              <input type="number" step="0.1" required value={thesisForm.expected_roi} onChange={e => setThesisForm({...thesisForm, expected_roi: e.target.value})} className="bg-gray-900 border border-gray-600 rounded px-2 py-1 text-sm text-gray-200 w-24" placeholder="15" />
            </div>
            <div className="flex-1 min-w-[200px]">
              <label className="text-xs text-gray-400 block mb-1">Rationale</label>
              <input type="text" required value={thesisForm.rationale} onChange={e => setThesisForm({...thesisForm, rationale: e.target.value})} className="bg-gray-900 border border-gray-600 rounded px-2 py-1 text-sm text-gray-200 w-full" placeholder="Based on asymmetry in social signals..." />
            </div>
            <button type="submit" disabled={thesisSubmitting} className="bg-emerald-700 hover:bg-emerald-600 disabled:bg-gray-700 text-white text-xs px-4 py-1.5 rounded">
              {thesisSubmitting ? 'Creating…' : 'Create Thesis'}
            </button>
          </form>
        </div>
      )}

      {/* Tab bar */}
      <div className="flex gap-1 border-b border-gray-700 pb-0.5">
        {tabs.map((t) => (
          <button
            key={t.id}
            onClick={() => setActiveTab(t.id)}
            className={`px-3 py-1.5 text-xs rounded-t transition-colors ${
              activeTab === t.id
                ? 'bg-gray-700 text-white'
                : 'text-gray-500 hover:text-gray-300 hover:bg-gray-800'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="text-gray-400 text-sm py-8 text-center">Loading deep dive for {symbol}...</div>
      ) : (
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
          {(activeTab === 'all' || activeTab === 'signals') && (
            <>
              <SignalTimeline signals={signals} />
              <SourceBreakdown signals={signals} />
            </>
          )}
          {(activeTab === 'all' || activeTab === 'sentiment') && (
            <SentimentSummary signals={signals} engineData={engines} />
          )}
          {(activeTab === 'all' || activeTab === 'stepps') && (
            <SteppsDimensions steppsData={steppsData} engineData={engines} />
          )}
          {(activeTab === 'all' || activeTab === 'thesis') && (
            <MosaicThesisSummary mosaics={mosaics} theses={theses} engineData={engines} />
          )}
        </div>
      )}
    </div>
  )
}
