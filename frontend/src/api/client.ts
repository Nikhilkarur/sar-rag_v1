import axios, { AxiosError, type InternalAxiosRequestConfig } from 'axios'
import { useAuthStore } from '../store/auth'

/** Base axios instance for the FastAPI backend. */
const client = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1',
  headers: { 'Content-Type': 'application/json' },
})

// Request: attach access token
client.interceptors.request.use((config) => {
  const token = useAuthStore.getState().accessToken
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

/* ── 401 → silent refresh ─────────────────────────────────────────────
   The backend ROTATES refresh tokens: every successful /auth/refresh
   invalidates the old token and returns a new pair. We must persist the
   new refresh token immediately or the next refresh will 401 and force
   a logout. A single in-flight refresh promise is shared so concurrent
   401s don't race each other into double-rotation. */

let refreshing: Promise<string | null> | null = null

async function refreshAccessToken(): Promise<string | null> {
  const refreshToken = sessionStorage.getItem('aegis_refresh_token')
  if (!refreshToken) return null
  try {
    // Raw axios (not `client`) so a 401 here can't recurse into this interceptor
    const { data } = await axios.post(`${client.defaults.baseURL}/auth/refresh`, {
      refresh_token: refreshToken,
    })
    // Persist the rotated pair — the old refresh token is now dead server-side
    sessionStorage.setItem('aegis_refresh_token', data.refresh_token as string)
    const store = useAuthStore.getState()
    if (store.user) store.setAuth(store.user, data.access_token as string, data.refresh_token as string)
    return data.access_token as string
  } catch {
    return null
  }
}

function forceLogout() {
  useAuthStore.getState().clearAuth()
  if (!window.location.pathname.startsWith('/login')) {
    window.location.href = '/login?expired=1'
  }
}

/** Auth endpoints must never trigger the refresh dance: a failed login is
    just a failed login, and a failed refresh is already terminal. */
function isAuthRoute(config: InternalAxiosRequestConfig | undefined): boolean {
  const url = config?.url ?? ''
  return url.includes('/auth/login') || url.includes('/auth/signup') || url.includes('/auth/refresh')
}

client.interceptors.response.use(
  (r) => r,
  async (error: AxiosError) => {
    const original = error.config as (InternalAxiosRequestConfig & { _retried?: boolean }) | undefined
    if (error.response?.status === 401 && original && !original._retried && !isAuthRoute(original)) {
      original._retried = true
      if (!refreshing) {
        refreshing = refreshAccessToken().finally(() => {
          refreshing = null
        })
      }
      const newToken = await refreshing
      if (newToken) {
        original.headers.Authorization = `Bearer ${newToken}`
        return client(original)
      }
      forceLogout()
    }
    return Promise.reject(error)
  },
)

export { client as api }
export default client
