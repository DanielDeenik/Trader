import { useState, useEffect } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { api } from '../api'

export default function Settings() {
  const { user } = useAuth()
  const [displayName, setDisplayName] = useState('')
  const [defaultPortfolio, setDefaultPortfolio] = useState('100000')
  const [alertThreshold, setAlertThreshold] = useState('5')
  const [watchlist, setWatchlist] = useState([])
  const [newSymbol, setNewSymbol] = useState('')
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    const loadSettings = async () => {
      try {
        if (user) {
          setDisplayName(user.display_name || user.displayName || '')
          const wl = await api.getWatchlist()
          setWatchlist(wl || [])
        }
      } catch (err) {
        console.error('Failed to load settings:', err)
      } finally {
        setLoading(false)
      }
    }
    loadSettings()
  }, [user])

  const handleUpdateSettings = async (e) => {
    e.preventDefault()
    setError('')
    setSuccess('')
    setSaving(true)

    try {
      await api.updateSettings({
        display_name: displayName,
        settings_json: {
          default_portfolio_value: defaultPortfolio,
          alert_threshold: alertThreshold,
        },
      })
      setSuccess('Settings updated successfully')
      setTimeout(() => setSuccess(''), 5000)
    } catch (err) {
      setError(err.message || 'Failed to update settings')
    } finally {
      setSaving(false)
    }
  }

  const handleAddToWatchlist = async (e) => {
    e.preventDefault()
    if (!newSymbol.trim()) return

    setError('')
    try {
      await api.addToWatchlist(newSymbol.toUpperCase())
      setNewSymbol('')
      const wl = await api.getWatchlist()
      setWatchlist(wl || [])
      setSuccess(`Added ${newSymbol.toUpperCase()} to watchlist`)
      setTimeout(() => setSuccess(''), 5000)
    } catch (err) {
      setError(err.message || 'Failed to add to watchlist')
    }
  }

  const handleRemoveFromWatchlist = async (symbol) => {
    setError('')
    try {
      await api.removeFromWatchlist(symbol)
      setWatchlist(watchlist.filter((item) => item.symbol !== symbol))
      setSuccess(`Removed ${symbol} from watchlist`)
      setTimeout(() => setSuccess(''), 5000)
    } catch (err) {
      setError(err.message || 'Failed to remove from watchlist')
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="flex items-center gap-2 text-gray-400">
          <div className="w-4 h-4 border-2 border-emerald-400/30 border-t-emerald-400 rounded-full animate-spin" />
          <span className="text-sm">Loading settings...</span>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-4 max-w-4xl">
      {/* Alert messages */}
      {error && (
        <div className="bg-red-500/10 border border-red-500/20 rounded-xl px-4 py-3 text-xs text-red-400 flex items-start gap-2">
          <span className="mt-0.5">!</span>
          <span>{error}</span>
        </div>
      )}
      {success && (
        <div className="bg-emerald-500/10 border border-emerald-500/20 rounded-xl px-4 py-3 text-xs text-emerald-400 flex items-start gap-2">
          <span className="mt-0.5">✓</span>
          <span>{success}</span>
        </div>
      )}

      {/* User Profile */}
      <div className="bg-[#111827]/80 border border-white/[0.06] rounded-xl p-6">
        <h2 className="text-sm font-bold text-white mb-4">User Profile</h2>
        <div className="space-y-3">
          <div>
            <label className="text-xs text-gray-400 uppercase tracking-wider block mb-1">Email</label>
            <input
              type="email"
              value={user?.email || ''}
              disabled
              className="w-full bg-white/[0.02] border border-white/[0.06] rounded-lg px-3 py-2 text-xs text-gray-500 font-mono cursor-not-allowed"
            />
          </div>
          <div className="text-xs text-gray-500 pt-2">
            Member since {user?.created_at ? new Date(user.created_at).toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' }) : 'N/A'}
          </div>
        </div>
      </div>

      {/* Settings Form */}
      <form onSubmit={handleUpdateSettings} className="bg-[#111827]/80 border border-white/[0.06] rounded-xl p-6 space-y-4">
        <h2 className="text-sm font-bold text-white">Preferences</h2>

        <div>
          <label className="text-xs text-gray-400 uppercase tracking-wider block mb-2">Display Name</label>
          <input
            type="text"
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            placeholder="Your display name"
            className="w-full bg-white/[0.04] border border-white/[0.08] rounded-lg px-3 py-2 text-[13px] text-white placeholder-gray-500 focus:outline-none focus:border-emerald-500/50 focus:ring-1 focus:ring-emerald-500/20 transition"
          />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="text-xs text-gray-400 uppercase tracking-wider block mb-2">Default Portfolio Value ($)</label>
            <input
              type="number"
              value={defaultPortfolio}
              onChange={(e) => setDefaultPortfolio(e.target.value)}
              className="w-full bg-white/[0.04] border border-white/[0.08] rounded-lg px-3 py-2 text-[13px] text-white placeholder-gray-500 font-mono focus:outline-none focus:border-emerald-500/50 focus:ring-1 focus:ring-emerald-500/20 transition"
            />
          </div>

          <div>
            <label className="text-xs text-gray-400 uppercase tracking-wider block mb-2">Alert Threshold (%)</label>
            <input
              type="number"
              value={alertThreshold}
              onChange={(e) => setAlertThreshold(e.target.value)}
              step="0.5"
              className="w-full bg-white/[0.04] border border-white/[0.08] rounded-lg px-3 py-2 text-[13px] text-white placeholder-gray-500 font-mono focus:outline-none focus:border-emerald-500/50 focus:ring-1 focus:ring-emerald-500/20 transition"
            />
          </div>
        </div>

        <button
          type="submit"
          disabled={saving}
          className="w-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 px-4 py-2.5 rounded-lg text-xs font-medium hover:bg-emerald-500/20 disabled:opacity-50 disabled:cursor-not-allowed transition"
        >
          {saving ? (
            <span className="flex items-center justify-center gap-2">
              <div className="w-3 h-3 border-2 border-emerald-400/30 border-t-emerald-400 rounded-full animate-spin" />
              Saving...
            </span>
          ) : (
            'Save Settings'
          )}
        </button>
      </form>

      {/* Watchlist */}
      <div className="bg-[#111827]/80 border border-white/[0.06] rounded-xl p-6 space-y-4">
        <h2 className="text-sm font-bold text-white">Watchlist</h2>

        <form onSubmit={handleAddToWatchlist} className="flex gap-2">
          <input
            type="text"
            value={newSymbol}
            onChange={(e) => setNewSymbol(e.target.value)}
            placeholder="Add symbol (e.g., AAPL)"
            maxLength="10"
            className="flex-1 bg-white/[0.04] border border-white/[0.08] rounded-lg px-3 py-2 text-[13px] text-white placeholder-gray-500 font-mono focus:outline-none focus:border-emerald-500/50 focus:ring-1 focus:ring-emerald-500/20 transition"
          />
          <button
            type="submit"
            disabled={!newSymbol.trim()}
            className="px-4 py-2 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-medium rounded-lg hover:bg-emerald-500/20 disabled:opacity-30 disabled:cursor-not-allowed transition"
          >
            Add
          </button>
        </form>

        {watchlist.length === 0 ? (
          <div className="py-8 text-center text-gray-500 text-xs">
            No symbols in watchlist yet
          </div>
        ) : (
          <div className="space-y-2">
            {watchlist.map((item) => (
              <div
                key={item.symbol}
                className="flex items-center justify-between bg-white/[0.02] border border-white/[0.06] rounded-lg px-3 py-2.5 hover:bg-white/[0.04] transition"
              >
                <div>
                  <p className="text-white font-mono text-sm font-bold">{item.symbol}</p>
                  <p className="text-xs text-gray-500 mt-0.5">
                    Added {new Date(item.added_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
                  </p>
                </div>
                <button
                  onClick={() => handleRemoveFromWatchlist(item.symbol)}
                  className="px-3 py-1 text-xs text-red-400/70 hover:text-red-400 hover:bg-red-500/10 rounded transition border border-red-500/0 hover:border-red-500/20"
                >
                  Remove
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
