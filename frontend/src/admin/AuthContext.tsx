// Provider and hook intentionally share one module as a single authentication boundary.
// oxlint-disable react/only-export-components
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import { loginRequest, logoutRequest, refreshRequest } from './api'
import type { AdminIdentity, TokenResponse } from './types'

const REFRESH_STORAGE_KEY = 'cipherscore.admin.refresh'

type AuthContextValue = {
  admin: AdminIdentity | null
  accessToken: string | null
  initializing: boolean
  login: (email: string, password: string) => Promise<void>
  logout: () => Promise<void>
  hasPermission: (permission?: string) => boolean
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [admin, setAdmin] = useState<AdminIdentity | null>(null)
  const [accessToken, setAccessToken] = useState<string | null>(null)
  const [initializing, setInitializing] = useState(true)

  const applySession = useCallback((session: TokenResponse) => {
    setAdmin(session.admin)
    setAccessToken(session.access_token)
    sessionStorage.setItem(REFRESH_STORAGE_KEY, session.refresh_token)
  }, [])

  const clearSession = useCallback(() => {
    setAdmin(null)
    setAccessToken(null)
    sessionStorage.removeItem(REFRESH_STORAGE_KEY)
  }, [])

  useEffect(() => {
    const refreshToken = sessionStorage.getItem(REFRESH_STORAGE_KEY)
    if (!refreshToken) {
      setInitializing(false)
      return
    }
    refreshRequest(refreshToken).then(applySession).catch(clearSession).finally(() => setInitializing(false))
  }, [applySession, clearSession])

  const login = useCallback(async (email: string, password: string) => {
    applySession(await loginRequest(email, password))
  }, [applySession])

  const logout = useCallback(async () => {
    const refreshToken = sessionStorage.getItem(REFRESH_STORAGE_KEY)
    try {
      if (accessToken && refreshToken) await logoutRequest(accessToken, refreshToken)
    } finally {
      clearSession()
    }
  }, [accessToken, clearSession])

  const value = useMemo<AuthContextValue>(() => ({
    admin,
    accessToken,
    initializing,
    login,
    logout,
    hasPermission: (permission) => !permission || Boolean(admin?.permissions.includes(permission)),
  }), [accessToken, admin, initializing, login, logout])

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth must be used inside AuthProvider')
  return context
}
