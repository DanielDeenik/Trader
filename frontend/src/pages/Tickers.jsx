import { useState, useEffect, useCallback } from 'react'
import { api } from '../api'
import { SymbolLink } from '../components/SymbolLink'

const PAGE_SIZE = 50

export default function Tickers() {
  // Data
  const [instruments, setInstruments] = useState([])
  const [total, setTotal] = useState(0)
  const [facets, setFacets] = useState({ sectors: [], exchanges: [], types: [] })
  const [loading, setLoading] = useState(true)

  // Filters
  const [search, setSearch] = useState('')
  const [typeFilter, setTypeFilter] = useState('')
  const [sectorFilter, setSectorFilter] = useState('')
  const [exchangeFilter, setExchangeFilter] = useState('')
  const [page, setPage] = useState(0)

  // Add form
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ symbol: '', name: '', type: 'stock', data_class: 'public' })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)

  // Debounced search
  const [debouncedSearch, setDebouncedSearch] = useState('')
  useEffect(() => {
    const t = setTimeout(() => setDebouncedSearch(search), 300)
    return () => clearTimeout(t)
  }, [search])

  // Load facets once
  useEffect(() => {
    api.getInstrumentFacets().then(setFacets).catch(() => {})
  }, [])

  // Fetch data
  const fetchData = useCallback(async () => {
    setLoading(true)
    try {
      const params = { limit: PAGE_SIZE, offset: page * PAGE_SIZE }
      if (debouncedSearch) params.search = debouncedSearch
      if (typeFilter) params.type = typeFilter
      if (sectorFilter) params.sector = sectorFilter
      if (exchangeFilter) params.exchange = exchangeFilter
      const res = await api.getInstruments(params)
      setInstruments(res.items || [])
      setTotal(res.total || 0)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [page, debouncedSearch, typeFilter, sectorFilter, exchangeFilter])

  useEffect(() => { fetchData() }, [fetchData])

  // Reset page when filters change
  useEffect(() => { setPage(0) }, [debouncedSearch, typeFilter, sectorFilter, exchangeFilter])

  const totalPages = Math.ceil(total / PAGE_SIZE)

  const handleAdd = async (e) => {
    e.preventDefault()
    setSaving(true)
    setError(null)
    try {
      await api.createInstrument(form)
      setForm({ symbol: '', name: '', type: 'stock', data_class: 'public' })
      setShowForm(false)
      fetchData()
    } catch (err) { setError(err.message) }
    finally { setSaving(false) }
  }

  const handleDelete = async (id) => {
    if (!confirm('Delete this instrument?')) return
    try { await api.deleteInstrument(id); fetchData() }
    catch (err) { setError(err.message) }
  }

  const formatMcap = (v) => {
    if (v == null) return '—'
    if (v >= 1000) return `$${(v / 1000).toFixed(1)}T`
    if (v >= 1) return `$${v.toFixed(1)}B`
    return `$${(v * 1000).toFixed(0)}M`
  }

  return (
    <div className="space-y-3">
      {/* Header */}
      <div className="flex items-center gap-3 flex-wrap">
        <span className="text-sm font-bold text-gray-200">Ticker Universe</span>
        <span className="text-xs text-gray-500">{total.toLocaleString()} instruments</span>
        <div className="ml-auto">
          {!showForm && (
            <button onClick={() => setShowForm(true)} className="px-3 py-1 bg-emerald-900 text-emerald-400 border border-emerald-700 text-xs rounded hover:bg-emerald-800">+ Add Ticker</button>
          )}
        </div>
      </div>

      {/* Add form */}
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

      {/* Search + Filters */}
      <div className="flex gap-2 flex-wrap items-center">
        <input
          value={search}
          onChange={e => setSearch(e.target.value)}
          placeholder="Search symbol or name..."
          className="bg-gray-900 border border-gray-700 text-gray-100 px-3 py-1.5 rounded text-xs w-64"
        />
        <select value={typeFilter} onChange={e => setTypeFilter(e.target.value)} className="bg-gray-900 border border-gray-700 text-gray-300 px-2 py-1.5 rounded text-xs">
          <option value="">All Types</option>
          {facets.types.map(t => <option key={t} value={t}>{t}</option>)}
        </select>
        <select value={sectorFilter} onChange={e => setSectorFilter(e.target.value)} className="bg-gray-900 border border-gray-700 text-gray-300 px-2 py-1.5 rounded text-xs">
          <option value="">All Sectors</option>
          {facets.sectors.map(s => <option key={s} value={s}>{s}</option>)}
        </select>
        <select value={exchangeFilter} onChange={e => setExchangeFilter(e.target.value)} className="bg-gray-900 border border-gray-700 text-gray-300 px-2 py-1.5 rounded text-xs">
          <option value="">All Exchanges</option>
          {facets.exchanges.map(e => <option key={e} value={e}>{e}</option>)}
        </select>
        {(search || typeFilter || sectorFilter || exchangeFilter) && (
          <button onClick={() => { setSearch(''); setTypeFilter(''); setSectorFilter(''); setExchangeFilter('') }} className="text-xs text-gray-400 hover:text-gray-200 underline">Clear</button>
        )}
      </div>

      {/* Table */}
      <div className="bg-gray-800 border border-gray-700 rounded overflow-x-auto">
        <table className="w-full text-xs">
          <thead><tr className="border-b border-gray-700 text-gray-400">
            <th className="text-left py-2 px-3">Symbol</th>
            <th className="text-left py-2 px-3">Name</th>
            <th className="text-left py-2 px-3">Type</th>
            <th className="text-left py-2 px-3">Sector</th>
            <th className="text-left py-2 px-3">Exchange</th>
            <th className="text-right py-2 px-3">Mkt Cap</th>
            <th className="text-center py-2 px-3">AI Score</th>
            <th className="text-center py-2 px-3">Trade Idea</th>
            <th className="text-right py-2 px-3 w-8"></th>
          </tr></thead>
          <tbody>
            {loading ? (
              <tr><td colSpan="9" className="py-4 text-center text-gray-500">Loading...</td></tr>
            ) : instruments.length === 0 ? (
              <tr><td colSpan="9" className="py-4 text-center text-gray-500">No instruments match your filters</td></tr>
            ) : instruments.map(i => (
              <tr key={i.id} className="border-b border-gray-700/50 hover:bg-gray-700/30">
                <td className="py-1.5 px-3 font-mono"><SymbolLink symbol={i.symbol} /></td>
                <td className="py-1.5 px-3 text-gray-400 truncate max-w-xs">{i.name}</td>
                <td className="py-1.5 px-3">
                  <span className={`px-1.5 py-0.5 rounded text-[10px] ${
                    i.type === 'stock' ? 'bg-blue-900/50 text-blue-400' :
                    i.type === 'etf' ? 'bg-purple-900/50 text-purple-400' :
                    i.type === 'crypto' ? 'bg-orange-900/50 text-orange-400' :
                    'bg-emerald-900/50 text-emerald-400'
                  }`}>{i.type}</span>
                </td>
                <td className="py-1.5 px-3 text-gray-500">{i.sector || '—'}</td>
                <td className="py-1.5 px-3 text-gray-500">{i.exchange || '—'}</td>
                <td className="py-1.5 px-3 text-right text-gray-400">{formatMcap(i.market_cap_b)}</td>
                <td className="py-1.5 px-3 text-center">
                  {i.ai_score != null ? (
                    <span className={`inline-block w-6 h-6 rounded-full text-[10px] font-bold leading-6 text-center ${
                      i.ai_score >= 8 ? 'bg-emerald-900/60 text-emerald-300' :
                      i.ai_score >= 6 ? 'bg-blue-900/60 text-blue-300' :
                      i.ai_score >= 4 ? 'bg-yellow-900/60 text-yellow-300' :
                      'bg-red-900/60 text-red-300'
                    }`}>{i.ai_score}</span>
                  ) : <span className="text-gray-600">—</span>}
                </td>
                <td className="py-1.5 px-3 text-center">
                  {i.trade_idea && i.trade_idea !== '—' ? (
                    <span className={`px-1.5 py-0.5 rounded text-[10px] font-semibold ${
                      i.trade_idea === 'BUY' ? 'bg-emerald-900/50 text-emerald-400' :
                      i.trade_idea === 'SELL' ? 'bg-red-900/50 text-red-400' :
                      'bg-gray-700 text-gray-400'
                    }`}>{i.trade_idea}</span>
                  ) : <span className="text-gray-600">—</span>}
                </td>
                <td className="py-1.5 px-3 text-right">
                  <button onClick={() => handleDelete(i.id)} className="text-red-400/50 hover:text-red-400 transition-colors">&times;</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between text-xs text-gray-400">
          <span>Page {page + 1} of {totalPages} ({total.toLocaleString()} results)</span>
          <div className="flex gap-1">
            <button
              onClick={() => setPage(0)}
              disabled={page === 0}
              className="px-2 py-1 bg-gray-800 border border-gray-700 rounded disabled:opacity-30 hover:bg-gray-700"
            >&laquo;</button>
            <button
              onClick={() => setPage(p => Math.max(0, p - 1))}
              disabled={page === 0}
              className="px-2 py-1 bg-gray-800 border border-gray-700 rounded disabled:opacity-30 hover:bg-gray-700"
            >&lsaquo; Prev</button>
            <button
              onClick={() => setPage(p => Math.min(totalPages - 1, p + 1))}
              disabled={page >= totalPages - 1}
              className="px-2 py-1 bg-gray-800 border border-gray-700 rounded disabled:opacity-30 hover:bg-gray-700"
            >Next &rsaquo;</button>
            <button
              onClick={() => setPage(totalPages - 1)}
              disabled={page >= totalPages - 1}
              className="px-2 py-1 bg-gray-800 border border-gray-700 rounded disabled:opacity-30 hover:bg-gray-700"
            >&raquo;</button>
          </div>
        </div>
      )}
    </div>
  )
}
