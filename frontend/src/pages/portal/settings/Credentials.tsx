import { useState } from 'react'
import { AlertTriangle, ArrowRight, RotateCcw } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import { useCredentials } from '../../../hooks/useTenant'
import { revealApiKey, rotateApiKey } from '../../../api/tenant'
import { useAuthStore } from '../../../store/auth'
import { Button } from '../../../components/ui/Button'
import { Modal } from '../../../components/ui/Modal'
import { CopyButton } from '../../../components/ui/CopyButton'
import { APIKeyReveal } from '../../../components/ui/APIKeyReveal'
import { Skeleton } from '../../../components/ui/Skeleton'
import { useToast } from '../../../components/ui/Toast'

export function Credentials() {
  const { data: creds, isLoading } = useCredentials()
  const { user } = useAuthStore()
  const { toast } = useToast()
  const qc = useQueryClient()

  const [rotateOpen, setRotateOpen] = useState(false)
  const [rotating, setRotating] = useState(false)
  const [newKey, setNewKey] = useState<string | null>(null)

  const tenantId = creds?.tenant_id_public ?? user?.tenant?.tenantIdPublic ?? 'TEN-0001'

  const handleRotate = async () => {
    setRotating(true)
    try {
      const result = await rotateApiKey()
      setNewKey(result.new_api_key)
      setRotateOpen(false)
      qc.invalidateQueries({ queryKey: ['credentials'] })
      toast('warning', 'API key rotated', 'Your previous key is now invalid.')
    } finally {
      setRotating(false)
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24, maxWidth: 760 }}>
      {/* Card 1 — Credentials */}
      <div className="card anim-fade-in-up">
        <h3 style={{ fontSize: 16, fontWeight: 600, letterSpacing: '-0.01em', marginBottom: 4 }}>
          API Credentials
        </h3>
        <p style={{ fontSize: 13, color: 'var(--text-3)', marginBottom: 24 }}>
          Use these to authenticate calls to the alert ingestion API.
        </p>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
          <div>
            <div className="label-upper" style={{ marginBottom: 8 }}>
              X-Tenant-ID
            </div>
            {isLoading ? (
              <Skeleton width={220} height={32} />
            ) : (
              <div style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
                <span
                  style={{
                    background: 'var(--bg-base)',
                    border: '1px solid var(--border)',
                    borderRadius: 'var(--r-sm)',
                    padding: '4px 10px',
                    fontFamily: 'var(--font-mono)',
                    fontSize: 13,
                    color: 'var(--text-1)',
                  }}
                >
                  {tenantId}
                </span>
                <CopyButton value={tenantId} />
              </div>
            )}
          </div>

          <div>
            <div className="label-upper" style={{ marginBottom: 8 }}>
              X-API-Key
            </div>
            {isLoading ? (
              <Skeleton width="100%" height={38} />
            ) : (
              <APIKeyReveal
                maskedDisplay={`${creds?.api_key_prefix ?? 'sk-ae-a1b2'}••••••••••••••••••••••••••••••••`}
                fetchKey={async () => { const res = await revealApiKey(); return res.api_key; }}
                label="key"
              />
            )}
          </div>

          {newKey && (
            <div
              className="anim-fade-in-up"
              style={{
                border: '1px solid var(--warning)',
                borderRadius: 'var(--r-md)',
                overflow: 'hidden',
              }}
            >
              <div
                style={{
                  background: 'var(--danger-subtle)',
                  borderBottom: '1px solid rgba(179,56,44,0.3)',
                  padding: '8px 14px',
                  fontSize: 12,
                  fontWeight: 600,
                  color: 'var(--danger)',
                }}
              >
                This key will not be shown again.
              </div>
              <div style={{ padding: 16, background: 'var(--warning-subtle)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
                  <AlertTriangle size={14} color="var(--warning)" />
                  <span style={{ fontSize: 13, fontWeight: 500, color: 'var(--warning)' }}>
                    New key — copy immediately.
                  </span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span
                    style={{
                      fontFamily: 'var(--font-mono)',
                      fontSize: 14,
                      color: 'var(--text-1)',
                      wordBreak: 'break-all',
                      flex: 1,
                    }}
                  >
                    {newKey}
                  </span>
                  <CopyButton value={newKey} />
                </div>
              </div>
            </div>
          )}

          <div>
            <Button
              variant="danger-ghost"
              size="sm"
              icon={<RotateCcw size={13} />}
              onClick={() => setRotateOpen(true)}
            >
              Rotate API Key
            </Button>
          </div>
        </div>
      </div>

      {/* Card 2 — pointer to the consolidated technical reference */}
      <Link
        to="/settings/schema"
        className="card anim-fade-in-up card-interactive"
        style={{ padding: 20, display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 16, textDecoration: 'none', color: 'inherit', animationDelay: '80ms' }}
      >
        <div>
          <h3 style={{ fontSize: 15, fontWeight: 600, letterSpacing: '-0.01em' }}>Integration guide &amp; API reference</h3>
          <p style={{ fontSize: 13, color: 'var(--text-3)', marginTop: 4 }}>
            The full endpoint, payload schema, and webhook contract now live in one printable
            handoff document under <b>Ingestion Schema</b>.
          </p>
        </div>
        <ArrowRight size={16} color="var(--text-3)" style={{ flexShrink: 0 }} />
      </Link>

      {/* Rotate modal */}
      <Modal
        open={rotateOpen}
        onClose={() => setRotateOpen(false)}
        title="Rotate API Key?"
        width={420}
        footer={
          <>
            <Button variant="secondary" onClick={() => setRotateOpen(false)}>
              Cancel
            </Button>
            <Button variant="danger" onClick={handleRotate} loading={rotating}>
              Rotate
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
          Your current key will stop working immediately. Update your integration before rotating.
        </div>
      </Modal>
    </div>
  )
}
