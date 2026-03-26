import { useState } from 'react'
import { useApi } from '../hooks'
import { api } from '../api'
import { SymbolLink } from '../components/SymbolLink'

export default function MosaicCards() {
  const { data: mosaics, refetch } = useApi(() => api.getMosaics())
  const [expanded, setExpanded] = useState(null)

  return (
    <div className="space-y-3">
      <div className="flex gap-2">
        <button onClick={refetch} className="px-3 py-1 bg-blue-900 text-blue-400 border border-blue-700 text-xs rounded">Refresh</button>
        <span className="text-xs text-gray-400 self-center">{(mosaics || []).length} mosaics</span>
      </div>

      {(mosaics || []).map(m => (
        <div key={m.id} className="bg-gray-800 border border-gray-700 rounded p-3">
          <div className="flex justify-between items-center cursor-pointer" onClick={() => setExpanded(expanded === m.id ? null : m.id)}>
            <div className="flex items-center gap-3">
              <SymbolLink symbol={m.symbol} />
              {m.coherence_score != null && <span className="text-xs text-gray-400">coherence: {(m.coherence_score * 100).toFixed(0)}%</span>}
              {m.action && <span className={`text-xs px-1 rounded ${m.action === 'promote' ? 'bg-emerald-900 text-emerald-400' : 'bg-gray-700 text-gray-400'}`}>{m.action}</span>}
            </div>
            <span className="text-xs text-gray-500">{m.domain}</span>
          </div>

          {expanded === m.id && (
            <div className="mt-2 border-t border-gray-700 pt-2 text-xs space-y-2">
              {m.narrative && <div className="bg-gray-900 p-2 rounded text-gray-300">{m.narrative}</div>}
              {m.fragments_json && (
                <pre className="bg-gray-900 p-2 rounded text-gray-400 overflow-x-auto max-h-32 overflow-y-auto">
                  {typeof m.fragments_json === 'string' ? m.fragments_json : JSON.stringify(m.fragments_json, null, 2)}
                </pre>
              )}
              <a href={`/gate/review?gate=L2_validation&symbol=${m.symbol}&entity_id=${m.id}&entity_type=mosaic`} className="block text-emerald-400 hover:text-emerald-300 no-underline">→ Review at L2 Gate</a>
            </div>
          )}
        </div>
      ))}

      {(!mosaics || mosaics.length === 0) && <div className="text-gray-500 text-xs">No mosaics yet. Run analysis to assemble signal clusters.</div>}
    </div>
  )
}
