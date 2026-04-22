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
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ symbol: '', source: 'manual', signal_type: '', direction: 'bullish', strength: 0.5, confidence: 0.5, notes: '' })
  const [error, setError] = useState(null)
  const [saving, setSaving] = useState(false)

  const handleCreate = async (e) => {
    e.preventDefault()
    setSaving(true)
    setError(null)
    try {
      await api.createSignal({
        ...form,
        strength: parseFloat(form.strength),
        confidence: parseFloat(form.confidence),
      })
      setForm({ symbol: '', source: 'manual', signal_type: '', direction: 'bullish', strength: 0.5, confidence: 0.5, notes: '' })
      setShowForm(false)
      refetch()
    } catch (err) { setError(err.message) }
    finally { setSaving(false) }
  }

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
        {!showForm && (
          <button onClick={() => setShowForm(true)} className="px-3 py-1 bg-emerald-900 text-emerald-400 border border-emerald-700 text-xs rounded">+ Add Signal</button>
        )}
        <button onClick={refetch} className="px-3 py-1 bg-blue-900 text-blue-400 border border-blue-700 text-xs rounded">Refresh</button>
        <span className="text-xs text-gray-400 self-center">{(signals || []).length} signals across {Object.keys(grouped).length} symbols</span>
      </div>

      {showForm && (
        <form onSubmit={handleCreate} className="bg-gray-800 border border-gray-700 rounded p-3 space-y-2">
          <div className="grid grid-cols-2 gap-2">
            <div><label className="text-xs text-gray-400 block mb-1">Symbol</label><input value={form.symbol} onChange={e => setForm({...form, symbol: e.target.value})} required className="w-full bg-gray-900 border border-gray-700 text-gray-100 px-2 py-1 rounded text-xs" /></div>
            <div><label className="text-xs text-gray-400 block mb-1">Source</label><select value={form.source} onChange={e => setForm({...form, source: e.target.value})} className="w-full bg-gray-900 border border-gray-700 text-gray-100 px-2 py-1 rounded text-xs"><option value="manual">Manual</option><option value="research">Research</option><option value="news">News</option><option value="other">Other</option></select></div>
            <div><label className="text-xs text-gray-400 block mb-1">Signal Type</label><input value={form.signal_type} onChange={e => setForm({...form, signal_type: e.target.value})} required className="w-full bg-gray-900 border border-gray-700 text-gray-100 px-2 py-1 rounded text-xs" /></div>
            <div><label className="text-xs text-gray-400 block mb-1">Direction</label><select value={form.direction} onChange={e => setForm({...form, direction: e.target.value})} className="w-full bg-gray-900 border border-gray-700 text-gray-100 px-2 py-1 rounded text-xs"><option value="bullish">Bullish</option><option value="bearish">Bearish</option><option value="neutral">Neutral</option></select></div>
          </div>
          <div className="grid grid-cols-2 gap-2">
            <div><label className="text-xs text-gray-400 block mb-1">Strength (0-1)</label><input type="number" step="0.1" min="0" max="1" value={form.strength} onChange={e => setForm({...form, strength: e.target.value})} className="w-full bg-gray-900 border border-gray-700 text-gray-100 px-2 py-1 rounded text-xs" /></div>
            <div><label className="text-xs text-gray-400 block mb-1">Confidence (0-1)</label><input type="number" step="0.1" min="0" max="1" value={form.confidence} onChange={e => setForm({...form, confidence: e.target.value})} className="w-full bg-gray-900 border border-gray-700 text-gray-100 px-2 py-1 rounded text-xs" /></div>
          </div>
          <div><label className="text-xs text-gray-400 block mb-1">Notes</label><textarea value={form.notes} onChange={e => setForm({...form, notes: e.target.value})} className="w-full bg-gray-900 border border-gray-700 text-gray-100 px-2 py-1 rounded text-xs" rows="2" /></div>
          <div className="flex gap-2">
            <button type="submit" disabled={saving} className="px-3 py-1 bg-emerald-900 text-emerald-400 border border-emerald-700 text-xs rounded">{saving ? 'Adding...' : 'Add'}</button>
            <button type="button" onClick={() => setShowForm(false)} className="px-3 py-1 bg-gray-700 text-gray-300 border border-gray-600 text-xs rounded">Cancel</button>
          </div>
          {error && <div className="text-xs text-red-400">{error}</div>}
        </form>
      )}

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
