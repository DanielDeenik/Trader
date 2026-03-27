import { createContext, useContext, useState, useCallback, useEffect } from 'react'
import { api } from '../api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [token, setToken] = useState(null)
  const [loading, setLoading] = useState(true)

  // Initialize auth state from session (check if token is still valid)
  useEffect(() => {
    const checkAuth = async () => {
      // Try to get current user if we have a token
      try {
        const userData = await api.getMe()
        setUser(userData)
      } catch (err) {
        // No valid auth
        setUser(null)
        setToken(null)
      } finally {
        setLoading(false)
      }
    }

    if (token) {
      checkAuth()
    } else {
      setLoading(false)
    }
  }, [token])

  const login = useCallback(async (email, password) => {
    const response = await api.login(email, password)
    setToken(response.token)
    setUser(response.user)
    return response
  }, [])

  const register = useCallback(async (email, password, displayName) => {
    const response = await api.register(email, password, displayName)
    setToken(response.token)
    setUser(response.user)
    return response
  }, [])

  const logout = useCallback(() => {
    setToken(null)
    setUser(null)
  }, [])

  const value = {
    user,
    token,
    loading,
    isAuthenticated: !!user,
    login,
    register,
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
