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

  // Initialize Google Sign-In (dynamically load GSI script only if valid client ID)
  useEffect(() => {
    const clientId = window.__GOOGLE_CLIENT_ID__
    if (!clientId || clientId.includes('REPLACE')) return

    function initGsi() {
      if (!window.google?.accounts?.id) return
      window.google.accounts.id.initialize({
        client_id: clientId,
        callback: handleGoogleCallback,
      })
      const btn = document.getElementById('google-signin-btn')
      if (btn) {
        window.google.accounts.id.renderButton(btn, {
          theme: 'filled_blue',
          size: 'large',
          width: 360,
          text: 'signin_with',
        })
      }
    }

    // If GSI already loaded, init immediately
    if (window.google?.accounts?.id) {
      initGsi()
      return
    }

    // Otherwise load the script dynamically
    const script = document.createElement('script')
    script.src = 'https://accounts.google.com/gsi/client'
    script.async = true
    script.onload = initGsi
    script.onerror = () => console.warn('Google Sign-In script failed to load')
    document.head.appendChild(script)
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
    <div className="min-h-screen bg-[#0a0f1a] flex items-center justify-center relative overflow-hidden">
      {/* Subtle background grid pattern */}
      <div
        className="absolute inset-0 opacity-5"
        style={{
          backgroundImage: 'linear-gradient(rgba(16,185,129,0.3) 1px, transparent 1px), linear-gradient(90deg, rgba(16,185,129,0.3) 1px, transparent 1px)',
          backgroundSize: '40px 40px',
        }}
      />

      <div className="relative z-10 w-full max-w-md mx-4">
        {/* Logo + Branding */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 mb-4">
            <svg width="32" height="32" viewBox="0 0 32 32" fill="none">
              <path d="M16 3L28 9V23L16 29L4 23V9L16 3Z" stroke="#10b981" strokeWidth="2" fill="none" />
              <path d="M16 3V29M4 9L28 23M28 9L4 23" stroke="#10b981" strokeWidth="1" opacity="0.4" />
              <circle cx="16" cy="16" r="4" fill="#10b981" opacity="0.6" />
            </svg>
          </div>
          <h1 className="text-3xl font-bold text-white tracking-tight">
            Social Arb
          </h1>
          <p className="text-gray-400 text-xs mt-2">
            Information Arbitrage Platform
          </p>
        </div>

        {/* Card */}
        <div className="bg-[#111827]/80 backdrop-blur border border-white/[0.06] rounded-xl p-8 shadow-2xl shadow-black/20">
          {error && (
            <div className="bg-red-500/10 border border-red-500/20 text-red-400 text-xs rounded-lg p-3 mb-5 flex items-start gap-2">
              <span className="mt-0.5 shrink-0 font-bold">!</span>
              <span>{error}</span>
            </div>
          )}

          {/* Google Sign-In Button */}
          {hasGoogleClientId && (
            <>
              <div id="google-signin-btn" className="mb-5 flex justify-center" />
              <div className="relative mb-5">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-white/[0.06]" />
                </div>
                <div className="relative flex justify-center text-xs">
                  <span className="px-3 bg-[#111827] text-gray-400">or sign in with email</span>
                </div>
              </div>
            </>
          )}

          {/* Email/Password Login */}
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-gray-400 mb-1.5 uppercase tracking-wider">
                Email
              </label>
              <input
                type="email"
                value={email}
                onChange={e => setEmail(e.target.value)}
                placeholder="you@example.com"
                autoComplete="email"
                className="w-full bg-white/[0.04] border border-white/[0.08] rounded-lg px-4 py-2.5 text-gray-100 placeholder-gray-500 focus:outline-none focus:border-emerald-500/50 focus:ring-1 focus:ring-emerald-500/20 transition text-[13px]"
                required
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-400 mb-1.5 uppercase tracking-wider">
                Password
              </label>
              <input
                type="password"
                value={password}
                onChange={e => setPassword(e.target.value)}
                placeholder="Enter your password"
                autoComplete="current-password"
                className="w-full bg-white/[0.04] border border-white/[0.08] rounded-lg px-4 py-2.5 text-gray-100 placeholder-gray-500 focus:outline-none focus:border-emerald-500/50 focus:ring-1 focus:ring-emerald-500/20 transition text-[13px]"
                required
              />
            </div>
            <button
              type="submit"
              disabled={loading}
              className="w-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 font-medium py-2.5 rounded-lg hover:bg-emerald-500/20 active:bg-emerald-500/30 transition-all duration-150 disabled:opacity-50 disabled:cursor-not-allowed text-sm"
            >
              {loading ? (
                <span className="flex items-center justify-center gap-2">
                  <span className="w-4 h-4 border-2 border-emerald-400/30 border-t-emerald-400 rounded-full animate-spin" />
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
