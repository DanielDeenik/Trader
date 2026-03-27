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
  Cell,
  ComposedChart,
} from 'recharts'

const LIFECYCLE_STAGES = {
  emerging: { label: 'Emerging', color: '#10b981', bgColor: '#064e3b' },
  validating: { label: 'Validating', color: '#3b82f6', bgColor: '#1e3a8a' },
  confirmed: { label: 'Confirmed', color: '#f59e0b', bgColor: '#78350f' },
  saturated: { label: 'Saturated', color: '#ef4444', bgColor: '#7f1d1d' },
}

const CATALYST_COLORS = {
  earnings: '#3b82f6',
  product: '#10b981',
  regulatory: '#f97316',
  partnership: '#a855f7',
  social: '#ec4899',
  macro: '#6b7280',
}

const CONVICTION_COLORS = {
  positive: '#10b981',
  negative: '#ef4444',
  neutral: '#9ca3af',
}

/* ──────────────────────────────────────────────
   Section 1: Header + Quick Stats
   ────────────────────────────────────────────── */
function Header({ symbol, data }) {
  const gold_rush = data?.engines?.gold_rush_scorer || {}
  const conviction = data?.engines?.conviction_scorer || {}

  const stage = gold_rush.stage || 'unknown'
  const stageConfig = LIFECYCLE_STAGES[stage] || { label: stage, color: '#9ca3af', bgColor: '#374151' }

  const convictionScore = conviction.conviction_score || 0
  const gradeLetters = ['F', 'D', 'C', 'B', 'A']
  const gradeIndex = Math.min(Math.floor(convictionScore / 20), 4)
  const grade = gradeLetters[gradeIndex]

  const decision = conviction.decision || 'WAIT'
  const decisionColors = {
    GO: '#10b981',
    'NO-GO': '#ef4444',
    WAIT: '#f59e0b',
  }

  return (
    <div className="bg-gray-800 border border-gray-700 rounded p-6 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-emerald-400 font-mono">{symbol}</h1>
          <p className="text-xs text-gray-400 mt-1">Mosaic Workbench • Investment Decision Interface</p>
        </div>
        <div className="flex gap-3">
          <Link
            to={`/deepdive/${symbol}`}
            className="text-xs px-3 py-2 rounded bg-blue-900 hover:bg-blue-800 text-blue-400 no-underline transition-colors border border-blue-700"
          >
            Deep Dive
          </Link>
          <Link
            to={`/lattice/${symbol}`}
            className="text-xs px-3 py-2 rounded bg-purple-900 hover:bg-purple-800 text-purple-400 no-underline transition-colors border border-purple-700"
          >
            Lattice
          </Link>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-4">
        {/* Stage Badge */}
        <div className="bg-gray-900 rounded p-3 border border-gray-700">
          <div className="text-xs text-gray-400 uppercase tracking-wider mb-1">Lifecycle Stage</div>
          <div
            className="text-lg font-bold rounded px-2 py-1 inline-block"
            style={{ color: stageConfig.color, backgroundColor: stageConfig.bgColor }}
          >
            {stageConfig.label}
          </div>
        </div>

        {/* Conviction Grade */}
        <div className="bg-gray-900 rounded p-3 border border-gray-700">
          <div className="text-xs text-gray-400 uppercase tracking-wider mb-1">Conviction Grade</div>
          <div className="text-3xl font-bold" style={{ color: stageConfig.color }}>
            {grade}
          </div>
          <div className="text-xs text-gray-500 mt-1">{convictionScore.toFixed(0)} / 100</div>
        </div>

        {/* Decision */}
        <div className="bg-gray-900 rounded p-3 border border-gray-700">
          <div className="text-xs text-gray-400 uppercase tracking-wider mb-1">Decision</div>
          <div
            className="text-lg font-bold rounded px-2 py-1 inline-block"
            style={{ color: decisionColors[decision] || '#9ca3af' }}
          >
            {decision}
          </div>
        </div>
      </div>
    </div>
  )
}

/* ──────────────────────────────────────────────
   Section 2: Information Asymmetry Panel
   ────────────────────────────────────────────── */
function AsymmetryPanel({ data }) {
  const asymmetry = data?.engines?.asymmetry_scanner || {}
  const signals = data?.signals || []

  const asymScore = asymmetry.asymmetry_score || 0
  const socialSignals = signals.filter((s) => s.source === 'reddit').length
  const institutionalSignals = signals.filter((s) => s.source === 'sec_edgar').length

  // Velocity comparison
  const velocityData = useMemo(() => {
    if (!signals.length) return []
    const byDay = {}
    for (const s of signals) {
      const day = (s.collected_at || s.created_at || '').slice(0, 10)
      if (!day) continue
      if (!byDay[day]) byDay[day] = { date: day, social: 0, institutional: 0 }
      if (s.source === 'reddit') byDay[day].social++
      if (s.source === 'sec_edgar') byDay[day].institutional++
    }
    return Object.values(byDay).sort((a, b) => a.date.localeCompare(b.date)).slice(-14)
  }, [signals])

  const percentAhead = ((socialSignals / (socialSignals + institutionalSignals)) * 100).toFixed(0)

  return (
    <div className="bg-gray-800 border border-gray-700 rounded p-6 space-y-4">
      <h2 className="text-lg font-bold text-gray-200">Information Asymmetry</h2>

      <div className="grid grid-cols-2 gap-4">
        {/* Asymmetry Score Gauge */}
        <div className="bg-gray-900 rounded p-4 border border-gray-700">
          <div className="text-sm text-gray-400 mb-3">Asymmetry Score</div>
          <div className="relative">
            <div className="text-4xl font-bold text-emerald-400">{asymScore.toFixed(0)}</div>
            <div className="w-full bg-gray-700 rounded-full h-2 mt-3 overflow-hidden">
              <div
                className="bg-emerald-500 h-full transition-all"
                style={{ width: `${Math.min(asymScore, 100)}%` }}
              ></div>
            </div>
            <div className="flex justify-between text-xs text-gray-500 mt-1">
              <span>Low</span>
              <span>High</span>
            </div>
          </div>
        </div>

        {/* Gap Indicator */}
        <div className="bg-gray-900 rounded p-4 border border-gray-700">
          <div className="text-sm text-gray-400 mb-3">Signal Gap</div>
          <div className="text-2xl font-bold text-emerald-400 mb-2">{percentAhead}%</div>
          <p className="text-xs text-gray-400">
            Retail knows <span className="text-emerald-400 font-bold">{percentAhead}%</span> more than market priced
          </p>
        </div>
      </div>

      {/* Signal Comparison */}
      <div className="grid grid-cols-2 gap-4">
        <div className="bg-gray-900 rounded p-4 border border-gray-700">
          <div className="text-sm text-gray-400 mb-2">Social Signals</div>
          <div className="text-3xl font-bold text-orange-400">{socialSignals}</div>
          <p className="text-xs text-gray-500 mt-1">Reddit, Twitter, etc.</p>
        </div>

        <div className="bg-gray-900 rounded p-4 border border-gray-700">
          <div className="text-sm text-gray-400 mb-2">Institutional Signals</div>
          <div className="text-3xl font-bold text-blue-400">{institutionalSignals}</div>
          <p className="text-xs text-gray-500 mt-1">SEC EDGAR, regulatory</p>
        </div>
      </div>

      {/* Velocity Comparison Chart */}
      {velocityData.length > 0 && (
        <div className="bg-gray-900 rounded p-4 border border-gray-700">
          <div className="text-sm text-gray-400 mb-3">Velocity Comparison (14d)</div>
          <ResponsiveContainer width="100%" height={200}>
            <ComposedChart data={velocityData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis dataKey="date" tick={{ fill: '#9ca3af', fontSize: 10 }} />
              <YAxis tick={{ fill: '#9ca3af', fontSize: 10 }} allowDecimals={false} />
              <Tooltip
                contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: 4 }}
                labelStyle={{ color: '#d1d5db', fontSize: 11 }}
                itemStyle={{ fontSize: 11 }}
              />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <Line
                type="monotone"
                dataKey="social"
                stroke="#ff6b35"
                strokeWidth={2}
                dot={{ r: 3 }}
                connectNulls
                name="Social Velocity"
              />
              <Line
                type="monotone"
                dataKey="institutional"
                stroke="#4da6ff"
                strokeWidth={2}
                dot={{ r: 3 }}
                connectNulls
                name="Institutional Velocity"
              />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  )
}

/* ──────────────────────────────────────────────
   Section 3: Gold Rush Lifecycle
   ────────────────────────────────────────────── */
function LifecyclePanel({ data }) {
  const gold_rush = data?.engines?.gold_rush_scorer || {}

  const stage = gold_rush.stage || 'emerging'
  const stageConfig = LIFECYCLE_STAGES[stage] || { label: stage, color: '#9ca3af', bgColor: '#374151' }

  const stages = ['emerging', 'validating', 'confirmed', 'saturated']
  const currentStageIndex = stages.indexOf(stage)

  return (
    <div className="bg-gray-800 border border-gray-700 rounded p-6 space-y-4">
      <h2 className="text-lg font-bold text-gray-200">Gold Rush Lifecycle</h2>

      {/* Stage Progression */}
      <div className="flex items-center gap-2 justify-between">
        {stages.map((s, idx) => {
          const config = LIFECYCLE_STAGES[s]
          const isActive = idx === currentStageIndex
          const isPast = idx < currentStageIndex

          return (
            <div key={s} className="flex-1">
              <div
                className={`rounded-full w-full py-2 text-center text-xs font-bold transition-all ${
                  isActive ? 'ring-2 ring-offset-2 ring-offset-gray-800' : ''
                }`}
                style={{
                  backgroundColor: isActive ? config.bgColor : isPast ? '#1f2937' : '#111827',
                  color: isActive ? config.color : '#6b7280',
                  borderColor: isActive ? config.color : '#374151',
                  border: '1px solid',
                  boxShadow: isActive ? `0 0 10px ${config.color}80` : 'none',
                }}
              >
                {config.label}
              </div>
            </div>
          )
        })}
      </div>

      {/* Stage Metrics */}
      <div className="grid grid-cols-2 gap-3">
        <div className="bg-gray-900 rounded p-3 border border-gray-700">
          <div className="text-xs text-gray-400">Stage Score</div>
          <div className="text-2xl font-bold text-emerald-400">{(gold_rush.stage_score || 0).toFixed(1)}</div>
        </div>

        <div className="bg-gray-900 rounded p-3 border border-gray-700">
          <div className="text-xs text-gray-400">Velocity</div>
          <div className="text-2xl font-bold text-blue-400">{(gold_rush.velocity || 0).toFixed(1)}</div>
        </div>

        <div className="bg-gray-900 rounded p-3 border border-gray-700">
          <div className="text-xs text-gray-400">Breadth</div>
          <div className="text-2xl font-bold text-purple-400">{(gold_rush.breadth || 0).toFixed(1)}</div>
        </div>

        <div className="bg-gray-900 rounded p-3 border border-gray-700">
          <div className="text-xs text-gray-400">Acceleration</div>
          <div className="text-2xl font-bold text-orange-400">{(gold_rush.acceleration || 0).toFixed(1)}</div>
        </div>
      </div>

      {/* Recommendation Badge */}
      <div className="bg-gray-900 rounded p-4 border border-gray-700">
        <div className="text-xs text-gray-400 uppercase tracking-wider mb-2">Recommendation</div>
        <div className="flex gap-2">
          {['enter', 'hold', 'monitor', 'exit'].map((rec) => (
            <span
              key={rec}
              className={`px-3 py-1 rounded text-xs font-bold uppercase ${
                rec === (gold_rush.recommendation || 'hold')
                  ? 'bg-emerald-900 text-emerald-400'
                  : 'bg-gray-800 text-gray-500'
              }`}
            >
              {rec}
            </span>
          ))}
        </div>
      </div>
    </div>
  )
}

/* ──────────────────────────────────────────────
   Section 4: Catalyst Timeline
   ────────────────────────────────────────────── */
function CatalystTimeline({ data }) {
  const catalysts = data?.engines?.catalyst_engine?.catalysts || []

  const sortedCatalysts = useMemo(() => {
    return [...catalysts].sort((a, b) => (b.confidence || 0) - (a.confidence || 0))
  }, [catalysts])

  const typeIcons = {
    earnings: '📊',
    product: '🚀',
    regulatory: '⚖️',
    partnership: '🤝',
    social: '💬',
    macro: '🌍',
  }

  if (!sortedCatalysts.length) {
    return (
      <div className="bg-gray-800 border border-gray-700 rounded p-6">
        <h2 className="text-lg font-bold text-gray-200 mb-4">Catalyst Timeline</h2>
        <div className="text-sm text-gray-500">No catalysts detected yet.</div>
      </div>
    )
  }

  return (
    <div className="bg-gray-800 border border-gray-700 rounded p-6 space-y-4">
      <h2 className="text-lg font-bold text-gray-200 mb-4">Catalyst Timeline</h2>

      <div className="space-y-3">
        {sortedCatalysts.map((catalyst, idx) => {
          const type = catalyst.type || 'macro'
          const color = CATALYST_COLORS[type] || '#9ca3af'
          const icon = typeIcons[type] || '•'

          return (
            <div
              key={idx}
              className="bg-gray-900 rounded p-4 border border-gray-700 hover:border-gray-600 transition-colors"
              style={{ borderLeftColor: color, borderLeftWidth: 4 }}
            >
              <div className="flex items-start gap-3">
                <span className="text-xl">{icon}</span>

                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-xs font-bold uppercase rounded px-2 py-1" style={{ color, backgroundColor: `${color}20` }}>
                      {type}
                    </span>
                    {catalyst.impact && (
                      <span
                        className={`text-xs font-bold px-2 py-1 rounded uppercase ${
                          catalyst.impact === 'high'
                            ? 'bg-red-900 text-red-400'
                            : catalyst.impact === 'medium'
                              ? 'bg-yellow-900 text-yellow-400'
                              : 'bg-blue-900 text-blue-400'
                        }`}
                      >
                        {catalyst.impact} impact
                      </span>
                    )}
                  </div>

                  <p className="text-sm text-gray-300 mb-2">{catalyst.description || 'No description'}</p>

                  {/* Confidence Bar */}
                  <div className="flex items-center gap-2">
                    <div className="flex-1 bg-gray-800 rounded-full h-2 overflow-hidden">
                      <div
                        className="h-full transition-all"
                        style={{
                          width: `${(catalyst.confidence || 0) * 100}%`,
                          backgroundColor: color,
                        }}
                      ></div>
                    </div>
                    <span className="text-xs text-gray-400 w-12 text-right">{((catalyst.confidence || 0) * 100).toFixed(0)}%</span>
                  </div>
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

/* ──────────────────────────────────────────────
   Section 5: Conviction Scorecard
   ────────────────────────────────────────────── */
function ConvictionScorecard({ data }) {
  const conviction = data?.engines?.conviction_scorer || {}

  const dimensions = conviction.dimensions || [
    { name: 'Mosaic Coherence', score: 0, weight: 0.2 },
    { name: 'Information Asymmetry', score: 0, weight: 0.2 },
    { name: 'Lifecycle Momentum', score: 0, weight: 0.2 },
    { name: 'Catalyst Probability', score: 0, weight: 0.2 },
    { name: 'Technical Setup', score: 0, weight: 0.1 },
    { name: 'Risk/Reward Ratio', score: 0, weight: 0.1 },
  ]

  const radarData = dimensions.map((d) => ({
    name: d.name.split(' ')[0],
    value: d.score || 0,
    fullName: d.name,
  }))

  const convictionScore = conviction.conviction_score || 0
  const decision = conviction.decision || 'WAIT'
  const decisionColors = {
    GO: '#10b981',
    'NO-GO': '#ef4444',
    WAIT: '#f59e0b',
  }

  const strengths = conviction.key_strengths || []
  const risks = conviction.key_risks || []

  return (
    <div className="bg-gray-800 border border-gray-700 rounded p-6 space-y-4">
      <h2 className="text-lg font-bold text-gray-200 mb-4">Conviction Scorecard</h2>

      <div className="grid grid-cols-3 gap-4">
        {/* Radar Chart */}
        <div className="col-span-2 bg-gray-900 rounded p-4 border border-gray-700">
          <div className="text-sm text-gray-400 mb-3">6-Dimension Conviction Analysis</div>
          <ResponsiveContainer width="100%" height={300}>
            <RadarChart data={radarData}>
              <PolarGrid stroke="#374151" />
              <PolarAngleAxis dataKey="name" tick={{ fill: '#9ca3af', fontSize: 11 }} />
              <PolarRadiusAxis angle={90} domain={[0, 100]} tick={{ fill: '#6b7280', fontSize: 10 }} />
              <Radar
                name="Score"
                dataKey="value"
                stroke="#10b981"
                fill="#10b981"
                fillOpacity={0.3}
                dot={{ fill: '#10b981', r: 4 }}
              />
              <Tooltip
                contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: 4 }}
                labelStyle={{ color: '#d1d5db', fontSize: 11 }}
                itemStyle={{ fontSize: 11 }}
              />
            </RadarChart>
          </ResponsiveContainer>
        </div>

        {/* Total Conviction Score */}
        <div className="bg-gray-900 rounded p-4 border border-gray-700 flex flex-col justify-center items-center">
          <div className="text-xs text-gray-400 uppercase tracking-wider mb-2">Total Conviction</div>
          <div className="text-5xl font-bold text-emerald-400 mb-2">{convictionScore.toFixed(0)}</div>
          <div className="text-xs text-gray-500">/100</div>

          <div className="mt-6 w-full">
            <div className="text-xs text-gray-400 uppercase tracking-wider mb-2">Decision</div>
            <div
              className="rounded px-3 py-2 text-center font-bold text-white text-sm"
              style={{ backgroundColor: decisionColors[decision] || '#9ca3af' }}
            >
              {decision}
            </div>
          </div>
        </div>
      </div>

      {/* Dimension Scores */}
      <div className="bg-gray-900 rounded p-4 border border-gray-700 space-y-3">
        <div className="text-sm text-gray-400 mb-3">Dimension Breakdown</div>
        {dimensions.map((d, idx) => (
          <div key={idx} className="space-y-1">
            <div className="flex justify-between items-center">
              <div>
                <div className="text-sm text-gray-300">{d.name}</div>
                <div className="text-xs text-gray-500">Weight: {(d.weight * 100).toFixed(0)}%</div>
              </div>
              <div className="text-lg font-bold text-emerald-400">{(d.score || 0).toFixed(1)}</div>
            </div>
            <div className="w-full bg-gray-800 rounded-full h-2 overflow-hidden">
              <div
                className="bg-emerald-500 h-full transition-all"
                style={{ width: `${Math.min((d.score || 0), 100)}%` }}
              ></div>
            </div>
          </div>
        ))}
      </div>

      {/* Key Strengths and Risks */}
      <div className="grid grid-cols-2 gap-4">
        {/* Strengths */}
        <div className="bg-gray-900 rounded p-4 border border-gray-700 space-y-2">
          <div className="text-sm text-gray-400 uppercase tracking-wider mb-2">Key Strengths</div>
          <div className="space-y-2">
            {strengths.length > 0 ? (
              strengths.map((strength, idx) => (
                <div key={idx} className="flex items-start gap-2">
                  <span className="text-emerald-400 font-bold flex-shrink-0 mt-0.5">+</span>
                  <span className="text-xs text-gray-300">{strength}</span>
                </div>
              ))
            ) : (
              <p className="text-xs text-gray-500">No strengths identified</p>
            )}
          </div>
        </div>

        {/* Risks */}
        <div className="bg-gray-900 rounded p-4 border border-gray-700 space-y-2">
          <div className="text-sm text-gray-400 uppercase tracking-wider mb-2">Key Risks</div>
          <div className="space-y-2">
            {risks.length > 0 ? (
              risks.map((risk, idx) => (
                <div key={idx} className="flex items-start gap-2">
                  <span className="text-red-400 font-bold flex-shrink-0 mt-0.5">-</span>
                  <span className="text-xs text-gray-300">{risk}</span>
                </div>
              ))
            ) : (
              <p className="text-xs text-gray-500">No risks identified</p>
            )}
          </div>
        </div>
      </div>

      {/* Final Decision Banner */}
      <div
        className="rounded p-4 text-center font-bold text-white text-lg"
        style={{ backgroundColor: decisionColors[decision] || '#9ca3af' }}
      >
        {decision === 'GO'
          ? '✓ GO — Proceed with position sizing'
          : decision === 'NO-GO'
            ? '✗ NO-GO — Do not enter position'
            : '⏳ WAIT — Gather more data before deciding'}
      </div>
    </div>
  )
}

/* ──────────────────────────────────────────────
   Main Page Component
   ────────────────────────────────────────────── */
export default function MosaicWorkbench() {
  const { symbol } = useParams()
  const { data, loading, error } = useApi(() => api.getEngineOutput(symbol), [symbol])

  if (loading)
    return (
      <div className="text-gray-400 text-sm">
        Running Camillo mosaic engines for {symbol}...
      </div>
    )

  if (error)
    return <div className="text-red-400 text-sm">Error: {error.message}</div>

  if (!data)
    return <div className="text-gray-500 text-sm">No data available</div>

  return (
    <div className="space-y-6">
      {/* Section 1: Header */}
      <Header symbol={symbol} data={data} />

      {/* Sections 2 & 3: Asymmetry (60%) + Lifecycle (40%) */}
      <div className="grid grid-cols-3 gap-6">
        <div className="col-span-2">
          <AsymmetryPanel data={data} />
        </div>
        <div className="col-span-1">
          <LifecyclePanel data={data} />
        </div>
      </div>

      {/* Section 4: Catalyst Timeline */}
      <CatalystTimeline data={data} />

      {/* Section 5: Conviction Scorecard */}
      <ConvictionScorecard data={data} />
    </div>
  )
}
