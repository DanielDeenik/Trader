import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useApi } from '../hooks'
import { api } from '../api'
import { SymbolLink } from '../components/SymbolLink'

export default function Decisions() {
  const { data: reviews, refetch } = useApi(() => api.getReviews())
  const [expandedThesis, setExpandedThesis] = useState(null)
  const [executingId, setExecutingId] = useState(null)
  const [execForm, setExecForm] = useState({ direction: 'long', size: '', entry_price: '' })
  const [submitting, setSubmitting] = useState(false)
  const [msg, setMsg] = useState(null)

  const promoted = (reviews || []).filter(r => r.decision === 'promote' || r.decision === 'execute' || r.decision === 'forge')

  const handleExecute = async (e, review) => {
    e.preventDefault()
    setSubmitting(true)
    setMsg(null)
    try {
      await api.createPosition({
        symbol: review.symbol,
        direction: execForm.direction,
        size: parseFloat(execForm.size),
        entry_price: parseFloat(execForm.entry_price),
        thesis_id: review.entity_type === 'thesis' ? review.entity_id : null,
      })
      setMsg({ type: 'success', text: `Position created for ${review.symbol}` })
      setExecutingId(null)
      setExecForm({ direction: 'long', size: '', entry_price: '' })
    } catch (err) {
      setMsg({ type: 'error', text: `Failed: ${err.message}` })
    }
    setSubmitting(false)
    setTimeout(() => setMsg(null), 5000)
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div className="text-xs text-gray-400">{promoted.length} decisions made</div>
        <button onClick={refetch} className="text-xs px-2 py-1 bg-blue-900 text-blue-400 border border-blue-700 rounded hover:bg-blue-800">Refresh</button>
      </div>

      {msg && (
        <div className={`text-xs px-3 py-2 rounded ${msg.type === 'success' ? 'bg-emerald-900 text-emerald-400' : 'bg-red-900 text-red-400'}`}>
          {msg.text}
        </div>
      )}

      {promoted.map(r => (
        <div key={r.id} className="bg-gray-800 border border-gray-700 rounded p-3">
          <div className="flex justify-between items-center">
            <div className="flex items-center gap-3">
              <SymbolLink symbol={r.symbol} />
              <span className="text-xs text-gray-400">{r.gate}</span>
              <span className={`text-xs px-1.5 rounded ${r.decision === 'promote' || r.decision === 'execute' ? 'bg-emerald-900 text-emerald-400' : 'bg-blue-900 text-blue-400'}`}>{r.decision}</span>
            </div>
            <div className="flex gap-2 items-center">
              <span className="text-xs text-gray-500">{r.total_score}/{r.threshold}</span>
              <button
                onClick={() => {
                  setExecutingId(executingId === r.id ? null : r.id)
                  setExecForm({ direction: 'long', size: '', entry_price: '' })
                }}
                className={`text-xs px-2 py-1 border rounded no-underline hover:bg-emerald-800 ${executingId === r.id ? 'bg-emerald-800 text-emerald-300 border-emerald-600' : 'bg-emerald-900 text-emerald-400 border-emerald-700'}`}
              >
                {executingId === r.id ? 'Cancel' : 'Execute → Position'}
              </button>
              <Link to={`/mosaic/${r.symbol}`} className="text-xs px-2 py-1 bg-purple-900 text-purple-400 border border-purple-700 rounded no-underline hover:bg-purple-800">Workbench</Link>
              {r.entity_id && <button onClick={() => setExpandedThesis(expandedThesis === r.id ? null : r.id)} className="text-xs px-2 py-1 bg-blue-900 text-blue-400 border border-blue-700 rounded hover:bg-blue-800">View</button>}
            </div>
          </div>

          {/* Inline Execute Form */}
          {executingId === r.id && (
            <form onSubmit={(e) => handleExecute(e, r)} className="mt-3 border-t border-gray-700 pt-3 flex gap-3 items-end flex-wrap">
              <div>
                <label className="text-xs text-gray-400 block mb-1">Direction</label>
                <select value={execForm.direction} onChange={e => setExecForm({...execForm, direction: e.target.value})} className="bg-gray-900 border border-gray-600 rounded px-2 py-1 text-sm text-gray-200">
                  <option value="long">Long</option>
                  <option value="short">Short</option>
                </select>
              </div>
              <div>
                <label className="text-xs text-gray-400 block mb-1">Size ($)</label>
                <input type="number" step="0.01" required value={execForm.size} onChange={e => setExecForm({...execForm, size: e.target.value})} className="bg-gray-900 border border-gray-600 rounded px-2 py-1 text-sm text-gray-200 w-28" placeholder="10000" />
              </div>
              <div>
                <label className="text-xs text-gray-400 block mb-1">Entry Price</label>
                <input type="number" step="0.01" required value={execForm.entry_price} onChange={e => setExecForm({...execForm, entry_price: e.target.value})} className="bg-gray-900 border border-gray-600 rounded px-2 py-1 text-sm text-gray-200 w-28" placeholder="150.00" />
              </div>
              <button type="submit" disabled={submitting} className="bg-emerald-700 hover:bg-emerald-600 disabled:bg-gray-700 text-white text-xs px-4 py-1.5 rounded">
                {submitting ? 'Creating…' : 'Create Position'}
              </button>
            </form>
          )}

          {r.dominant_narrative && <div className="text-xs text-gray-400 mt-2">{r.dominant_narrative}</div>}
          {expandedThesis === r.id && r.entity_type === 'thesis' && (
            <div className="mt-2 border-t border-gray-700 pt-2 text-xs text-gray-400 space-y-1">
              <div>Entity ID: {r.entity_id}</div>
              <div>Type: {r.entity_type}</div>
              {r.scores_json && <pre className="bg-gray-900 p-2 rounded overflow-x-auto max-h-24 overflow-y-auto text-gray-500">{typeof r.scores_json === 'string' ? r.scores_json : JSON.stringify(r.scores_json, null, 2)}</pre>}
            </div>
          )}
        </div>
      ))}

      {promoted.length === 0 && <div className="text-gray-500 text-xs">No decisions yet. Promote signals through HITL gates.</div>}
    </div>
  )
}
