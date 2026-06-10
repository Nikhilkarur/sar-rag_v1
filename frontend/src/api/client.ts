import axios from 'axios'
import { useAuthStore } from '../store/auth'

/**
 * Base axios instance. The mock layer (src/mocks/store.ts) currently serves
 * all data; when the FastAPI backend lands, the api/* modules switch over to
 * this client without touching any page code.
 */
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

// Response: on 401, attempt token refresh once, else clear auth + redirect
let refreshing: Promise<string | null> | null = null

async function tryRefresh(): Promise<string | null> {
  const refreshToken = localStorage.getItem('aegis_refresh_token')
  if (!refreshToken) return null
  try {
    const { data } = await axios.post(
      `${client.defaults.baseURL}/auth/refresh`,
      { refresh_token: refreshToken },
    )
    return data.access_token as string
  } catch {
    return null
  }
}

client.interceptors.response.use(
  (r) => r,
  async (error) => {
    const original = error.config
    if (error.response?.status === 401 && original && !original._retried) {
      original._retried = true
      refreshing = refreshing ?? tryRefresh()
      const newToken = await refreshing
      refreshing = null
      if (newToken) {
        const store = useAuthStore.getState()
        if (store.user) store.setAuth(store.user, newToken, localStorage.getItem('aegis_refresh_token') || '')
        original.headers.Authorization = `Bearer ${newToken}`
        return client(original)
      }
      useAuthStore.getState().clearAuth()
      window.location.href = '/login'
    }
    return Promise.reject(error)
  },
)

export default client
