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

  useEffect(() => {
    const loadSettings = async () => {
      try {
        if (user) {
          setDisplayName(user.display_name || user.displayName || '')
          const wl = await api.getWatchlist()
          setWatchlist(wl || [])
        }
      } catch (err) {
        setError('Failed to load settings')
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

    try {
      await api.updateSettings({
        display_name: displayName,
        settings_json: {
          default_portfolio_value: defaultPortfolio,
          alert_threshold: alertThreshold,
        },
      })
      setSuccess('Settings updated successfully')
    } catch (err) {
      setError(err.message || 'Failed to update settings')
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
      setSuccess(`Added ${newSymbol} to watchlist`)
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
    } catch (err) {
      setError(err.message || 'Failed to remove from watchlist')
    }
  }

  if (loading) {
    return (
      <div className="p-4 text-gray-400">
        <p>Loading settings...</p>
      </div>
    )
  }

  return (
    <div className="max-w-2xl space-y-6">
      {/* User Info */}
      <div className="bg-gray-800 border border-gray-700 rounded-lg p-6">
        <h2 className="text-lg font-bold text-white mb-4">User Profile</h2>
        <div className="space-y-2 text-sm text-gray-400">
          <p>
            <span className="text-gray-500">Email:</span> {user?.email}
          </p>
          <p>
            <span className="text-gray-500">Member since:</span> {user?.created_at ? new Date(user.created_at).toLocaleDateString() : 'N/A'}
          </p>
        </div>
      </div>

      {/* Settings Form */}
      <form onSubmit={handleUpdateSettings} className="bg-gray-800 border border-gray-700 rounded-lg p-6">
        <h2 className="text-lg font-bold text-white mb-4">Settings</h2>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Display Name
            </label>
            <input
              type="text"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-emerald-400"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Default Portfolio Value ($)
            </label>
            <input
              type="number"
              value={defaultPortfolio}
              onChange={(e) => setDefaultPortfolio(e.target.value)}
              className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-emerald-400"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Alert Threshold (%)
            </label>
            <input
              type="number"
              value={alertThreshold}
              onChange={(e) => setAlertThreshold(e.target.value)}
              className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-emerald-400"
            />
          </div>

          {error && (
            <div className="bg-red-900/30 border border-red-700 rounded px-3 py-2 text-xs text-red-300">
              {error}
            </div>
          )}

          {success && (
            <div className="bg-green-900/30 border border-green-700 rounded px-3 py-2 text-xs text-green-300">
              {success}
            </div>
          )}

          <button
            type="submit"
            className="bg-emerald-600 hover:bg-emerald-700 text-white font-medium py-2 px-4 rounded text-sm transition-colors"
          >
            Save Settings
          </button>
        </div>
      </form>

      {/* Watchlist */}
      <div className="bg-gray-800 border border-gray-700 rounded-lg p-6">
        <h2 className="text-lg font-bold text-white mb-4">Watchlist</h2>

        <form onSubmit={handleAddToWatchlist} className="mb-4 flex gap-2">
          <input
            type="text"
            value={newSymbol}
            onChange={(e) => setNewSymbol(e.target.value)}
            placeholder="Add symbol (e.g., AAPL)"
            className="flex-1 bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-emerald-400"
          />
          <button
            type="submit"
            className="bg-emerald-600 hover:bg-emerald-700 text-white font-medium py-2 px-4 rounded text-sm transition-colors"
          >
            Add
          </button>
        </form>

        {watchlist.length === 0 ? (
          <p className="text-sm text-gray-400">No symbols in watchlist yet</p>
        ) : (
          <div className="space-y-2">
            {watchlist.map((item) => (
              <div
                key={item.symbol}
                className="flex items-center justify-between bg-gray-700 border border-gray-600 rounded px-3 py-2"
              >
                <div>
                  <p className="text-white font-medium text-sm">{item.symbol}</p>
                  <p className="text-xs text-gray-400">
                    Added {new Date(item.added_at).toLocaleDateString()}
                  </p>
                </div>
                <button
                  onClick={() => handleRemoveFromWatchlist(item.symbol)}
                  className="text-red-400 hover:text-red-300 text-sm transition-colors"
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
