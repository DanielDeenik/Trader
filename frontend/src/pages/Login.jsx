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
    if (!clientId || !window.google?.accounts?.id) return

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

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-900">
      <div className="bg-gray-800 border border-gray-700 rounded-lg p-8 w-full max-w-md">
        <h1 className="text-2xl font-bold text-emerald-400 text-center tracking-widest mb-1">
          SOCIAL ARB
        </h1>
        <p className="text-gray-400 text-center text-sm mb-8">
          Information Arbitrage Platform
        </p>

        {error && (
          <div className="bg-red-900/30 border border-red-700 text-red-300 text-sm rounded p-3 mb-4">
            {error}
          </div>
        )}

        {/* Google Sign-In Button */}
        <div id="google-signin-btn" className="mb-6 flex justify-center"></div>

        {window.__GOOGLE_CLIENT_ID__ && (
          <div className="relative mb-6">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-gray-600"></div>
            </div>
            <div className="relative flex justify-center text-sm">
              <span className="px-2 bg-gray-800 text-gray-500">or</span>
            </div>
          </div>
        )}

        {/* Email/Password Login */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm text-gray-300 mb-1">Email</label>
            <input
              type="email"
              value={email}
              onChange={e => setEmail(e.target.value)}
              placeholder="you@example.com"
              className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-gray-100 placeholder-gray-500 focus:outline-none focus:border-emerald-500"
              required
            />
          </div>
          <div>
            <label className="block text-sm text-gray-300 mb-1">Password</label>
            <input
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              placeholder="••••••••"
              className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-gray-100 placeholder-gray-500 focus:outline-none focus:border-emerald-500"
              required
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="w-full bg-emerald-600 hover:bg-emerald-500 text-white font-medium py-2 rounded transition disabled:opacity-50"
          >
            {loading ? 'Signing in...' : 'Sign In'}
          </button>
        </form>

        <div className="mt-6 border-t border-gray-700 pt-4 text-center">
          <p className="text-gray-500 text-xs">
            Don't have an account?{' '}
            <button
              onClick={() => setError('Register via Google Sign-In or ask admin')}
              className="text-emerald-400 hover:underline"
            >
              Create one here
            </button>
          </p>
        </div>
      </div>
    </div>
  )
}
