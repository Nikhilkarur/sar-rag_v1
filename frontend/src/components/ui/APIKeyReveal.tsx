import { useEffect, useRef, useState } from 'react'
import { Eye, EyeOff, Lock } from 'lucide-react'
import { Button } from './Button'
import { CopyButton } from './CopyButton'
import { Input, Field } from './Input'
import { Modal } from './Modal'

interface APIKeyRevealProps {
  maskedDisplay: string
  fetchKey: () => Promise<string>
  label?: string
}

const REVEAL_SECONDS = 10
const RING_C = 2 * Math.PI * 9 // r=9 countdown ring

export function APIKeyReveal({ maskedDisplay, fetchKey, label = 'key' }: APIKeyRevealProps) {
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [password, setPassword] = useState('')
  const [passwordError, setPasswordError] = useState('')
  const [loading, setLoading] = useState(false)
  const [revealed, setRevealed] = useState<string | null>(null)
  const [remaining, setRemaining] = useState(REVEAL_SECONDS)
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    return () => {
      if (timerRef.current) clearInterval(timerRef.current)
    }
  }, [])

  const startCountdown = () => {
    setRemaining(REVEAL_SECONDS)
    timerRef.current = setInterval(() => {
      setRemaining((r) => {
        if (r <= 1) {
          if (timerRef.current) clearInterval(timerRef.current)
          setRevealed(null)
          return REVEAL_SECONDS
        }
        return r - 1
      })
    }, 1000)
  }

  const handleConfirm = async () => {
    if (password.length < 4) {
      setPasswordError('Enter your account password to reveal the key.')
      return
    }
    setLoading(true)
    try {
      const key = await fetchKey()
      setRevealed(key)
      setConfirmOpen(false)
      setPassword('')
      setPasswordError('')
      startCountdown()
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 8,
          background: 'var(--bg-base)',
          border: `1px solid ${revealed ? 'var(--warning)' : 'var(--border)'}`,
          borderRadius: 'var(--r-md)',
          padding: '8px 12px',
          transition: 'border-color var(--t-base)',
          animation: revealed ? 'revealFlash 600ms ease-out' : undefined,
          minWidth: 0,
        }}
      >
        <span
          style={{
            fontFamily: 'var(--font-mono)',
            fontSize: 13,
            color: revealed ? 'var(--text-1)' : 'var(--text-3)',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
            flex: 1,
          }}
        >
          {revealed ?? maskedDisplay}
        </span>
        {revealed && <CopyButton value={revealed} size={14} />}
        {revealed ? (
          <span style={{ display: 'flex', alignItems: 'center', gap: 6, flexShrink: 0 }}>
            <svg width="22" height="22" viewBox="0 0 22 22" className="countdown-ring">
              <circle cx="11" cy="11" r="9" stroke="var(--border)" strokeWidth="2" fill="none" />
              <circle
                cx="11"
                cy="11"
                r="9"
                stroke="var(--warning)"
                strokeWidth="2"
                fill="none"
                strokeLinecap="round"
                strokeDasharray={RING_C}
                strokeDashoffset={RING_C * (1 - remaining / REVEAL_SECONDS)}
                transform="rotate(-90 11 11)"
              />
            </svg>
            <button
              onClick={() => {
                if (timerRef.current) clearInterval(timerRef.current)
                setRevealed(null)
                setRemaining(REVEAL_SECONDS)
              }}
              aria-label="Hide key"
              style={{
                background: 'none',
                border: 'none',
                color: 'var(--text-3)',
                cursor: 'pointer',
                display: 'flex',
                padding: 2,
              }}
            >
              <Eye size={15} />
            </button>
          </span>
        ) : (
          <Button
            variant="secondary"
            size="sm"
            icon={<EyeOff size={13} />}
            onClick={() => setConfirmOpen(true)}
          >
            Reveal
          </Button>
        )}
      </div>
      {revealed && remaining <= 3 && (
        <div
          className="anim-fade-in"
          style={{ fontSize: 12, color: 'var(--warning)', marginTop: 6 }}
        >
          Hiding {label} in {remaining}…
        </div>
      )}

      <Modal
        open={confirmOpen}
        onClose={() => {
          setConfirmOpen(false)
          setPassword('')
          setPasswordError('')
        }}
        title="Confirm your password"
        width={380}
        footer={
          <>
            <Button variant="secondary" onClick={() => setConfirmOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleConfirm} loading={loading} icon={<Lock size={14} />}>
              Reveal Key
            </Button>
          </>
        }
      >
        <p style={{ fontSize: 13, color: 'var(--text-3)', marginBottom: 16 }}>
          For security, re-enter your account password. The {label} will be visible for{' '}
          {REVEAL_SECONDS} seconds.
        </p>
        <Field error={passwordError}>
          <Input
            type="password"
            placeholder="Account password"
            value={password}
            autoFocus
            onChange={(e) => {
              setPassword(e.target.value)
              setPasswordError('')
            }}
            onKeyDown={(e) => e.key === 'Enter' && handleConfirm()}
            error={!!passwordError}
          />
        </Field>
      </Modal>
    </>
  )
}
