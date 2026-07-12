import { createContext, useContext, useState } from 'react'
import { env } from '../config/env'

const SessionContext = createContext(null)

export function SessionProvider({ children }) {
  // Soft-gating: during this transitional phase auth is off by default so the
  // workspaces stay usable. Set VITE_SKIP_AUTH=false in .env to enforce gating
  // (redirect unauthenticated users to /login).
  const [user_id, setUserId] = useState(null)
  const [authToken, setAuthToken] = useState(null)
  const [isAuthenticated, setIsAuthenticated] = useState(env.SKIP_AUTH ? true : false)

  const login = (payload) => {
    // TODO: POST /api/v1/auth/login (not implemented yet — Guide 2 Step 5)
    console.log('[auth] login stub', payload)
    setUserId(payload?.user_id ?? 'dev-user')
    setAuthToken(payload?.token ?? null)
    setIsAuthenticated(true)
  }

  const logout = () => {
    setUserId(null)
    setAuthToken(null)
    setIsAuthenticated(false)
  }

  return (
    <SessionContext.Provider
      value={{ user_id, authToken, isAuthenticated, login, logout }}
    >
      {children}
    </SessionContext.Provider>
  )
}

export function useSession() {
  const ctx = useContext(SessionContext)
  if (!ctx) throw new Error('useSession must be used within a SessionProvider')
  return ctx
}
