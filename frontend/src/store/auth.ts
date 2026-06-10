import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { User } from '../types'

interface AuthState {
  user: User | null
  accessToken: string | null
  isAuthenticated: boolean
  setAuth: (user: User, accessToken: string, refreshToken: string) => void
  updateUser: (user: User) => void
  clearAuth: () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      accessToken: null,
      isAuthenticated: false,
      setAuth: (user, accessToken, refreshToken) => {
        localStorage.setItem('aegis_refresh_token', refreshToken)
        set({ user, accessToken, isAuthenticated: true })
      },
      updateUser: (user) => set({ user }),
      clearAuth: () => {
        localStorage.removeItem('aegis_refresh_token')
        set({ user: null, accessToken: null, isAuthenticated: false })
      },
    }),
    { name: 'aegis-auth' },
  ),
)
