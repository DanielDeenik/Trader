import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useApi } from '../hooks'
import { api } from '../api'
import { SymbolLink } from '../components/SymbolLink'

export default function MosaicCards() {
  const { data: mosaics, refetch } = useApi(() => api.getMosaics())
  const [expanded, setExpanded] = useState(null)
  const [msg, setMsg] = useState(null)

  const handleRunAnalysis = async () => {
    setMsg(null)
    try {
      await api.createTask({ task_type: 'analyze' })
      setMsg({ type: 'success', text: 'Analysis started — mosaics will update when complete' })
    } catch (err) {
      setMsg({ type: 'error', text: `Failed: ${err.message}` })
    }
    setTimeout(() => setMsg(null), 5000)
  }

  return (
    <div className="space-y-3">
      <div className="flex gap-2 items-center">
        <button onClick={refetch} className="px-3 py-1 bg-blue-900 text-blue-400 border border-blue-700 text-xs rounded hover:bg-blue-800">Refresh</button>
        <button onClick={handleRunAnalysis} className="px-3 py-1 bg-orange-900 text-orange-400 border border-orange-700 text-xs rounded hover:bg-orange-800">Run Analysis</button>
        <span className="text-xs text-gray-400 self-center">{(mosaics || []).length} mosaics</span>
      </div>

      {msg && (
        <div className={`text-xs px-3 py-2 rounded ${msg.type === 'success' ? 'bg-emerald-900 text-emerald-400' : 'bg-red-900 text-red-400'}`}>
          {msg.text}
        </div>
      )}

      {(mosaics || []).map(m => (
        <div key={m.id} className="bg-gray-800 border border-gray-700 rounded p-3">
          <div className="flex justify-between items-center cursor-pointer" onClick={() => setExpanded(expanded === m.id ? null : m.id)}>
            <div className="flex items-center gap-3">
              <SymbolLink symbol={m.symbol} />
              {m.coherence_score != null && <span className="text-xs text-gray-400">coherence: {(m.coherence_score * 100).toFixed(0)}%</span>}
              {m.action && <span className={`text-xs px-1 rounded ${m.action === 'promote' ? 'bg-emerald-900 text-emerald-400' : 'bg-gray-700 text-gray-400'}`}>{m.action}</span>}
            </div>
            <div className="flex items-center gap-2">
              <Link to={`/mosaic/${m.symbol}`} className="text-xs px-2 py-1 bg-purple-900 text-purple-400 border border-purple-700 rounded no-underline hover:bg-purple-800" onClick={e => e.stopPropagation()}>
                Workbench
              </Link>
              <span className="text-xs text-gray-500">{m.domain}</span>
            </div>
          </div>

          {expanded === m.id && (
            <div className="mt-2 border-t border-gray-700 pt-2 text-xs space-y-2">
              {m.narrative && <div className="bg-gray-900 p-2 rounded text-gray-300">{m.narrative}</div>}
              {m.fragments_json && (
                <pre className="bg-gray-900 p-2 rounded text-gray-400 overflow-x-auto max-h-32 overflow-y-auto">
                  {typeof m.fragments_json === 'string' ? m.fragments_json : JSON.stringify(m.fragments_json, null, 2)}
                </pre>
              )}
              <div className="flex gap-2">
                <Link to={`/gate/review?gate=L2_validation&symbol=${m.symbol}&entity_id=${m.id}&entity_type=mosaic`} className="text-xs px-2 py-1 bg-emerald-900 text-emerald-400 border border-emerald-700 rounded no-underline hover:bg-emerald-800">
                  Promote → Gate Review
                </Link>
                <Link to={`/deepdive/${m.symbol}`} className="text-xs px-2 py-1 bg-blue-900 text-blue-400 border border-blue-700 rounded no-underline hover:bg-blue-800">
                  Deep Dive
                </Link>
                <Link to={`/lattice/${m.symbol}`} className="text-xs px-2 py-1 bg-purple-900 text-purple-400 border border-purple-700 rounded no-underline hover:bg-purple-800">
                  Lattice
                </Link>
              </div>
            </div>
          )}
        </div>
      ))}

      {(!mosaics || mosaics.length === 0) && <div className="text-gray-500 text-xs">No mosaics yet. Run analysis to assemble signal clusters.</div>}
    </div>
  )
}
