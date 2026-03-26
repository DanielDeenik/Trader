import { useApi } from '../hooks'
import { api } from '../api'
import { SymbolLink } from '../components/SymbolLink'

export default function Overview() {
  const { data: health } = useApi(() => api.getHealth())
  const { data: instruments } = useApi(() => api.getInstruments())
  const { data: reviews } = useApi(() => api.getReviews())

  const counts = health?.table_counts || {}

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-3 gap-3">
        {[
          ['Instruments', counts.instruments || 0],
          ['Signals', counts.signals || 0],
          ['OHLCV Bars', counts.ohlcv || 0],
          ['Mosaics', counts.mosaics || 0],
          ['Theses', counts.theses || 0],
          ['Reviews', counts.reviews || 0],
          ['Positions', counts.positions || 0],
          ['Tasks', counts.tasks || 0],
          ['STEPPS Scores', counts.stepps_scores || 0],
        ].map(([label, count]) => (
          <div key={label} className="bg-gray-800 border border-gray-700 rounded p-3">
            <div className="text-xs text-gray-400">{label}</div>
            <div className="text-xl font-bold mt-1">{count}</div>
          </div>
        ))}
      </div>

      {(instruments || []).length > 0 && (
        <div className="bg-gray-800 border border-gray-700 rounded p-3">
          <div className="text-xs font-bold mb-2">Tracked Instruments</div>
          <div className="flex flex-wrap gap-2">
            {(instruments || []).map(i => (
              <SymbolLink key={i.id} symbol={i.symbol} />
            ))}
          </div>
        </div>
      )}

      {(reviews || []).length > 0 && (
        <div className="bg-gray-800 border border-gray-700 rounded p-3">
          <div className="text-xs font-bold mb-2">Recent Reviews</div>
          {(reviews || []).slice(0, 5).map(r => (
            <div key={r.id} className="flex justify-between text-xs border-b border-gray-700 py-1">
              <span>{r.gate} — <SymbolLink symbol={r.symbol} /></span>
              <span className="text-gray-400">{r.decision}</span>
            </div>
          ))}
        </div>
      )}

      <div className="bg-gray-800/50 border border-gray-700 rounded p-3 text-xs text-gray-400">
        <p className="mb-1">Workflow: Add tickers → Collect data → Review signals (L1) → Assemble mosaics (L2) → Forge theses (L3) → Execute (L4) → Track (L5)</p>
      </div>
    </div>
  )
}
