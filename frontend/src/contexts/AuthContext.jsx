import { createContext, useContext, useState, useCallback, useEffect } from 'react'
import { api } from '../api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  // Auth bypassed for solo/local use — all routes accessible without login
  const [user, setUser] = useState({ email: 'dan@socialarb.local', displayName: 'Dan' })
  const [token, setToken] = useState('local')
  const [loading, setLoading] = useState(false)

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
