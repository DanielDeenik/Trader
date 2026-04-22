import { useState, useEffect } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { useNavigate } from 'react-router-dom'

export default function Login() {
  const { login, loginWithGoogle, isAuthenticated } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (isAuthenticated) {
      navigate('/', { replace: true })
    }
  }, [isAuthenticated, navigate])

  // Initialize Google Sign-In
  useEffect(() => {
    const clientId = window.__GOOGLE_CLIENT_ID__
    if (!clientId || clientId.includes('REPLACE') || !window.google?.accounts?.id) return

    window.google.accounts.id.initialize({
      client_id: clientId,
      callback: handleGoogleCallback,
    })
    window.google.accounts.id.renderButton(
      document.getElementById('google-signin-btn'),
      { theme: 'filled_blue', size: 'large', width: 360, text: 'signin_with' }
    )
  }, [])

  async function handleGoogleCallback(response) {
    setError('')
    setLoading(true)
    try {
      await loginWithGoogle(response.credential)
      navigate('/', { replace: true })
    } catch (err) {
      setError(err.message || 'Google sign-in failed')
    } finally {
      setLoading(false)
    }
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await login(email, password)
      navigate('/', { replace: true })
    } catch (err) {
      setError(err.message || 'Invalid credentials')
    } finally {
      setLoading(false)
    }
  }

  const hasGoogleClientId = window.__GOOGLE_CLIENT_ID__ && !window.__GOOGLE_CLIENT_ID__.includes('REPLACE')

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-900 relative overflow-hidden">
      {/* Subtle background grid pattern */}
      <div className="absolute inset-0 opacity-5" style={{
        backgroundImage: 'linear-gradient(rgba(16,185,129,0.3) 1px, transparent 1px), linear-gradient(90deg, rgba(16,185,129,0.3) 1px, transparent 1px)',
        backgroundSize: '40px 40px'
      }} />

      <div className="relative z-10 w-full max-w-md mx-4">
        {/* Logo + Branding */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 mb-4">
            <svg width="32" height="32" viewBox="0 0 32 32" fill="none">
              <path d="M16 3L28 9V23L16 29L4 23V9L16 3Z" stroke="#10b981" strokeWidth="2" fill="none"/>
              <path d="M16 3V29M4 9L28 23M28 9L4 23" stroke="#10b981" strokeWidth="1" opacity="0.4"/>
              <circle cx="16" cy="16" r="4" fill="#10b981" opacity="0.6"/>
            </svg>
          </div>
          <h1 className="text-3xl font-bold text-white tracking-tight">
            Social Arb
          </h1>
          <p className="text-gray-500 text-sm mt-1">
            Information Arbitrage Platform
          </p>
        </div>

        {/* Card */}
        <div className="bg-gray-800/80 backdrop-blur border border-gray-700/50 rounded-xl p-8 shadow-2xl shadow-black/20">
          {error && (
            <div className="bg-red-900/20 border border-red-800/50 text-red-400 text-sm rounded-lg p-3 mb-5 flex items-start gap-2">
              <span className="mt-0.5 shrink-0">!</span>
              <span>{error}</span>
            </div>
          )}

          {/* Google Sign-In Button */}
          {hasGoogleClientId && (
            <>
              <div id="google-signin-btn" className="mb-5 flex justify-center" />
              <div className="relative mb-5">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-gray-700" />
                </div>
                <div className="relative flex justify-center text-xs">
                  <span className="px-3 bg-gray-800 text-gray-500">or sign in with email</span>
                </div>
              </div>
            </>
          )}

          {/* Email/Password Login */}
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-gray-400 mb-1.5 uppercase tracking-wider">Email</label>
              <input
                type="email"
                value={email}
                onChange={e => setEmail(e.target.value)}
                placeholder="you@example.com"
                autoComplete="email"
                className="w-full bg-gray-900/50 border border-gray-600/50 rounded-lg px-4 py-2.5 text-gray-100 placeholder-gray-600 focus:outline-none focus:border-emerald-500/50 focus:ring-1 focus:ring-emerald-500/20 transition"
                required
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-400 mb-1.5 uppercase tracking-wider">Password</label>
              <input
                type="password"
                value={password}
                onChange={e => setPassword(e.target.value)}
                placeholder="Enter your password"
                autoComplete="current-password"
                className="w-full bg-gray-900/50 border border-gray-600/50 rounded-lg px-4 py-2.5 text-gray-100 placeholder-gray-600 focus:outline-none focus:border-emerald-500/50 focus:ring-1 focus:ring-emerald-500/20 transition"
                required
              />
            </div>
            <button
              type="submit"
              disabled={loading}
              className="w-full bg-emerald-600 hover:bg-emerald-500 active:bg-emerald-700 text-white font-medium py-2.5 rounded-lg transition-all duration-150 disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-emerald-900/30"
            >
              {loading ? (
                <span className="flex items-center justify-center gap-2">
                  <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  Signing in...
                </span>
              ) : (
                'Sign In'
              )}
            </button>
          </form>
        </div>

        {/* Footer */}
        <p className="text-center text-gray-600 text-xs mt-6">
          Mosaic Theory + Information Arbitrage
        </p>
      </div>
    </div>
  )
}
