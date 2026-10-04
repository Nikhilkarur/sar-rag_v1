import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'
import type { User } from '../types'

interface AuthState {
  user: User | null
  accessToken: string | null
  isAuthenticated: boolean
  setAuth: (user: User, accessToken: string, refreshToken: string) => void
  updateUser: (user: User) => void
  clearAuth: () => void
  /** Alias of clearAuth — both names are used across the app */
  logout: () => void
}

// Same base URL as api/client.ts (which imports this store, so it can't be imported here)
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'

/** Best-effort server-side revoke of this tab's refresh session, so a signed-out tab's
    refresh token is dead even if it was copied (other sign-ins stay active). Fire-and-forget
    with keepalive: it must not block sign-out and must survive the hard redirect to /login
    that can follow. */
function revokeServerSession() {
  const refreshToken = sessionStorage.getItem('aegis_refresh_token')
  if (!refreshToken) return
  fetch(`${API_BASE_URL}/auth/logout`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh_token: refreshToken }),
    keepalive: true,
  }).catch(() => {})
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      accessToken: null,
      isAuthenticated: false,
      setAuth: (user, accessToken, refreshToken) => {
        sessionStorage.setItem('aegis_refresh_token', refreshToken)
        set({ user, accessToken, isAuthenticated: true })
      },
      updateUser: (user) => set({ user }),
      clearAuth: () => {
        revokeServerSession()
        sessionStorage.removeItem('aegis_refresh_token')
        set({ user: null, accessToken: null, isAuthenticated: false })
      },
      logout: () => {
        revokeServerSession()
        sessionStorage.removeItem('aegis_refresh_token')
        set({ user: null, accessToken: null, isAuthenticated: false })
      },
    }),
    {
      name: 'aegis-auth',
      // Session-scoped (not localStorage): closing the tab/browser clears the login,
      // so the dashboard cannot be reached without signing in again. Backend security
      // (JWT, refresh-token rotation, rate limiting, etc.) is unchanged.
      storage: createJSONStorage(() => sessionStorage),
    },
  ),
)
