import { useNavigate } from 'react-router-dom'
import { Check, Mail, X } from 'lucide-react'
import { useAuthStore } from '../../store/auth'
import { AegisShield } from '../../components/AegisLogo'
import { Button } from '../../components/ui/Button'

function TimelineNode({
  label,
  state,
}: {
  label: string
  state: 'done' | 'active' | 'pending'
}) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8, width: 110 }}>
      <div
        style={{
          width: 28,
          height: 28,
          borderRadius: '50%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          flexShrink: 0,
          background:
            state === 'done' ? 'var(--success)' : state === 'active' ? 'var(--warning-subtle)' : 'transparent',
          border:
            state === 'done'
              ? '1.5px solid var(--success)'
              : state === 'active'
                ? '1.5px solid var(--warning)'
                : '1.5px solid var(--border)',
          animation: state === 'active' ? 'processingPulse 2s infinite' : undefined,
        }}
      >
        {state === 'done' && <Check size={14} color="#fff" />}
        {state === 'active' && (
          <span style={{ width: 8, height: 8, borderRadius: '50%', background: 'var(--warning)' }} />
        )}
      </div>
      <span
        style={{
          fontSize: 12,
          color: state === 'pending' ? 'var(--text-4)' : 'var(--text-2)',
          fontWeight: state === 'active' ? 500 : 400,
          whiteSpace: 'nowrap',
        }}
      >
        {label}
      </span>
    </div>
  )
}

export function StatusPage() {
  const { user, clearAuth } = useAuthStore()
  const navigate = useNavigate()
  const status = user?.tenant?.status
  const rejected = status === 'REJECTED'

  return (
    <div
      style={{
        width: 480,
        maxWidth: '100%',
        background: 'var(--bg-surface)',
        border: '1px solid var(--border)',
        borderRadius: 'var(--r-xl)',
        boxShadow: 'var(--shadow-lg)',
        padding: 48,
        textAlign: 'center',
        animation: 'scaleIn 250ms ease-out',
        margin: 'auto',
      }}
    >
        <div style={{ display: 'flex', justifyContent: 'center', marginBottom: 24 }}>
          <AegisShield size={32} />
        </div>

        {!rejected ? (
          <>
            <div style={{ display: 'flex', justifyContent: 'center', marginBottom: 20 }}>
              <div className="status-ring" />
            </div>
            <h1 style={{ fontSize: 24, fontWeight: 600, letterSpacing: '-0.02em' }}>
              Application Under Review
            </h1>
            <p style={{ fontSize: 14, color: 'var(--text-3)', marginTop: 10, lineHeight: 1.6 }}>
              {user?.tenant?.name} is being manually verified by the Aegis team. We verify every
              regulated entity before activation.
            </p>

            <div
              style={{
                display: 'flex',
                alignItems: 'flex-start',
                justifyContent: 'center',
                margin: '32px 0 8px',
              }}
            >
              <TimelineNode label="Submitted" state="done" />
              <div style={{ flex: 1, height: 2, background: 'var(--success)', marginTop: 13, maxWidth: 60 }} />
              <TimelineNode label="Under Review" state="active" />
              <div style={{ flex: 1, height: 2, background: 'var(--border)', marginTop: 13, maxWidth: 60 }} />
              <TimelineNode label="Activated" state="pending" />
            </div>

            <p style={{ fontSize: 12, color: 'var(--text-4)', marginTop: 20 }}>
              Typically 1–2 business days.
            </p>
            <a
              href="mailto:support@aegis-aml.com"
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: 6,
                marginTop: 12,
                fontSize: 13,
                color: 'var(--accent-text)',
                textDecoration: 'none',
              }}
            >
              <Mail size={13} />
              support@aegis-aml.com
            </a>
          </>
        ) : (
          <>
            <div style={{ display: 'flex', justifyContent: 'center', marginBottom: 20 }}>
              <div
                style={{
                  width: 40,
                  height: 40,
                  borderRadius: '50%',
                  background: 'var(--danger-subtle)',
                  border: '1.5px solid var(--danger)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  animation: 'scaleIn 300ms cubic-bezier(0.34,1.56,0.64,1)',
                }}
              >
                <X size={20} color="var(--danger)" />
              </div>
            </div>
            <h1 style={{ fontSize: 24, fontWeight: 600, letterSpacing: '-0.02em' }}>
              Application Not Approved
            </h1>
            <div
              style={{
                background: 'var(--danger-subtle)',
                border: '1px solid rgba(239,68,68,0.3)',
                borderRadius: 'var(--r-md)',
                padding: 16,
                marginTop: 20,
                fontSize: 14,
                color: 'var(--text-2)',
                textAlign: 'left',
              }}
            >
              {user?.tenant?.rejectionReason ??
                'We were unable to verify the registration details provided. Please contact us to discuss your application.'}
            </div>
            <div style={{ marginTop: 24 }}>
              <Button onClick={() => (window.location.href = 'mailto:support@aegis-aml.com')}>
                Contact us to appeal
              </Button>
            </div>
          </>
        )}

        <div style={{ marginTop: 32, borderTop: '1px solid var(--border-subtle)', paddingTop: 16 }}>
          <button
            onClick={() => {
              clearAuth()
              navigate('/login')
            }}
            style={{
              background: 'none',
              border: 'none',
              fontSize: 13,
              color: 'var(--text-4)',
              cursor: 'pointer',
              transition: 'color var(--t-fast)',
            }}
            onMouseEnter={(e) => (e.currentTarget.style.color = 'var(--text-1)')}
            onMouseLeave={(e) => (e.currentTarget.style.color = 'var(--text-4)')}
          >
            Sign out
          </button>
        </div>
    </div>
  )
}
