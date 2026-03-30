import { createContext, useContext, useState, useCallback, useEffect } from 'react'

const API_BASE = '/api/v1'
const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [token, setToken] = useState(null)
  const [loading, setLoading] = useState(true)

  // Restore session from sessionStorage on mount
  useEffect(() => {
    const savedToken = sessionStorage.getItem('sa_token')
    const savedUser = sessionStorage.getItem('sa_user')
    if (savedToken && savedUser) {
      setToken(savedToken)
      setUser(JSON.parse(savedUser))
    }
    setLoading(false)
  }, [])

  // Persist session
  function saveSession(tok, usr) {
    setToken(tok)
    setUser(usr)
    sessionStorage.setItem('sa_token', tok)
    sessionStorage.setItem('sa_user', JSON.stringify(usr))
  }

  const login = useCallback(async (email, password) => {
    const res = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    })
    const data = await res.json()
    if (!res.ok) throw new Error(data.detail || 'Login failed')
    saveSession(data.token, data.user)
    return data
  }, [])

  const loginWithGoogle = useCallback(async (credential) => {
    const res = await fetch(`${API_BASE}/auth/google`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ credential }),
    })
    const data = await res.json()
    if (!res.ok) throw new Error(data.detail || 'Google login failed')
    saveSession(data.token, data.user)
    return data
  }, [])

  const logout = useCallback(() => {
    setToken(null)
    setUser(null)
    sessionStorage.removeItem('sa_token')
    sessionStorage.removeItem('sa_user')
  }, [])

  const value = {
    user,
    token,
    loading,
    isAuthenticated: !!user,
    login,
    loginWithGoogle,
    logout,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider')
  }
  return context
}
