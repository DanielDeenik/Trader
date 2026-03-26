import { useState } from 'react'
import { useApi } from '../hooks'
import { api } from '../api'
import { SymbolLink } from '../components/SymbolLink'

const SOURCE_COLORS = {
  yfinance: 'text-blue-400', reddit: 'text-orange-400', sec_edgar: 'text-yellow-400',
  google_trends: 'text-green-400', github: 'text-purple-400', coingecko: 'text-cyan-400', defillama: 'text-pink-400',
}

export default function SignalRadar() {
  const { data: signals, refetch } = useApi(() => api.getSignals())
  const [expanded, setExpanded] = useState(null)

  // Group by symbol
  const grouped = {}
  for (const s of (signals || [])) {
    if (!grouped[s.symbol]) grouped[s.symbol] = []
    grouped[s.symbol].push(s)
  }

  const formatAge = (ts) => {
    if (!ts) return '?'
    const mins = Math.floor((Date.now() - new Date(ts).getTime()) / 60000)
    if (mins < 60) return `${mins}m`
    if (mins < 1440) return `${Math.floor(mins / 60)}h`
    return `${Math.floor(mins / 1440)}d`
  }

  return (
    <div className="space-y-3">
      <div className="flex gap-2">
        <button onClick={refetch} className="px-3 py-1 bg-blue-900 text-blue-400 border border-blue-700 text-xs rounded">Refresh</button>
        <span className="text-xs text-gray-400 self-center">{(signals || []).length} signals across {Object.keys(grouped).length} symbols</span>
      </div>

      {Object.entries(grouped).sort((a, b) => b[1].length - a[1].length).map(([symbol, sigs]) => (
        <div key={symbol} className="bg-gray-800 border border-gray-700 rounded p-3">
          <div className="flex justify-between items-center cursor-pointer" onClick={() => setExpanded(expanded === symbol ? null : symbol)}>
            <div className="flex items-center gap-2">
              <SymbolLink symbol={symbol} />
              <span className="text-xs text-gray-500">{sigs.length} signals</span>
            </div>
            <div className="flex gap-1">
              {[...new Set(sigs.map(s => s.source))].map(src => (
                <span key={src} className={`text-xs ${SOURCE_COLORS[src] || 'text-gray-400'}`}>{src}</span>
              ))}
            </div>
          </div>

          {expanded === symbol && (
            <div className="mt-2 space-y-1 border-t border-gray-700 pt-2">
              {sigs.map(sig => (
                <div key={sig.id} className="bg-gray-900 border border-gray-700 rounded p-2 text-xs">
                  <div className="flex justify-between">
                    <span className={SOURCE_COLORS[sig.source] || 'text-gray-400'}>{sig.source}</span>
                    <span className="text-gray-500">{formatAge(sig.created_at || sig.timestamp)}</span>
                  </div>
                  <div className="text-gray-300 mt-1">
                    {sig.direction && <span className={sig.direction === 'bullish' ? 'text-green-400' : sig.direction === 'bearish' ? 'text-red-400' : 'text-gray-400'}>{sig.direction}</span>}
                    {sig.strength != null && <span className="text-gray-500 ml-2">str:{(sig.strength * 100).toFixed(0)}%</span>}
                    {sig.confidence != null && <span className="text-gray-500 ml-2">conf:{(sig.confidence * 100).toFixed(0)}%</span>}
                  </div>
                </div>
              ))}

              <a href={`/gate/review?gate=L1_triage&symbol=${symbol}&entity_type=signal_cluster`} className="block text-xs text-emerald-400 hover:text-emerald-300 mt-1 no-underline">→ Review at L1 Gate</a>
            </div>
          )}
        </div>
      ))}

      {Object.keys(grouped).length === 0 && <div className="text-gray-500 text-xs">No signals yet. Trigger collection from Task Queue.</div>}
    </div>
  )
}
