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
    refresh token is dead even if it was copied (other sign-ins stay active). Fire-and-forget:
    it must not block sign-out. Sign-out buttons navigate in-app, so a plain request completes;
    keepalive (survives a hard redirect) only same-origin, since browsers may refuse the CORS
    preflight a cross-origin JSON keepalive request needs. */
function revokeServerSession() {
  const refreshToken = sessionStorage.getItem('aegis_refresh_token')
  if (!refreshToken) return
  const url = `${API_BASE_URL}/auth/logout`
  fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh_token: refreshToken }),
    keepalive: new URL(url, window.location.href).origin === window.location.origin,
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

/* ── Duplicated tabs ──────────────────────────────────────────────────
   "Duplicate tab" copies sessionStorage, so the copy holds the SAME refresh session as the
   original. Whichever tab refreshes second would then present an already-rotated token,
   which the backend treats as a replay and revokes the session, signing out BOTH tabs. So
   on load a tab asks the others whether its session is already open; if so it is the copy
   and gives the session up locally (it signs in again and gets its own), and the original
   keeps working. */
const TAB_ID = `${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}`
const TAB_BORN = Date.now()

/** The refresh JWT's session id ("sid"). Decoded only to compare tabs, never trusted. */
function currentSessionId(): string | null {
  try {
    const payload = sessionStorage.getItem('aegis_refresh_token')?.split('.')[1]
    if (!payload) return null
    return JSON.parse(atob(payload.replace(/-/g, '+').replace(/_/g, '/'))).sid ?? null
  } catch {
    return null
  }
}

function watchDuplicateTabs() {
  if (typeof BroadcastChannel === 'undefined') return
  const channel = new BroadcastChannel('aegis-auth-tabs')
  channel.onmessage = ({ data }) => {
    const sid = currentSessionId()
    if (!sid || data?.sid !== sid) return
    if (data.type === 'hello') {
      // The older tab keeps the session (tab id breaks a tie, e.g. two copies restored at once)
      if (TAB_BORN < data.born || (TAB_BORN === data.born && TAB_ID < data.tab)) {
        channel.postMessage({ type: 'taken', sid, to: data.tab })
      }
    } else if (data.type === 'taken' && data.to === TAB_ID) {
      // Local only: revoking the session server-side would sign the original out too
      sessionStorage.removeItem('aegis_refresh_token')
      useAuthStore.setState({ user: null, accessToken: null, isAuthenticated: false })
    }
  }
  const sid = currentSessionId()
  if (sid) channel.postMessage({ type: 'hello', sid, tab: TAB_ID, born: TAB_BORN })
}

watchDuplicateTabs()
