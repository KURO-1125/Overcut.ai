import React, { createContext, useContext, useState, useEffect, useCallback } from 'react'
import { apiFetch, ApiError } from '../lib/api'

const AuthContext = createContext(null)
const TOKEN_KEY  = 'OVERCUT_JWT'
const SESSION_KEY = 'OVERCUT_USER_SESSION'

// ── Demo profiles (used when backend is offline) ──────────────────
export const DEMO_USERS = [
  {
    id: 'user_1',
    name: 'Alex Vance',
    email: 'alex.vance@scuderia.f1',
    role: 'Chief Race Engineer',
    team: 'Scuderia Ferrari HP',
    avatar: 'AV',
    accentColor: '#E80020',
    isDemo: true,
  },
  {
    id: 'user_2',
    name: 'Maya Lin',
    email: 'maya.lin@redbullracing.com',
    role: 'Principal Telemetry Architect',
    team: 'Oracle Red Bull Racing',
    avatar: 'ML',
    accentColor: '#3671C6',
    isDemo: true,
  },
  {
    id: 'user_3',
    name: 'Elena Rostova',
    email: 'elena.rostova@overcut.ev',
    role: 'Senior BMS Battery Specialist',
    team: 'NASA Ames / EV Fleet',
    avatar: 'ER',
    accentColor: '#10B981',
    isDemo: true,
  },
]

// ── Normalize API response → internal user shape ─────────────────
function normalizeApiUser(apiUser, token) {
  return {
    id:          apiUser.user_id,
    name:        apiUser.name,
    email:       apiUser.email,
    role:        apiUser.role,
    team:        apiUser.team,
    avatar:      apiUser.avatar,
    accentColor: apiUser.accent_color || '#00D4FF',
    token,
    isDemo:      false,
  }
}

export function AuthProvider({ children }) {
  // Restore session from localStorage
  const [user, setUser] = useState(() => {
    try {
      const saved = localStorage.getItem(SESSION_KEY)
      if (saved === 'null') return null       // explicit logout
      if (saved) return JSON.parse(saved)
    } catch { /* corrupted */ }
    return null                              // no implicit demo session
  })

  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false)
  const [authMode, setAuthMode] = useState('login')
  const [authError, setAuthError] = useState('')
  const [authLoading, setAuthLoading] = useState(false)

  // Persist session on every user change
  useEffect(() => {
    try {
      if (user) {
        localStorage.setItem(SESSION_KEY, JSON.stringify(user))
        if (user.token) localStorage.setItem(TOKEN_KEY, user.token)
      } else {
        localStorage.setItem(SESSION_KEY, 'null')
        localStorage.removeItem(TOKEN_KEY)
      }
    } catch { /* ignore */ }
  }, [user])

  // Silently re-validate JWT on mount (verify token is still accepted)
  useEffect(() => {
    const token = localStorage.getItem(TOKEN_KEY)
    if (!token || user?.isDemo) return

    let cancelled = false
    apiFetch('/api/auth/me', {
      headers: { Authorization: `Bearer ${token}` },
      timeoutMs: 5000,
    })
      .then(r => r.json())
      .then(data => {
        if (!cancelled && data) {
          setUser(normalizeApiUser(data, token))
        }
      })
      .catch((err) => {
        if (!cancelled && err instanceof ApiError && err.status === 401) {
          setUser(null)
        }
      })

    return () => { cancelled = true }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  // ── Real login ──────────────────────────────────────────────────
  const login = useCallback(async (email, password) => {
    setAuthLoading(true)
    setAuthError('')
    try {
      const res = await apiFetch('/api/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email, password }),
        timeoutMs: 10000,
      })
      const data = await res.json()

      const u = normalizeApiUser(data, data.token)
      setUser(u)
      setIsAuthModalOpen(false)
      return { success: true, user: u }
    } catch (err) {
      // Only fall back to a demo profile when the API is unreachable; a 401
      // must stay a failed login instead of silently granting access.
      if (!(err instanceof ApiError)) {
        const demo = DEMO_USERS.find(d => d.email.toLowerCase() === email.toLowerCase())
        if (demo) {
          setUser(demo)
          setIsAuthModalOpen(false)
          return { success: true, user: demo }
        }
      }
      const msg = err.name === 'TimeoutError' ? 'Backend offline — only demo accounts available.' : err.message
      setAuthError(msg)
      return { success: false, error: msg }
    } finally {
      setAuthLoading(false)
    }
  }, [])

  // ── Real signup ─────────────────────────────────────────────────
  const signup = useCallback(async ({ name, email, password, role, team }) => {
    setAuthLoading(true)
    setAuthError('')
    try {
      const res = await apiFetch('/api/auth/register', {
        method: 'POST',
        body: JSON.stringify({ name, email, password, role, team }),
        timeoutMs: 10000,
      })
      const data = await res.json()

      const u = normalizeApiUser(data, data.token)
      setUser(u)
      setIsAuthModalOpen(false)
      return { success: true, user: u }
    } catch (err) {
      const msg = err.name === 'TimeoutError' ? 'Backend offline — cannot create account right now.' : err.message
      setAuthError(msg)
      return { success: false, error: msg }
    } finally {
      setAuthLoading(false)
    }
  }, [])

  // ── Demo login (1-click) ────────────────────────────────────────
  const loginWithDemo = useCallback((demoUser) => {
    setUser(demoUser)
    setIsAuthModalOpen(false)
  }, [])

  // ── Logout ──────────────────────────────────────────────────────
  const logout = useCallback(() => {
    setUser(null)
  }, [])

  const openAuth = useCallback((mode = 'login') => {
    setAuthMode(mode)
    setAuthError('')
    setIsAuthModalOpen(true)
  }, [])

  const closeAuth = useCallback(() => {
    setIsAuthModalOpen(false)
    setAuthError('')
  }, [])

  return (
    <AuthContext.Provider value={{
      user,
      isAuthenticated: !!user,
      login,
      signup,
      loginWithDemo,
      logout,
      isAuthModalOpen,
      authMode,
      authError,
      authLoading,
      openAuth,
      closeAuth,
      setAuthMode,
    }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
