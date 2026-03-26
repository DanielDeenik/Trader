import { useState } from 'react'
import { useApi } from '../hooks'
import { api } from '../api'
import { SymbolLink } from '../components/SymbolLink'

export default function ThesisForge() {
  const { data: theses, refetch } = useApi(() => api.getTheses())
  const [expanded, setExpanded] = useState(null)

  return (
    <div className="space-y-3">
      <div className="flex gap-2">
        <button onClick={refetch} className="px-3 py-1 bg-blue-900 text-blue-400 border border-blue-700 text-xs rounded">Refresh</button>
        <span className="text-xs text-gray-400 self-center">{(theses || []).length} theses</span>
      </div>

      {(theses || []).map(t => (
        <div key={t.id} className="bg-gray-800 border border-gray-700 rounded p-3">
          <div className="flex justify-between items-center cursor-pointer" onClick={() => setExpanded(expanded === t.id ? null : t.id)}>
            <div className="flex items-center gap-3">
              <SymbolLink symbol={t.symbol} />
              {t.lifecycle_stage && <span className="text-xs text-yellow-400">{t.lifecycle_stage}</span>}
              {t.status && <span className={`text-xs px-1 rounded ${t.status === 'active' ? 'bg-emerald-900 text-emerald-400' : 'bg-gray-700 text-gray-400'}`}>{t.status}</span>}
            </div>
            <span className="text-xs text-gray-500">{t.domain}</span>
          </div>

          {expanded === t.id && (
            <div className="mt-2 border-t border-gray-700 pt-2 text-xs space-y-2">
              <div className="grid grid-cols-3 gap-2">
                <div className="bg-red-900/30 p-2 rounded"><span className="text-gray-400">Bear:</span> <span className="text-red-400">{t.roi_bear != null ? `${(t.roi_bear * 100).toFixed(0)}%` : '—'}</span></div>
                <div className="bg-gray-900 p-2 rounded"><span className="text-gray-400">Base:</span> <span className="text-gray-200">{t.roi_base != null ? `${(t.roi_base * 100).toFixed(0)}%` : '—'}</span></div>
                <div className="bg-emerald-900/30 p-2 rounded"><span className="text-gray-400">Bull:</span> <span className="text-emerald-400">{t.roi_bull != null ? `${(t.roi_bull * 100).toFixed(0)}%` : '—'}</span></div>
              </div>
              {t.kelly_fraction != null && <div className="text-gray-400">Kelly: {(t.kelly_fraction * 100).toFixed(1)}%</div>}
              {t.vulnerability_json && <pre className="bg-gray-900 p-2 rounded text-gray-400 overflow-x-auto max-h-24 overflow-y-auto">{typeof t.vulnerability_json === 'string' ? t.vulnerability_json : JSON.stringify(t.vulnerability_json, null, 2)}</pre>}
              <a href={`/gate/review?gate=L3_conviction&symbol=${t.symbol}&entity_id=${t.id}&entity_type=thesis`} className="block text-emerald-400 hover:text-emerald-300 no-underline">→ Review at L3 Gate</a>
            </div>
          )}
        </div>
      ))}

      {(!theses || theses.length === 0) && <div className="text-gray-500 text-xs">No theses yet. Run analysis to forge theses from mosaics.</div>}
    </div>
  )
}
