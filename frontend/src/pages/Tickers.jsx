import { useState, useEffect, useCallback } from 'react'
import { api } from '../api'
import { Link } from 'react-router-dom'

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
      console.error(err)
    } finally {
      setLoading(false)
    }
  }, [page, debouncedSearch, typeFilter, sectorFilter, exchangeFilter])

  useEffect(() => { fetchData() }, [fetchData])

  // Reset page when filters change
  useEffect(() => { setPage(0) }, [debouncedSearch, typeFilter, sectorFilter, exchangeFilter])

  const totalPages = Math.ceil(total / PAGE_SIZE)

  const formatMcap = (v) => {
    if (v == null) return '—'
    if (v >= 1000) return `$${(v / 1000).toFixed(1)}T`
    if (v >= 1) return `$${v.toFixed(1)}B`
    return `$${(v * 1000).toFixed(0)}M`
  }

  const getTypeBadgeColor = (type) => {
    switch (type) {
      case 'stock':
        return 'bg-blue-500/10 text-blue-400 border border-blue-500/20'
      case 'etf':
        return 'bg-purple-500/10 text-purple-400 border border-purple-500/20'
      case 'crypto':
        return 'bg-orange-500/10 text-orange-400 border border-orange-500/20'
      case 'private':
        return 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
      default:
        return 'bg-gray-500/10 text-gray-400 border border-gray-500/20'
    }
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-bold text-white">Ticker Universe</h1>
          <p className="text-xs text-gray-400 mt-1">{total.toLocaleString()} instruments</p>
        </div>
      </div>

      {/* Search + Filters */}
      <div className="bg-[#111827]/80 border border-white/[0.06] rounded-xl p-4 space-y-3">
        <div>
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search symbol or name..."
            className="w-full bg-white/[0.04] border border-white/[0.08] rounded-lg px-3 py-2 text-[13px] text-white placeholder-gray-500 focus:outline-none focus:border-emerald-500/50 focus:ring-1 focus:ring-emerald-500/20 transition"
          />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            className="bg-white/[0.04] border border-white/[0.08] rounded-lg px-3 py-2 text-[13px] text-white focus:outline-none focus:border-emerald-500/50 focus:ring-1 focus:ring-emerald-500/20 transition"
          >
            <option value="">All Types</option>
            {facets.types && facets.types.map(t => (
              <option key={t} value={t}>{t.charAt(0).toUpperCase() + t.slice(1)}</option>
            ))}
          </select>

          <select
            value={sectorFilter}
            onChange={(e) => setSectorFilter(e.target.value)}
            className="bg-white/[0.04] border border-white/[0.08] rounded-lg px-3 py-2 text-[13px] text-white focus:outline-none focus:border-emerald-500/50 focus:ring-1 focus:ring-emerald-500/20 transition"
          >
            <option value="">All Sectors</option>
            {facets.sectors && facets.sectors.map(s => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>

          <select
            value={exchangeFilter}
            onChange={(e) => setExchangeFilter(e.target.value)}
            className="bg-white/[0.04] border border-white/[0.08] rounded-lg px-3 py-2 text-[13px] text-white focus:outline-none focus:border-emerald-500/50 focus:ring-1 focus:ring-emerald-500/20 transition"
          >
            <option value="">All Exchanges</option>
            {facets.exchanges && facets.exchanges.map(e => (
              <option key={e} value={e}>{e}</option>
            ))}
          </select>
        </div>

        {(search || typeFilter || sectorFilter || exchangeFilter) && (
          <button
            onClick={() => {
              setSearch('')
              setTypeFilter('')
              setSectorFilter('')
              setExchangeFilter('')
            }}
            className="text-xs text-amber-400 hover:text-amber-300 transition"
          >
            Clear filters
          </button>
        )}
      </div>

      {/* Table */}
      <div className="bg-[#111827]/80 border border-white/[0.06] rounded-xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-[13px]">
            <thead>
              <tr className="bg-white/[0.03] border-b border-white/[0.06]">
                <th className="text-left py-3 px-4 font-mono text-gray-400">Symbol</th>
                <th className="text-left py-3 px-4 text-gray-400">Name</th>
                <th className="text-left py-3 px-4 text-gray-400">Type</th>
                <th className="text-left py-3 px-4 text-gray-400">Sector</th>
                <th className="text-left py-3 px-4 text-gray-400">Exchange</th>
                <th className="text-right py-3 px-4 font-mono text-gray-400">Market Cap</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan="6" className="py-8 px-4 text-center text-gray-500">
                    <div className="flex items-center justify-center gap-2">
                      <div className="w-4 h-4 border-2 border-emerald-400/30 border-t-emerald-400 rounded-full animate-spin" />
                      <span>Loading instruments...</span>
                    </div>
                  </td>
                </tr>
              ) : instruments.length === 0 ? (
                <tr>
                  <td colSpan="6" className="py-8 px-4 text-center text-gray-500">
                    No instruments found
                  </td>
                </tr>
              ) : (
                instruments.map(instrument => (
                  <tr key={instrument.id} className="border-b border-white/[0.03] hover:bg-white/[0.02] transition">
                    <td className="py-3 px-4">
                      <Link
                        to={`/tickers/${instrument.symbol}`}
                        className="font-mono text-emerald-400 hover:text-emerald-300 transition"
                      >
                        {instrument.symbol}
                      </Link>
                    </td>
                    <td className="py-3 px-4 text-gray-300 truncate max-w-xs">
                      {instrument.name}
                    </td>
                    <td className="py-3 px-4">
                      <span className={`inline-block px-2 py-1 rounded text-[11px] font-medium ${getTypeBadgeColor(instrument.type)}`}>
                        {instrument.type}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-gray-500">
                      {instrument.sector || '—'}
                    </td>
                    <td className="py-3 px-4 text-gray-500">
                      {instrument.exchange || '—'}
                    </td>
                    <td className="py-3 px-4 text-right font-mono text-gray-400">
                      {formatMcap(instrument.market_cap_b)}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between text-xs text-gray-400 px-2">
          <span>
            Page {page + 1} of {totalPages} • {total.toLocaleString()} results
          </span>
          <div className="flex gap-2">
            <button
              onClick={() => setPage(0)}
              disabled={page === 0}
              className="px-3 py-2 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 rounded-lg disabled:opacity-30 disabled:cursor-not-allowed hover:bg-emerald-500/20 transition"
            >
              First
            </button>
            <button
              onClick={() => setPage(p => Math.max(0, p - 1))}
              disabled={page === 0}
              className="px-3 py-2 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 rounded-lg disabled:opacity-30 disabled:cursor-not-allowed hover:bg-emerald-500/20 transition"
            >
              Prev
            </button>
            <button
              onClick={() => setPage(p => Math.min(totalPages - 1, p + 1))}
              disabled={page >= totalPages - 1}
              className="px-3 py-2 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 rounded-lg disabled:opacity-30 disabled:cursor-not-allowed hover:bg-emerald-500/20 transition"
            >
              Next
            </button>
            <button
              onClick={() => setPage(totalPages - 1)}
              disabled={page >= totalPages - 1}
              className="px-3 py-2 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 rounded-lg disabled:opacity-30 disabled:cursor-not-allowed hover:bg-emerald-500/20 transition"
            >
              Last
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
