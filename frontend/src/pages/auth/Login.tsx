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

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!email || !password) {
      setError('Enter your email and password.')
      return
    }
    setLoading(true)
    setError('')
    try {
      const result = await login({ email, password })
      setAuth(result.user, result.access_token, result.refresh_token)
      navigate(result.user.role === 'SUPER_ADMIN' ? '/admin/verifications' : '/dashboard')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Sign in failed. Please try again.')
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

        <div
          style={{
            marginTop: 20,
            padding: '10px 12px',
            background: 'var(--bg-base)',
            border: '1px dashed var(--border)',
            borderRadius: 'var(--r-md)',
            fontSize: 11,
            color: 'var(--text-4)',
            fontFamily: 'var(--font-mono)',
            lineHeight: 1.8,
          }}
        >
          <span style={{ color: 'var(--text-3)' }}>Demo credentials</span>
          <br />
          demo@demofintech.com / Demo2026!
          <br />
          admin@aegis-aml.com / AegisAdmin2026!
        </div>
    </div>
  )
}
