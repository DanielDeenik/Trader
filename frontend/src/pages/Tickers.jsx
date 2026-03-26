import { useState } from 'react'
import { useApi } from '../hooks'
import { api } from '../api'
import { SymbolLink } from '../components/SymbolLink'

export default function Tickers() {
  const { data: instruments, refetch } = useApi(() => api.getInstruments())
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ symbol: '', name: '', type: 'stock', data_class: 'public' })
  const [error, setError] = useState(null)
  const [saving, setSaving] = useState(false)

  const handleAdd = async (e) => {
    e.preventDefault()
    setSaving(true)
    setError(null)
    try {
      await api.createInstrument(form)
      setForm({ symbol: '', name: '', type: 'stock', data_class: 'public' })
      setShowForm(false)
      refetch()
    } catch (err) { setError(err.message) }
    finally { setSaving(false) }
  }

  const handleDelete = async (id) => {
    if (!confirm('Delete this instrument?')) return
    try { await api.deleteInstrument(id); refetch() }
    catch (err) { setError(err.message) }
  }

  return (
    <div className="space-y-4">
      {!showForm && (
        <button onClick={() => setShowForm(true)} className="px-3 py-1 bg-emerald-900 text-emerald-400 border border-emerald-700 text-xs rounded">+ Add Ticker</button>
      )}

      {showForm && (
        <form onSubmit={handleAdd} className="bg-gray-800 border border-gray-700 rounded p-3 space-y-2">
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="text-xs text-gray-400 block mb-1">Symbol</label>
              <input value={form.symbol} onChange={e => setForm({...form, symbol: e.target.value})} placeholder="NVDA" required className="w-full bg-gray-900 border border-gray-700 text-gray-100 px-2 py-1 rounded text-xs" />
            </div>
            <div>
              <label className="text-xs text-gray-400 block mb-1">Name</label>
              <input value={form.name} onChange={e => setForm({...form, name: e.target.value})} placeholder="NVIDIA Corp" required className="w-full bg-gray-900 border border-gray-700 text-gray-100 px-2 py-1 rounded text-xs" />
            </div>
            <div>
              <label className="text-xs text-gray-400 block mb-1">Type</label>
              <select value={form.type} onChange={e => setForm({...form, type: e.target.value})} className="w-full bg-gray-900 border border-gray-700 text-gray-100 px-2 py-1 rounded text-xs">
                <option value="stock">Stock</option>
                <option value="etf">ETF</option>
                <option value="crypto">Crypto</option>
                <option value="private">Private</option>
              </select>
            </div>
            <div>
              <label className="text-xs text-gray-400 block mb-1">Class</label>
              <select value={form.data_class} onChange={e => setForm({...form, data_class: e.target.value})} className="w-full bg-gray-900 border border-gray-700 text-gray-100 px-2 py-1 rounded text-xs">
                <option value="public">Public</option>
                <option value="private">Private</option>
              </select>
            </div>
          </div>
          <div className="flex gap-2">
            <button type="submit" disabled={saving} className="px-3 py-1 bg-emerald-900 text-emerald-400 border border-emerald-700 text-xs rounded">{saving ? 'Adding...' : 'Add'}</button>
            <button type="button" onClick={() => setShowForm(false)} className="px-3 py-1 bg-gray-700 text-gray-300 border border-gray-600 text-xs rounded">Cancel</button>
          </div>
          {error && <div className="text-xs text-red-400">{error}</div>}
        </form>
      )}

      <div className="bg-gray-800 border border-gray-700 rounded overflow-x-auto">
        <table className="w-full text-xs">
          <thead><tr className="border-b border-gray-700">
            <th className="text-left py-2 px-3">Symbol</th>
            <th className="text-left py-2 px-3">Name</th>
            <th className="text-left py-2 px-3">Type</th>
            <th className="text-left py-2 px-3">Class</th>
            <th className="text-right py-2 px-3"></th>
          </tr></thead>
          <tbody>
            {(instruments || []).map(i => (
              <tr key={i.id} className="border-b border-gray-700 hover:bg-gray-700/50">
                <td className="py-2 px-3"><SymbolLink symbol={i.symbol} /></td>
                <td className="py-2 px-3 text-gray-400">{i.name}</td>
                <td className="py-2 px-3 text-gray-400">{i.type}</td>
                <td className="py-2 px-3 text-gray-400">{i.data_class}</td>
                <td className="py-2 px-3 text-right"><button onClick={() => handleDelete(i.id)} className="text-red-400 hover:text-red-300">×</button></td>
              </tr>
            ))}
          </tbody>
        </table>
        {(!instruments || instruments.length === 0) && <div className="p-4 text-center text-gray-500 text-xs">No tickers yet</div>}
      </div>
    </div>
  )
}
