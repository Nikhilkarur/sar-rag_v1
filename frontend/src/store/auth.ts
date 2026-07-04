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
        sessionStorage.removeItem('aegis_refresh_token')
        set({ user: null, accessToken: null, isAuthenticated: false })
      },
      logout: () => {
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
