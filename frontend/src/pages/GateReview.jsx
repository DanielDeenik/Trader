import { useState } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import { api } from '../api'

const GATE_CONFIGS = {
  L1_triage: {
    label: 'L1: Signal Triage',
    description: 'Initial signal quality assessment (20 pts)',
    criteria: [
      { id: 'signal_diversity', label: 'Signal Diversity', hint: 'Multiple sources conveying same thesis' },
      { id: 'source_credibility', label: 'Source Credibility', hint: 'Track record of signal source' },
      { id: 'narrative_coherence', label: 'Narrative Coherence', hint: 'Story holds together logically' },
      { id: 'virality_potential', label: 'Virality Potential', hint: 'Likelihood of social amplification' },
    ],
    threshold: 12,
    max: 20,
    decisions: [
      { value: 'promote', label: 'Promote to L2', color: 'emerald' },
      { value: 'watch', label: 'Watch', color: 'amber' },
      { value: 'discard', label: 'Discard', color: 'red' },
    ],
  },
  L2_validation: {
    label: 'L2: Mosaic Validation',
    description: 'Mosaic coherence & signal alignment (20 pts)',
    criteria: [
      { id: 'divergence_strength', label: 'Divergence Strength', hint: 'Social vs market sentiment gap' },
      { id: 'mosaic_coherence', label: 'Mosaic Coherence', hint: 'Signals reinforce central thesis' },
      { id: 'cross_source_validation', label: 'Cross-Source Validation', hint: 'Different sources agree' },
      { id: 'thesis_potential', label: 'Thesis Potential', hint: 'Can support investment decision' },
    ],
    threshold: 12,
    max: 20,
    decisions: [
      { value: 'forge', label: 'Forge Thesis', color: 'emerald' },
      { value: 'watch', label: 'Watch', color: 'amber' },
      { value: 'discard', label: 'Discard', color: 'red' },
    ],
  },
  L3_conviction: {
    label: 'L3: Conviction & Execution',
    description: 'Investment conviction & risk/reward (25 pts)',
    criteria: [
      { id: 'risk_reward_ratio', label: 'Risk/Reward Ratio', hint: 'Asymmetry in payoff structure' },
      { id: 'kelly_confidence', label: 'Kelly Confidence', hint: 'Sizing model conviction' },
      { id: 'catalyst_strength', label: 'Catalyst Strength', hint: 'Near-term catalysts present' },
      { id: 'market_timing', label: 'Market Timing', hint: 'Entry point validity' },
      { id: 'asymmetry_quality', label: 'Asymmetry Quality', hint: 'Information gap durability' },
    ],
    threshold: 15,
    max: 25,
    decisions: [
      { value: 'execute', label: 'Execute Position', color: 'emerald' },
      { value: 'defer', label: 'Defer (await catalyst)', color: 'amber' },
      { value: 'reject', label: 'Reject', color: 'red' },
    ],
  },
}

export default function GateReview() {
  const [params] = useSearchParams()
  const navigate = useNavigate()

  const gate = params.get('gate') || 'L1_triage'
  const symbol = params.get('symbol') || ''
  const entityId = params.get('entity_id')
  const entityType = params.get('entity_type') || 'signal'

  const config = GATE_CONFIGS[gate] || GATE_CONFIGS.L1_triage
  const [scores, setScores] = useState({})
  const [decision, setDecision] = useState(null)
  const [narratives, setNarratives] = useState({
    narrative: '',
    dominant_narrative: '',
    market_pricing: '',
    invalidation: '',
    risk_note: '',
    position_size: '',
  })
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState(null)
  const [success, setSuccess] = useState(false)

  const total = config.criteria.reduce((s, c) => s + (scores[c.id] || 0), 0)
  const passing = total >= config.threshold

  const handleScoreChange = (critId, value) => {
    setScores({ ...scores, [critId]: Math.max(1, Math.min(5, value)) })
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!decision) {
      setError('Select a decision')
      return
    }

    setSubmitting(true)
    setError(null)

    try {
      await api.createReview({
        gate,
        symbol,
        entity_id: parseInt(entityId) || 0,
        entity_type: entityType,
        scores,
        decision,
        ...narratives,
      })
      setSuccess(true)
      setTimeout(() => navigate(-1), 1500)
    } catch (err) {
      setError(err.message || 'Failed to submit review')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="max-w-3xl space-y-4">
      {/* Header */}
      <div className="bg-[#111827]/80 border border-white/[0.06] rounded-xl p-4">
        <h2 className="text-sm font-bold text-white mb-1">{config.label}</h2>
        <p className="text-xs text-gray-400 mb-3">{config.description}</p>
        <div className="flex items-center justify-between">
          <span className="text-sm font-mono text-emerald-400">{symbol}</span>
          <div className="text-xs">
            <span className="text-gray-400">Score: </span>
            <span className={`font-mono font-bold ${passing ? 'text-emerald-400' : 'text-red-400'}`}>
              {total}/{config.max}
            </span>
            <span className={`ml-2 ${passing ? 'text-emerald-400' : 'text-red-400'}`}>
              {passing ? '✓ PASS' : `✗ NEED ${config.threshold}`}
            </span>
          </div>
        </div>
      </div>

      {/* Score Sliders */}
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="bg-[#111827]/80 border border-white/[0.06] rounded-xl p-4">
          <h3 className="text-xs font-bold text-white/60 mb-4 uppercase tracking-wider">Scoring Criteria</h3>

          <div className="space-y-4">
            {config.criteria.map((crit) => (
              <div key={crit.id}>
                <div className="flex items-center justify-between mb-2">
                  <div>
                    <label className="text-xs font-semibold text-gray-300">{crit.label}</label>
                    <p className="text-xs text-gray-500 mt-0.5">{crit.hint}</p>
                  </div>
                  <div className="text-sm font-mono text-emerald-400 font-bold">
                    {scores[crit.id] || 0}/5
                  </div>
                </div>

                <div className="flex gap-1">
                  {[1, 2, 3, 4, 5].map((score) => (
                    <button
                      key={score}
                      type="button"
                      onClick={() => handleScoreChange(crit.id, score)}
                      className={`flex-1 py-2 rounded text-xs font-bold transition-all ${
                        scores[crit.id] === score
                          ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                          : 'bg-white/[0.04] text-gray-400 hover:bg-white/[0.08] border border-white/[0.06]'
                      }`}
                    >
                      {score}
                    </button>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Decision */}
        <div className="bg-[#111827]/80 border border-white/[0.06] rounded-xl p-4">
          <h3 className="text-xs font-bold text-white/60 mb-3 uppercase tracking-wider">Decision</h3>

          <div className="flex gap-2 flex-wrap">
            {config.decisions.map((dec) => {
              const isActive = decision === dec.value;
              const colorMap = {
                emerald: isActive ? 'bg-emerald-500/20 border-emerald-500/30 text-emerald-300' : '',
                amber: isActive ? 'bg-amber-500/20 border-amber-500/30 text-amber-300' : '',
                red: isActive ? 'bg-red-500/20 border-red-500/30 text-red-300' : '',
              };
              return (
              <button
                key={dec.value}
                type="button"
                onClick={() => setDecision(dec.value)}
                className={`px-4 py-2 rounded-lg text-xs font-bold transition-all border ${
                  isActive
                    ? colorMap[dec.color] || 'bg-emerald-500/20 border-emerald-500/30 text-emerald-300'
                    : 'bg-white/[0.04] border-white/[0.06] text-gray-400 hover:bg-white/[0.08]'
                }`}
              >
                {dec.label}
              </button>
              );
            })}
          </div>
        </div>

        {/* Narrative Fields */}
        <div className="bg-[#111827]/80 border border-white/[0.06] rounded-xl p-4 space-y-3">
          <h3 className="text-xs font-bold text-white/60 uppercase tracking-wider">Investment Narrative</h3>

          <div>
            <label className="text-xs text-gray-400 block mb-1">Dominant Narrative</label>
            <textarea
              value={narratives.dominant_narrative}
              onChange={(e) =>
                setNarratives({ ...narratives, dominant_narrative: e.target.value })
              }
              placeholder="Core story behind this investment..."
              className="w-full bg-white/[0.04] border border-white/[0.08] text-white px-3 py-2 rounded-lg text-xs h-14 resize-none focus:outline-none focus:border-emerald-500/50 focus:ring-1 focus:ring-emerald-500/20 transition"
            />
          </div>

          <div>
            <label className="text-xs text-gray-400 block mb-1">Market Pricing</label>
            <textarea
              value={narratives.market_pricing}
              onChange={(e) => setNarratives({ ...narratives, market_pricing: e.target.value })}
              placeholder="How is this thesis currently priced by market?..."
              className="w-full bg-white/[0.04] border border-white/[0.08] text-white px-3 py-2 rounded-lg text-xs h-14 resize-none focus:outline-none focus:border-emerald-500/50 focus:ring-1 focus:ring-emerald-500/20 transition"
            />
          </div>

          <div>
            <label className="text-xs text-gray-400 block mb-1">Invalidation Triggers</label>
            <textarea
              value={narratives.invalidation}
              onChange={(e) => setNarratives({ ...narratives, invalidation: e.target.value })}
              placeholder="What would disprove this thesis?..."
              className="w-full bg-white/[0.04] border border-white/[0.08] text-white px-3 py-2 rounded-lg text-xs h-14 resize-none focus:outline-none focus:border-emerald-500/50 focus:ring-1 focus:ring-emerald-500/20 transition"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs text-gray-400 block mb-1">Position Size</label>
              <input
                type="text"
                value={narratives.position_size}
                onChange={(e) => setNarratives({ ...narratives, position_size: e.target.value })}
                placeholder="e.g., 2% portfolio"
                className="w-full bg-white/[0.04] border border-white/[0.08] text-white px-3 py-2 rounded-lg text-xs focus:outline-none focus:border-emerald-500/50 focus:ring-1 focus:ring-emerald-500/20 transition"
              />
            </div>

            <div>
              <label className="text-xs text-gray-400 block mb-1">Risk Note</label>
              <input
                type="text"
                value={narratives.risk_note}
                onChange={(e) => setNarratives({ ...narratives, risk_note: e.target.value })}
                placeholder="Key risks to monitor..."
                className="w-full bg-white/[0.04] border border-white/[0.08] text-white px-3 py-2 rounded-lg text-xs focus:outline-none focus:border-emerald-500/50 focus:ring-1 focus:ring-emerald-500/20 transition"
              />
            </div>
          </div>
        </div>

        {/* Messages */}
        {error && <div className="text-xs text-red-400 bg-red-500/10 px-3 py-2 rounded-lg border border-red-500/20">{error}</div>}
        {success && (
          <div className="text-xs text-emerald-400 bg-emerald-500/10 px-3 py-2 rounded-lg border border-emerald-500/20">
            Review submitted
          </div>
        )}

        {/* Submit */}
        <button
          type="submit"
          disabled={submitting || !decision}
          className="w-full px-4 py-2.5 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 font-medium text-xs rounded-lg hover:bg-emerald-500/20 disabled:opacity-50 disabled:cursor-not-allowed transition"
        >
          {submitting ? 'Submitting…' : `Submit ${config.label}`}
        </button>
      </form>
    </div>
  )
}
