import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useApi } from '../hooks'
import { api } from '../api'
import { SymbolLink } from '../components/SymbolLink'

export default function Decisions() {
  const { data: reviews } = useApi(() => api.getReviews())
  const [expandedThesis, setExpandedThesis] = useState(null)

  const promoted = (reviews || []).filter(r => r.decision === 'promote' || r.decision === 'execute' || r.decision === 'forge')

  return (
    <div className="space-y-3">
      <div className="text-xs text-gray-400">{promoted.length} decisions made</div>

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
              <Link to={`/positions`} className="text-xs px-2 py-1 bg-emerald-900 text-emerald-400 border border-emerald-700 rounded no-underline hover:bg-emerald-800">Execute</Link>
              {r.entity_id && <button onClick={() => setExpandedThesis(expandedThesis === r.id ? null : r.id)} className="text-xs px-2 py-1 bg-blue-900 text-blue-400 border border-blue-700 rounded hover:bg-blue-800">View</button>}
            </div>
          </div>
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
