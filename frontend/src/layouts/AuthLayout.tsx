import { Outlet } from 'react-router-dom'
import UniverseCanvas from '../components/UniverseCanvas/UniverseCanvas'

/**
 * Wraps /login, /signup, and /status. The compliance universe runs behind
 * frosted glass — visible, alive, but out of reach until the user is in.
 */
export default function AuthLayout() {
  return (
    <div className="auth-layout">
      {/* Background: the universe, blurred */}
      <div className="auth-universe-bg" aria-hidden="true">
        <UniverseCanvas interactive={false} blurred={true} />
      </div>

      {/* Frosted glass overlay — sits between canvas and card */}
      <div className="auth-glass-overlay" aria-hidden="true" />

      {/* Page content (login card, signup card, status card) */}
      <div className="auth-content">
        <Outlet />
      </div>
    </div>
  )
}
