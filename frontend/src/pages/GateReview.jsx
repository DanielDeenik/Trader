import { useState } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import { api } from '../api'
import { ScoreSlider } from '../components/ScoreSlider'
import { DecisionButton } from '../components/DecisionButton'

const GATE_CONFIG = {
  L1_triage: { label: 'L1: Signal Triage', criteria: ['signal_quality', 'source_diversity', 'timing', 'novelty'], threshold: 12, max: 20 },
  L2_validation: { label: 'L2: Mosaic Validation', criteria: ['coherence', 'divergence_strength', 'multi_domain', 'data_freshness'], threshold: 12, max: 20 },
  L3_conviction: { label: 'L3: Thesis Conviction', criteria: ['thesis_clarity', 'risk_reward', 'market_timing', 'catalyst_strength', 'invalidation_clarity'], threshold: 15, max: 25 },
}

export default function GateReview() {
  const [params] = useSearchParams()
  const navigate = useNavigate()
  const gate = params.get('gate') || 'L1_triage'
  const symbol = params.get('symbol') || ''
  const entityId = params.get('entity_id')
  const entityType = params.get('entity_type') || 'signal_cluster'

  const config = GATE_CONFIG[gate] || GATE_CONFIG.L1_triage
  const [scores, setScores] = useState({})
  const [decision, setDecision] = useState(null)
  const [narratives, setNarratives] = useState({ dominant_narrative: '', market_pricing: '', invalidation: '', position_size: '', risk_note: '' })
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState(null)
  const [success, setSuccess] = useState(false)

  const total = config.criteria.reduce((s, c) => s + (scores[c] || 0), 0)
  const passing = total >= config.threshold

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!decision) { setError('Select a decision'); return }
    setSubmitting(true); setError(null)
    try {
      await api.createReview({ gate, symbol, entity_id: parseInt(entityId) || 0, entity_type: entityType, scores, decision, ...narratives })
      setSuccess(true)
      setTimeout(() => navigate(-1), 1500)
    } catch (err) { setError(err.message) }
    finally { setSubmitting(false) }
  }

  return (
    <div className="max-w-2xl space-y-4">
      <div className="text-sm"><span className="text-gray-400">{config.label}</span> <span className="text-emerald-400 font-mono ml-2">{symbol}</span></div>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="bg-gray-800 border border-gray-700 rounded p-3">
          <div className="text-xs font-bold mb-3">
            Score: {total}/{config.max}
            <span className={`ml-2 ${passing ? 'text-emerald-400' : 'text-red-400'}`}>{passing ? '✓ Pass' : `✗ Need ${config.threshold}`}</span>
          </div>
          {config.criteria.map(c => (
            <ScoreSlider key={c} criterion={c.replace(/_/g, ' ')} score={scores[c] || 0} onScore={v => setScores({...scores, [c]: v})} />
          ))}
        </div>

        <div className="bg-gray-800 border border-gray-700 rounded p-3">
          <div className="text-xs font-bold mb-2">Decision</div>
          <DecisionButton decision={decision} onDecision={setDecision} gate={gate} />
        </div>

        <div className="bg-gray-800 border border-gray-700 rounded p-3 space-y-2">
          <div className="text-xs font-bold">Notes</div>
          {[['dominant_narrative', 'Dominant Narrative'], ['market_pricing', 'Market Pricing'], ['invalidation', 'Invalidation Triggers'], ['risk_note', 'Risk Note']].map(([key, label]) => (
            <div key={key}>
              <label className="text-xs text-gray-400 block mb-1">{label}</label>
              <textarea value={narratives[key]} onChange={e => setNarratives({...narratives, [key]: e.target.value})} className="w-full bg-gray-900 border border-gray-700 text-gray-100 px-2 py-1 rounded text-xs h-12" />
            </div>
          ))}
          <div>
            <label className="text-xs text-gray-400 block mb-1">Position Size</label>
            <input value={narratives.position_size} onChange={e => setNarratives({...narratives, position_size: e.target.value})} placeholder="e.g., 2% portfolio" className="w-full bg-gray-900 border border-gray-700 text-gray-100 px-2 py-1 rounded text-xs" />
          </div>
        </div>

        {error && <div className="text-xs text-red-400">{error}</div>}
        {success && <div className="text-xs text-emerald-400">✓ Review submitted</div>}

        <button type="submit" disabled={submitting || !decision} className="w-full px-4 py-2 bg-blue-900 text-blue-400 border border-blue-700 text-xs rounded disabled:opacity-50">
          {submitting ? 'Submitting...' : 'Submit Review'}
        </button>
      </form>
    </div>
  )
}
