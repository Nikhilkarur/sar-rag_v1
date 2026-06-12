import { Link, Outlet } from 'react-router-dom'
import DotMesh from '../components/DotMesh'
import { AegisShield } from '../components/AegisLogo'

/**
 * Wraps /login, /signup, and /status — same Attio-school shell as the
 * landing page: white field, drifting dot mesh, brand top-left,
 * centered hairline card.
 */
export default function AuthLayout() {
  return (
    <div className="auth-layout">
      <div className="auth-mesh" aria-hidden="true">
        <DotMesh />
      </div>

      <Link to="/" className="auth-brand">
        <AegisShield size={22} />
        <span className="auth-brand-word">
          AEGIS <em>AML</em>
        </span>
      </Link>

      <div className="auth-content">
        <Outlet />
      </div>

      <div className="auth-foot">PMLA 2002 · FIU-IND goAML · © 2026 Aegis AML</div>
    </div>
  )
}
