import { useEffect, useState } from 'react'
import { AlertTriangle, CheckCircle2, RotateCcw, XCircle, Zap } from 'lucide-react'
import { useQueryClient } from '@tanstack/react-query'
import { useWebhookConfig, useWebhookEvents } from '../../../hooks/useTenant'
import { rotateWebhookSecret, sendTestWebhook, updateWebhookConfig } from '../../../api/tenant'
import { Button } from '../../../components/ui/Button'
import { Toggle } from '../../../components/ui/Toggle'
import { Input } from '../../../components/ui/Input'
import { CopyButton } from '../../../components/ui/CopyButton'
import { Modal } from '../../../components/ui/Modal'
import { Skeleton } from '../../../components/ui/Skeleton'
import { useToast } from '../../../components/ui/Toast'
import { WebhookEventCard } from '../../../components/WebhookEventCard'

type TestResult = { status: 'SUCCESS' | 'FAILED'; latency_ms: number; message?: string } | null

export function Webhook() {
  const { data: config, isLoading } = useWebhookConfig()
  const { data: events, isLoading: eventsLoading } = useWebhookEvents()
  const { toast } = useToast()
  const qc = useQueryClient()

  const [useSink, setUseSink] = useState(true)
  const [url, setUrl] = useState('')
  const [saving, setSaving] = useState(false)
  const [newSecret, setNewSecret] = useState<string | null>(null)
  const [rotateOpen, setRotateOpen] = useState(false)
  const [rotating, setRotating] = useState(false)
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState<TestResult>(null)

  useEffect(() => {
    if (config) {
      setUseSink(config.use_internal_sink)
      setUrl(config.callback_url ?? '')
    }
  }, [config])

  const handleToggle = async (next: boolean) => {
    setUseSink(next)
    if (next) {
      // Switching to the internal sink saves immediately — no URL needed.
      await updateWebhookConfig({ callback_url: undefined, use_internal_sink: true })
      qc.invalidateQueries({ queryKey: ['webhook-config'] })
      toast('success', 'Test receiver activated', 'SARs will be delivered to the built-in sink.')
    }
  }

  const handleSave = async () => {
    if (!/^https?:\/\/.+\..+/.test(url)) {
      toast('error', 'Invalid URL', 'Enter a valid https:// callback URL.')
      return
    }
    setSaving(true)
    try {
      // Saving only changes the destination; the signing secret is rotated separately (below),
      // so a URL change never invalidates the secret the bank verifies with.
      await updateWebhookConfig({ callback_url: url, use_internal_sink: false })
      qc.invalidateQueries({ queryKey: ['webhook-config'] })
      toast('success', 'Webhook configuration saved', 'Deliveries are signed with your current secret.')
    } finally {
      setSaving(false)
    }
  }

  const handleRotate = async () => {
    setRotating(true)
    try {
      // The full secret only exists in the rotate response — keep it in state to show once.
      const rotated = await rotateWebhookSecret()
      setNewSecret(rotated.secret)
      setRotateOpen(false)
      qc.invalidateQueries({ queryKey: ['webhook-config'] })
      toast('warning', 'Signing secret rotated', 'Your previous secret is now invalid.')
    } finally {
      setRotating(false)
    }
  }

  const handleTest = async () => {
    setTesting(true)
    setTestResult(null)
    try {
      const result = await sendTestWebhook()
      setTestResult(result as any)
      qc.invalidateQueries({ queryKey: ['webhook-events'] })
    } finally {
      setTesting(false)
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24, maxWidth: 760 }}>
      {/* Section 1 — Delivery Configuration */}
      <div className="card anim-fade-in-up">
        <h3 style={{ fontSize: 16, fontWeight: 600, letterSpacing: '-0.01em', marginBottom: 4 }}>
          Delivery Configuration
        </h3>
        <p style={{ fontSize: 13, color: 'var(--text-3)', marginBottom: 24 }}>
          Where approved SARs are delivered after officer sign-off.
        </p>

        {isLoading ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <Skeleton height={24} width={280} />
            <Skeleton height={38} />
          </div>
        ) : (
          <>
            <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
              <Toggle checked={useSink} onChange={handleToggle} />
              <div>
                <div style={{ fontSize: 14, fontWeight: 500, display: 'flex', alignItems: 'center', gap: 8 }}>
                  Use Built-in Test Receiver
                  {useSink && (
                    <span
                      className="anim-fade-in-up"
                      style={{
                        height: 20,
                        padding: '0 8px',
                        borderRadius: 'var(--r-full)',
                        background: 'var(--success-subtle)',
                        color: 'var(--success)',
                        fontSize: 11,
                        fontWeight: 600,
                        display: 'inline-flex',
                        alignItems: 'center',
                      }}
                    >
                      Active
                    </span>
                  )}
                </div>
                <div style={{ fontSize: 13, color: 'var(--text-3)', marginTop: 2 }}>
                  Verify the full pipeline without running your own callback server.
                </div>
              </div>
            </div>

            <div style={{ marginTop: 20 }}>
              {useSink ? (
                <div className="anim-fade-in">
                  <p style={{ fontSize: 12, color: 'var(--text-4)' }}>
                    Webhook payloads are recorded inside Aegis and listed in the Delivery Log below. No server
                    needed for testing.
                  </p>
                </div>
              ) : (
                <div className="anim-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                  <div>
                    <div className="label-upper" style={{ marginBottom: 8 }}>
                      Callback URL
                    </div>
                    <Input
                      placeholder="https://your-server.com/callback"
                      value={url}
                      onChange={(e) => setUrl(e.target.value)}
                      style={{ fontFamily: 'var(--font-mono)', fontSize: 13 }}
                    />
                  </div>
                  <div>
                    <Button onClick={handleSave} loading={saving} size="sm">
                      Save
                    </Button>
                  </div>
                  {(newSecret || config?.secret_prefix) && (
                    <div>
                      <div className="label-upper" style={{ marginBottom: 8 }}>
                        Signing Secret
                      </div>
                      {newSecret ? (
                        <div
                          className="anim-fade-in-up"
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: 8,
                            background: 'var(--warning-subtle)',
                            border: '1px solid var(--warning)',
                            borderRadius: 'var(--r-md)',
                            padding: '8px 12px',
                          }}
                        >
                          <span style={{ fontFamily: 'var(--font-mono)', fontSize: 13, flex: 1, wordBreak: 'break-all' }}>
                            {newSecret}
                          </span>
                          <CopyButton value={newSecret} />
                        </div>
                      ) : (
                        <span style={{ fontFamily: 'var(--font-mono)', fontSize: 13, color: 'var(--text-3)' }}>
                          {config?.secret_prefix}•••••••••••••••••••••••••
                        </span>
                      )}
                      {newSecret ? (
                        <p style={{ fontSize: 12, color: 'var(--warning)', marginTop: 6 }}>
                          Update your HMAC verification immediately — this secret is shown once.
                        </p>
                      ) : (
                        <p style={{ fontSize: 12, color: 'var(--text-4)', marginTop: 6 }}>
                          The full secret is only shown when it is generated. Generate a new one to set up
                          verification of <code>X-Aegis-Signature</code>.
                        </p>
                      )}
                      <div style={{ marginTop: 10 }}>
                        <Button
                          variant="danger-ghost"
                          size="sm"
                          icon={<RotateCcw size={13} />}
                          onClick={() => setRotateOpen(true)}
                        >
                          Generate New Secret
                        </Button>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </>
        )}
      </div>

      {/* Section 2 — Test */}
      <div className="card anim-fade-in-up" style={{ animationDelay: '80ms' }}>
        <h3 style={{ fontSize: 16, fontWeight: 600, letterSpacing: '-0.01em', marginBottom: 4 }}>
          Test & Verify
        </h3>
        <p style={{ fontSize: 13, color: 'var(--text-3)', marginBottom: 20 }}>
          Fires a sample SAR payload at the active receiver, signed with your secret.
        </p>
        <Button variant="secondary" icon={<Zap size={14} />} onClick={handleTest} loading={testing}>
          Send Test Payload
        </Button>
        {testResult && (
          <div
            className="anim-fade-in-up"
            style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 14, fontSize: 13 }}
          >
            {testResult.status === 'SUCCESS' ? (
              <>
                <CheckCircle2 size={15} color="var(--success)" />
                <span style={{ color: 'var(--success)' }}>Delivered in {testResult.latency_ms}ms</span>
              </>
            ) : (
              <>
                <XCircle size={15} color="var(--danger)" />
                <span style={{ color: 'var(--danger)' }}>Failed: {testResult.message ?? 'delivery failed'}</span>
              </>
            )}
          </div>
        )}
      </div>

      {/* Section 3 — Delivery Log */}
      <div className="card anim-fade-in-up" style={{ animationDelay: '160ms' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
          <h3 style={{ fontSize: 16, fontWeight: 600, letterSpacing: '-0.01em' }}>Delivery Log</h3>
          <span
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 6,
              fontSize: 12,
              color: 'var(--success)',
              background: 'var(--success-subtle)',
              padding: '2px 10px',
              borderRadius: 'var(--r-full)',
            }}
          >
            <span className="pulse-dot" style={{ background: 'var(--success)' }} />
            Live
          </span>
        </div>

        {eventsLoading ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            <Skeleton height={48} />
            <Skeleton height={48} />
            <Skeleton height={48} />
          </div>
        ) : (events ?? []).length === 0 ? (
          <p style={{ fontSize: 13, color: 'var(--text-4)', padding: '16px 0' }}>
            No deliveries yet. Approve a SAR or send a test payload to see events here.
          </p>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {(events ?? []).slice(0, 10).map((evt) => (
              <WebhookEventCard key={evt.id} event={evt} />
            ))}
          </div>
        )}
      </div>

      {/* Rotate secret modal */}
      <Modal
        open={rotateOpen}
        onClose={() => setRotateOpen(false)}
        title="Generate a new signing secret?"
        width={420}
        footer={
          <>
            <Button variant="secondary" onClick={() => setRotateOpen(false)}>
              Cancel
            </Button>
            <Button variant="danger" onClick={handleRotate} loading={rotating}>
              Generate
            </Button>
          </>
        }
      >
        <div
          style={{
            background: 'var(--danger-subtle)',
            border: '1px solid rgba(179,56,44,0.3)',
            borderRadius: 'var(--r-md)',
            padding: 14,
            fontSize: 13,
            color: 'var(--text-2)',
            display: 'flex',
            gap: 10,
            alignItems: 'flex-start',
          }}
        >
          <AlertTriangle size={15} color="var(--danger)" style={{ flexShrink: 0, marginTop: 1 }} />
          Your current secret stops working immediately: every delivery from now on, including retries, is
          signed with the new one. Update your HMAC verification right after.
        </div>
      </Modal>
    </div>
  )
}
