import { createContext, useContext, useState, useEffect } from 'react'
import { API_BASE } from '../config/api'

const AuthContext = createContext(null)
const TOKEN_KEY = 'amlkr_token'

function decodeJwtPayload(token) {
  try {
    const base64 = token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/')
    return JSON.parse(atob(base64))
  } catch {
    return null
  }
}

export function AuthProvider({ children }) {
  const [user, setUser]       = useState(null)
  const [token, setToken]     = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const stored = localStorage.getItem(TOKEN_KEY)
    if (stored) {
      const payload = decodeJwtPayload(stored)
      if (payload && payload.exp * 1000 > Date.now()) {
        setToken(stored)
        setUser({ id: payload.sub, email: payload.email, role: payload.role })
      } else {
        localStorage.removeItem(TOKEN_KEY)
      }
    }
    setLoading(false)
  }, [])

  const login = async (email, password) => {
    const res = await fetch(`${API_BASE}/api/auth/login`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ email, password }),
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.detail ?? 'Credenciales incorrectas')
    }
    const data = await res.json()
    localStorage.setItem(TOKEN_KEY, data.token)
    setToken(data.token)
    setUser(data.user)
    return data.user
  }

  const loginWithGoogle = async (idToken) => {
    const res = await fetch(`${API_BASE}/api/auth/google`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id_token: idToken }),
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.detail ?? 'Google login failed')
    }
    const data = await res.json()
    localStorage.setItem(TOKEN_KEY, data.token)
    setToken(data.token)
    setUser(data.user)
    return data.user
  }

  const register = async (name, email, password) => {
    const res = await fetch(`${API_BASE}/api/auth/register`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ name, email, password }),
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.detail ?? 'Error al crear la cuenta')
    }
    const data = await res.json()
    localStorage.setItem(TOKEN_KEY, data.token)
    setToken(data.token)
    setUser(data.user)
    return data.user
  }

  const logout = () => {
    localStorage.removeItem(TOKEN_KEY)
    setToken(null)
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, token, loading, login, loginWithGoogle, register, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
