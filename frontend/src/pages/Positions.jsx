import { useState } from 'react'
import { useApi } from '../hooks'
import { api } from '../api'
import { SymbolLink } from '../components/SymbolLink'

export default function Positions() {
  const { data: positions, refetch } = useApi(() => api.getPositions())
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ thesis_id: '', symbol: '', domain: 'public', direction: 'long', allocation_pct: '', conviction: 'medium', entry_price: '', entry_date: '' })
  const [error, setError] = useState(null)
  const [saving, setSaving] = useState(false)
  const [closeForm, setCloseForm] = useState(null)
  const [closeData, setCloseData] = useState({ exit_price: '', exit_date: '' })
  const [closeError, setCloseError] = useState(null)
  const [closeLoading, setCloseLoading] = useState(false)

  const handleAdd = async (e) => {
    e.preventDefault(); setSaving(true); setError(null)
    try {
      await api.createPosition({ ...form, thesis_id: parseInt(form.thesis_id) || 1, allocation_pct: parseFloat(form.allocation_pct), entry_price: parseFloat(form.entry_price), entry_date: form.entry_date || new Date().toISOString().split('T')[0] })
      setForm({ thesis_id: '', symbol: '', domain: 'public', direction: 'long', allocation_pct: '', conviction: 'medium', entry_price: '', entry_date: '' })
      setShowForm(false); refetch()
    } catch (err) { setError(err.message) }
    finally { setSaving(false) }
  }

  const handleClose = async (e) => {
    e.preventDefault(); setCloseLoading(true); setCloseError(null)
    try {
      await api.closePosition(closeForm, { exit_price: parseFloat(closeData.exit_price), exit_date: closeData.exit_date || new Date().toISOString().split('T')[0] })
      setCloseData({ exit_price: '', exit_date: '' })
      setCloseForm(null); refetch()
    } catch (err) { setCloseError(err.message) }
    finally { setCloseLoading(false) }
  }

  return (
    <div className="space-y-4">
      {!showForm && <button onClick={() => setShowForm(true)} className="px-3 py-1 bg-emerald-900 text-emerald-400 border border-emerald-700 text-xs rounded">+ Add Position</button>}

      {showForm && (
        <form onSubmit={handleAdd} className="bg-gray-800 border border-gray-700 rounded p-3 space-y-2">
          <div className="grid grid-cols-3 gap-2">
            <div><label className="text-xs text-gray-400 block mb-1">Symbol</label><input value={form.symbol} onChange={e => setForm({...form, symbol: e.target.value})} required className="w-full bg-gray-900 border border-gray-700 text-gray-100 px-2 py-1 rounded text-xs" /></div>
            <div><label className="text-xs text-gray-400 block mb-1">Entry Price</label><input type="number" step="0.01" value={form.entry_price} onChange={e => setForm({...form, entry_price: e.target.value})} required className="w-full bg-gray-900 border border-gray-700 text-gray-100 px-2 py-1 rounded text-xs" /></div>
            <div><label className="text-xs text-gray-400 block mb-1">Allocation %</label><input type="number" step="0.1" value={form.allocation_pct} onChange={e => setForm({...form, allocation_pct: e.target.value})} required className="w-full bg-gray-900 border border-gray-700 text-gray-100 px-2 py-1 rounded text-xs" /></div>
          </div>
          <div className="flex gap-2">
            <button type="submit" disabled={saving} className="px-3 py-1 bg-emerald-900 text-emerald-400 border border-emerald-700 text-xs rounded">{saving ? 'Adding...' : 'Add'}</button>
            <button type="button" onClick={() => setShowForm(false)} className="px-3 py-1 bg-gray-700 text-gray-300 border border-gray-600 text-xs rounded">Cancel</button>
          </div>
          {error && <div className="text-xs text-red-400">{error}</div>}
        </form>
      )}

      {closeForm && (
        <form onSubmit={handleClose} className="bg-gray-800 border border-gray-700 rounded p-3 space-y-2">
          <div className="text-xs font-bold text-gray-300 mb-2">Close Position #{closeForm}</div>
          <div className="grid grid-cols-2 gap-2">
            <div><label className="text-xs text-gray-400 block mb-1">Exit Price</label><input type="number" step="0.01" value={closeData.exit_price} onChange={e => setCloseData({...closeData, exit_price: e.target.value})} required className="w-full bg-gray-900 border border-gray-700 text-gray-100 px-2 py-1 rounded text-xs" /></div>
            <div><label className="text-xs text-gray-400 block mb-1">Exit Date</label><input type="date" value={closeData.exit_date} onChange={e => setCloseData({...closeData, exit_date: e.target.value})} className="w-full bg-gray-900 border border-gray-700 text-gray-100 px-2 py-1 rounded text-xs" /></div>
          </div>
          <div className="flex gap-2">
            <button type="submit" disabled={closeLoading} className="px-3 py-1 bg-red-900 text-red-400 border border-red-700 text-xs rounded">{closeLoading ? 'Closing...' : 'Close'}</button>
            <button type="button" onClick={() => setCloseForm(null)} className="px-3 py-1 bg-gray-700 text-gray-300 border border-gray-600 text-xs rounded">Cancel</button>
          </div>
          {closeError && <div className="text-xs text-red-400">{closeError}</div>}
        </form>
      )}

      <div className="bg-gray-800 border border-gray-700 rounded overflow-x-auto">
        <table className="w-full text-xs">
          <thead><tr className="border-b border-gray-700">
            <th className="text-left py-2 px-3">Symbol</th>
            <th className="text-left py-2 px-3">Direction</th>
            <th className="text-right py-2 px-3">Entry</th>
            <th className="text-right py-2 px-3">Alloc%</th>
            <th className="text-left py-2 px-3">Conviction</th>
            <th className="text-left py-2 px-3">Status</th>
            <th className="text-right py-2 px-3">P&L / Action</th>
          </tr></thead>
          <tbody>
            {(positions || []).map(p => (
              <tr key={p.id} className="border-b border-gray-700 hover:bg-gray-700/50">
                <td className="py-2 px-3"><SymbolLink symbol={p.symbol} /></td>
                <td className="py-2 px-3"><span className={p.direction === 'long' ? 'text-emerald-400' : 'text-red-400'}>{p.direction}</span></td>
                <td className="py-2 px-3 text-right text-gray-300">${parseFloat(p.entry_price).toFixed(2)}</td>
                <td className="py-2 px-3 text-right text-gray-300">{p.allocation_pct}%</td>
                <td className="py-2 px-3 text-gray-400">{p.conviction}</td>
                <td className="py-2 px-3"><span className={`px-1 rounded text-xs ${p.status === 'open' ? 'bg-emerald-900 text-emerald-400' : 'bg-gray-700 text-gray-400'}`}>{p.status || 'open'}</span></td>
                <td className="py-2 px-3 text-right">{p.status === 'open' ? <button onClick={() => setCloseForm(p.id)} className="text-red-400 hover:text-red-300 text-xs">Close</button> : (p.pnl_pct != null ? <span className={p.pnl_pct >= 0 ? 'text-emerald-400' : 'text-red-400'}>{p.pnl_pct.toFixed(1)}%</span> : '—')}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {(!positions || positions.length === 0) && <div className="p-4 text-center text-gray-500 text-xs">No positions yet</div>}
      </div>
    </div>
  )
}
