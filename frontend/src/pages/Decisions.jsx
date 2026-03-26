import { useApi } from '../hooks'
import { api } from '../api'
import { SymbolLink } from '../components/SymbolLink'

export default function Decisions() {
  const { data: reviews } = useApi(() => api.getReviews())

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
            <span className="text-xs text-gray-500">{r.total_score}/{r.threshold}</span>
          </div>
          {r.dominant_narrative && <div className="text-xs text-gray-400 mt-2">{r.dominant_narrative}</div>}
        </div>
      ))}

      {promoted.length === 0 && <div className="text-gray-500 text-xs">No decisions yet. Promote signals through HITL gates.</div>}
    </div>
  )
}
