import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { AlertCircle, Eye, EyeOff } from 'lucide-react'
import { login } from '../../api/auth'
import { useAuthStore } from '../../store/auth'
import { AegisShield } from '../../components/AegisLogo'
import { Button } from '../../components/ui/Button'
import { Input, Field } from '../../components/ui/Input'

export function Login() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()
  const setAuth = useAuthStore((s) => s.setAuth)

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    // Read the LIVE DOM values, not just React state. Chrome autofill can paint a field
    // without firing onChange, leaving `email`/`password` state stale/empty — which posts
    // the wrong credentials and gets a confusing 401. FormData reads whatever is actually
    // in the inputs; trim guards against copy-paste whitespace.
    const form = new FormData(e.currentTarget)
    const emailVal = (((form.get('email') as string | null) ?? email) || '').trim()
    const passwordVal = (((form.get('password') as string | null) ?? password) || '').trim()
    if (!emailVal || !passwordVal) {
      setError('Enter your email and password.')
      return
    }
    // Keep React state in sync with what we actually submit (in case autofill desynced it).
    setEmail(emailVal)
    setPassword(passwordVal)
    setLoading(true)
    setError('')
    try {
      const result = await login({ email: emailVal, password: passwordVal })
      setAuth(result.user, result.access_token, result.refresh_token)
      navigate(result.user.role === 'SUPER_ADMIN' ? '/admin/overview' : '/dashboard')
    } catch (err) {
      // Prefer the backend's message ("Invalid email or password") over axios's
      // generic "Request failed with status code 401".
      const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail
      setError(typeof detail === 'string' ? detail : 'Sign in failed. Please check your email and password.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div
      style={{
        width: 400,
        maxWidth: '100%',
        background: 'var(--bg-surface)',
        border: '1px solid var(--border)',
        borderRadius: 'var(--r-xl)',
        boxShadow: 'var(--shadow-lg)',
        padding: 40,
        animation: 'scaleIn 250ms ease-out',
      }}
    >
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', textAlign: 'center' }}>
          <AegisShield size={34} />
          <h1 style={{ fontSize: 22, fontWeight: 600, marginTop: 14, letterSpacing: '-0.02em', color: 'var(--text-1)' }}>
            Sign in to Aegis
          </h1>
          <p style={{ fontSize: 13.5, color: 'var(--text-3)', marginTop: 6 }}>
            The compliance workspace for your team.
          </p>
        </div>

        <div style={{ height: 1, background: 'var(--border-subtle)', margin: '24px 0' }} />

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <Field label="Email">
            <Input
              type="email"
              name="email"
              placeholder="you@company.com"
              value={email}
              autoComplete="email"
              autoFocus
              onChange={(e) => {
                setEmail(e.target.value)
                setError('')
              }}
            />
          </Field>
          <Field label="Password">
            <Input
              type={showPassword ? 'text' : 'password'}
              name="password"
              placeholder="••••••••••"
              value={password}
              autoComplete="current-password"
              onChange={(e) => {
                setPassword(e.target.value)
                setError('')
              }}
              rightSlot={
                <button
                  type="button"
                  onClick={() => setShowPassword((s) => !s)}
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                  style={{
                    background: 'none',
                    border: 'none',
                    color: 'var(--text-4)',
                    cursor: 'pointer',
                    display: 'flex',
                    padding: 4,
                  }}
                >
                  {showPassword ? <EyeOff size={15} /> : <Eye size={15} />}
                </button>
              }
            />
          </Field>

          {error && (
            <div
              className="anim-fade-in-up"
              style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, color: 'var(--danger)' }}
            >
              <AlertCircle size={14} style={{ flexShrink: 0 }} />
              {error}
            </div>
          )}

          <Button type="submit" loading={loading} fullWidth style={{ height: 40 }}>
            Sign in →
          </Button>
        </form>

        <div style={{ height: 1, background: 'var(--border-subtle)', margin: '24px 0' }} />

        <div style={{ textAlign: 'center' }}>
          <Link
            to="/signup"
            style={{ fontSize: 13, color: 'var(--text-3)', textDecoration: 'none', transition: 'color var(--t-fast)' }}
            onMouseEnter={(e) => (e.currentTarget.style.color = 'var(--accent-text)')}
            onMouseLeave={(e) => (e.currentTarget.style.color = 'var(--text-3)')}
          >
            New entity? Request access →
          </Link>
        </div>
    </div>
  )
}
