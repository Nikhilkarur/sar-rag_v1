// The product is single-theme: warm editorial light (FT paper × Stripe × Apple).
// This module survives only so stale imports keep working; it always applies light.
export type Theme = 'light'

export function useThemeStore() {
  return { theme: 'light' as Theme, setTheme: () => {}, toggleTheme: () => {} }
}

if (typeof document !== 'undefined') {
  document.documentElement.dataset.theme = 'light'
  // Clear any persisted dark preference from earlier builds
  try { localStorage.removeItem('aegis-theme') } catch { /* private mode */ }
}
