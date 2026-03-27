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

/* ──────────────────────────────────────────────
   Colour palette (dark-theme friendly)
   ────────────────────────────────────────────── */
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

/* ──────────────────────────────────────────────
   Panel 1 — Signal Trends Chart
   ────────────────────────────────────────────── */
function SignalTrendsChart({ signals }) {
  const chartData = useMemo(() => {
    if (!signals || !signals.length) return []
    // Group signals by day + source
    const byDay = {}
    for (const s of signals) {
      const day = (s.collected_at || s.created_at || '').slice(0, 10)
      if (!day) continue
      if (!byDay[day]) byDay[day] = {}
      const src = s.source || 'unknown'
      byDay[day][src] = (byDay[day][src] || 0) + 1
    }
    return Object.entries(byDay)
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([date, sources]) => ({ date, ...sources }))
  }, [signals])

  const sources = useMemo(() => {
    const s = new Set()
    for (const row of chartData) {
      Object.keys(row).forEach((k) => k !== 'date' && s.add(k))
    }
    return [...s]
  }, [chartData])

  if (!chartData.length) {
    return <EmptyPanel label="No signal data yet" />
  }

  return (
    <div className="bg-gray-800 border border-gray-700 rounded p-4">
      <h3 className="text-sm font-bold text-gray-200 mb-3">Signal Trends by Source</h3>
      <ResponsiveContainer width="100%" height={260}>
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
          <XAxis dataKey="date" tick={{ fill: '#9ca3af', fontSize: 10 }} />
          <YAxis tick={{ fill: '#9ca3af', fontSize: 10 }} allowDecimals={false} />
          <Tooltip
            contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: 4 }}
            labelStyle={{ color: '#d1d5db', fontSize: 11 }}
            itemStyle={{ fontSize: 11 }}
          />
          <Legend wrapperStyle={{ fontSize: 11 }} />
          {sources.map((src) => (
            <Line
              key={src}
              type="monotone"
              dataKey={src}
              stroke={SOURCE_COLORS[src] || '#8884d8'}
              strokeWidth={2}
              dot={{ r: 3 }}
              connectNulls
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

/* ──────────────────────────────────────────────
   Panel 2 — Sentiment Analysis
   ────────────────────────────────────────────── */
function SentimentPanel({ signals, engineData }) {
  // Extract sentiment from engine output
  const sentDiv = engineData?.sentiment_divergence || {}

  // Aggregate sentiment from signals that have nlp_sentiment
  const sentimentStats = useMemo(() => {
    if (!signals || !signals.length) return null
    let bullish = 0, bearish = 0, neutral = 0, total = 0
    const scores = []
    for (const s of signals) {
      const sent = s.nlp_sentiment || s.sentiment
      if (!sent) continue
      total++
      const dir = sent.direction || sent.sentiment_direction
      if (dir === 'bullish') bullish++
      else if (dir === 'bearish') bearish++
      else neutral++
      const compound = sent.compound ?? sent.score ?? null
      if (compound !== null) scores.push(compound)
    }
    if (!total) return null
    const avg = scores.length ? scores.reduce((a, b) => a + b, 0) / scores.length : 0
    return { bullish, bearish, neutral, total, avgCompound: avg }
  }, [signals])

  // Build bar chart data for sentiment by source
  const sentBySource = useMemo(() => {
    if (!signals || !signals.length) return []
    const map = {}
    for (const s of signals) {
      const sent = s.nlp_sentiment || s.sentiment
      if (!sent) continue
      const src = s.source || 'unknown'
      if (!map[src]) map[src] = { source: src, bullish: 0, bearish: 0, neutral: 0 }
      const dir = sent.direction || sent.sentiment_direction
      if (dir === 'bullish') map[src].bullish++
      else if (dir === 'bearish') map[src].bearish++
      else map[src].neutral++
    }
    return Object.values(map)
  }, [signals])

  return (
    <div className="bg-gray-800 border border-gray-700 rounded p-4">
      <h3 className="text-sm font-bold text-gray-200 mb-3">Sentiment Analysis</h3>

      {/* Engine divergence score */}
      {sentDiv.divergence_score != null && (
        <div className="flex items-center gap-4 mb-3">
          <MetricBadge
            label="Divergence"
            value={sentDiv.divergence_score?.toFixed(2)}
            color={sentDiv.divergence_score > 0 ? BULLISH_COLOR : BEARISH_COLOR}
          />
          {sentDiv.social_sentiment != null && (
            <MetricBadge label="Social Sentiment" value={sentDiv.social_sentiment?.toFixed(2)} />
          )}
          {sentDiv.market_direction != null && (
            <MetricBadge label="Market Direction" value={sentDiv.market_direction} />
          )}
        </div>
      )}

      {/* Aggregated NLP stats */}
      {sentimentStats ? (
        <div className="space-y-3">
          <div className="flex gap-3">
            <StatPill label="Bullish" count={sentimentStats.bullish} color={BULLISH_COLOR} total={sentimentStats.total} />
            <StatPill label="Bearish" count={sentimentStats.bearish} color={BEARISH_COLOR} total={sentimentStats.total} />
            <StatPill label="Neutral" count={sentimentStats.neutral} color={NEUTRAL_COLOR} total={sentimentStats.total} />
          </div>
          <div className="text-xs text-gray-400">
            Avg compound: <span className={sentimentStats.avgCompound >= 0 ? 'text-emerald-400' : 'text-red-400'}>
              {sentimentStats.avgCompound.toFixed(3)}
            </span>
            {' '}across {sentimentStats.total} scored signals
          </div>

          {sentBySource.length > 0 && (
            <ResponsiveContainer width="100%" height={180}>
              <BarChart data={sentBySource} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis type="number" tick={{ fill: '#9ca3af', fontSize: 10 }} allowDecimals={false} />
                <YAxis dataKey="source" type="category" tick={{ fill: '#9ca3af', fontSize: 10 }} width={80} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: 4 }}
                  itemStyle={{ fontSize: 11 }}
                />
                <Bar dataKey="bullish" stackId="a" fill={BULLISH_COLOR} />
                <Bar dataKey="neutral" stackId="a" fill={NEUTRAL_COLOR} />
                <Bar dataKey="bearish" stackId="a" fill={BEARISH_COLOR} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>
      ) : (
        <p className="text-xs text-gray-500">No NLP sentiment data for these signals.</p>
      )}
    </div>
  )
}

/* ──────────────────────────────────────────────
   Panel 3 — STEPPS Radar
   ────────────────────────────────────────────── */
const STEPPS_DIMS = ['social_currency', 'triggers', 'emotion', 'public_visibility', 'practical_value', 'stories']
const STEPPS_LABELS = {
  social_currency: 'Social Currency',
  triggers: 'Triggers',
  emotion: 'Emotion',
  public_visibility: 'Public',
  practical_value: 'Practical Value',
  stories: 'Stories',
}

function SteppsRadar({ steppsData, engineData }) {
  const steppsEngine = engineData?.stepps_classifier || {}

  // Try stepps scores from dedicated endpoint first, then engine output
  const scores = useMemo(() => {
    // From /stepps/scores endpoint (array)
    if (steppsData && steppsData.length) {
      const latest = steppsData[0]
      const dims = latest.dimension_scores || latest.scores || latest
      return STEPPS_DIMS.map((d) => ({
        dimension: STEPPS_LABELS[d],
        score: dims[d] ?? 0,
        fullMark: 1,
      }))
    }
    // From engine output
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

  if (!scores) {
    return <EmptyPanel label="No STEPPS data yet" />
  }

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
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Link to={`/tickers/${symbol}`} className="text-xs text-gray-500 hover:text-gray-300 no-underline">
            &larr; Engine View
          </Link>
          <span className="text-lg font-bold text-emerald-400 font-mono">{symbol}</span>
          <span className="text-xs px-2 py-0.5 rounded bg-gray-700 text-gray-300">Deep Dive</span>
        </div>
        <div className="flex gap-2">
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
            <SignalTrendsChart signals={signals} />
          )}
          {(activeTab === 'all' || activeTab === 'sentiment') && (
            <SentimentPanel signals={signals} engineData={engines} />
          )}
          {(activeTab === 'all' || activeTab === 'stepps') && (
            <SteppsRadar steppsData={steppsData} engineData={engines} />
          )}
          {(activeTab === 'all' || activeTab === 'thesis') && (
            <MosaicThesisSummary mosaics={mosaics} theses={theses} engineData={engines} />
          )}
        </div>
      )}
    </div>
  )
}
