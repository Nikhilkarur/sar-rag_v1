import { useEffect, useState } from 'react'
import { CheckCircle2, XCircle, Zap } from 'lucide-react'
import { useQueryClient } from '@tanstack/react-query'
import { useWebhookConfig, useWebhookEvents } from '../../../hooks/useTenant'
import { sendTestWebhook, updateWebhookConfig } from '../../../api/tenant'
import { Button } from '../../../components/ui/Button'
import { Toggle } from '../../../components/ui/Toggle'
import { Input } from '../../../components/ui/Input'
import { CopyButton } from '../../../components/ui/CopyButton'
import { Skeleton } from '../../../components/ui/Skeleton'
import { useToast } from '../../../components/ui/Toast'
import { WebhookEventCard } from '../../../components/WebhookEventCard'

type TestResult = { status: 'SUCCESS' | 'FAILED'; latency_ms: number } | null

export function Webhook() {
  const { data: config, isLoading } = useWebhookConfig()
  const { data: events, isLoading: eventsLoading } = useWebhookEvents()
  const { toast } = useToast()
  const qc = useQueryClient()

  const [useSink, setUseSink] = useState(true)
  const [url, setUrl] = useState('')
  const [saving, setSaving] = useState(false)
  const [newSecret, setNewSecret] = useState<string | null>(null)
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
      const result = await updateWebhookConfig({ callback_url: url, use_internal_sink: false })
      setNewSecret(result.secret_prefix)
      qc.invalidateQueries({ queryKey: ['webhook-config'] })
      toast('success', 'Webhook configuration saved', 'A new signing secret was generated.')
    } finally {
      setSaving(false)
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
                  <div className="label-upper" style={{ marginBottom: 8 }}>
                    Sink URL
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    <Input
                      readOnly
                      value={config?.internal_sink_url ?? ''}
                      style={{ fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--text-2)' }}
                    />
                    <CopyButton value={config?.internal_sink_url ?? ''} />
                  </div>
                  <p style={{ fontSize: 12, color: 'var(--text-4)', marginTop: 8 }}>
                    Webhook payloads are delivered internally. No server needed for testing.
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
                      Save & Generate Secret
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
                      {newSecret && (
                        <p style={{ fontSize: 12, color: 'var(--warning)', marginTop: 6 }}>
                          Update your HMAC verification immediately — this secret is shown once.
                        </p>
                      )}
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
                <span style={{ color: 'var(--danger)' }}>Failed: 404 Not Found</span>
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
    </div>
  )
}
