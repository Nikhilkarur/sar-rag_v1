import { useState } from 'react'
import { AlertTriangle, ChevronDown, RotateCcw } from 'lucide-react'
import { useQueryClient } from '@tanstack/react-query'
import { useCredentials } from '../../../hooks/useTenant'
import { revealApiKey, rotateApiKey } from '../../../api/tenant'
import { useAuthStore } from '../../../store/auth'
import { Button } from '../../../components/ui/Button'
import { Modal } from '../../../components/ui/Modal'
import { CopyButton } from '../../../components/ui/CopyButton'
import { CodeBlock } from '../../../components/ui/CodeBlock'
import { APIKeyReveal } from '../../../components/ui/APIKeyReveal'
import { Skeleton } from '../../../components/ui/Skeleton'
import { useToast } from '../../../components/ui/Toast'
import { cls } from '../../../utils/format'

const SNIPPETS = (tenantId: string) => ({
  cURL: `# Submit a flagged transaction alert to Aegis
curl -X POST https://api.aegis-aml.com/api/v1/alerts/ingest \\
  -H "X-API-Key: sk-ae-YOUR-API-KEY" \\
  -H "X-Tenant-ID: ${tenantId}" \\
  -H "Content-Type: application/json" \\
  -d '{
    "customer": { "full_name": "Rajesh Kumar", "id": "CUST-98271" },
    "account":  { "number": "HDFC-00123456789" },
    "txn": {
      "ref_id": "TXN-2026-061099182",
      "amount": 990000.00,
      "currency": "INR",
      "type": "NEFT_TRANSFER",
      "direction": "DEBIT",
      "timestamp": "2026-06-10T09:30:00+05:30"
    },
    "risk": { "score": 87, "reason": "Near reporting threshold" }
  }'`,
  Python: `import httpx

# Submit a flagged transaction alert to Aegis
response = httpx.post(
    "https://api.aegis-aml.com/api/v1/alerts/ingest",
    headers={
        "X-API-Key": "sk-ae-YOUR-API-KEY",
        "X-Tenant-ID": "${tenantId}",
    },
    json={
        "customer": {"full_name": "Rajesh Kumar", "id": "CUST-98271"},
        "account": {"number": "HDFC-00123456789"},
        "txn": {
            "ref_id": "TXN-2026-061099182",
            "amount": 990000.00,
            "currency": "INR",
            "type": "NEFT_TRANSFER",
            "direction": "DEBIT",
            "timestamp": "2026-06-10T09:30:00+05:30",
        },
        "risk": {"score": 87, "reason": "Near reporting threshold"},
    },
)
print(response.json())  # {"alert_id": "...", "status": "PROCESSING"}`,
  'Node.js': `import axios from 'axios'

// Submit a flagged transaction alert to Aegis
const { data } = await axios.post(
  'https://api.aegis-aml.com/api/v1/alerts/ingest',
  {
    customer: { full_name: 'Rajesh Kumar', id: 'CUST-98271' },
    account: { number: 'HDFC-00123456789' },
    txn: {
      ref_id: 'TXN-2026-061099182',
      amount: 990000.0,
      currency: 'INR',
      type: 'NEFT_TRANSFER',
      direction: 'DEBIT',
      timestamp: '2026-06-10T09:30:00+05:30',
    },
    risk: { score: 87, reason: 'Near reporting threshold' },
  },
  {
    headers: {
      'X-API-Key': 'sk-ae-YOUR-API-KEY',
      'X-Tenant-ID': '${tenantId}',
    },
  },
)
console.log(data) // { alert_id: '...', status: 'PROCESSING' }`,
})

export function Credentials() {
  const { data: creds, isLoading } = useCredentials()
  const { user } = useAuthStore()
  const { toast } = useToast()
  const qc = useQueryClient()

  const [guideOpen, setGuideOpen] = useState(false)
  const [tab, setTab] = useState<'cURL' | 'Python' | 'Node.js'>('cURL')
  const [rotateOpen, setRotateOpen] = useState(false)
  const [rotating, setRotating] = useState(false)
  const [newKey, setNewKey] = useState<string | null>(null)

  const tenantId = creds?.tenant_id_public ?? user?.tenant?.tenantIdPublic ?? 'TEN-0001'
  const snippets = SNIPPETS(tenantId)

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

      {/* Card 2 — Integration Guide */}
      <div className="card anim-fade-in-up" style={{ padding: 0, animationDelay: '80ms' }}>
        <button
          onClick={() => setGuideOpen((o) => !o)}
          style={{
            width: '100%',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: 24,
            background: 'none',
            border: 'none',
            cursor: 'pointer',
            color: 'var(--text-1)',
          }}
        >
          <div style={{ textAlign: 'left' }}>
            <h3 style={{ fontSize: 16, fontWeight: 600, letterSpacing: '-0.01em' }}>Integration Guide</h3>
            <p style={{ fontSize: 13, color: 'var(--text-3)', marginTop: 4 }}>
              How to call <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12 }}>/api/v1/alerts/ingest</span> from your TMS
            </p>
          </div>
          <ChevronDown
            size={16}
            color="var(--text-3)"
            style={{ transition: 'transform 200ms', transform: guideOpen ? 'rotate(180deg)' : 'none' }}
          />
        </button>
        <div className="accordion-body" style={{ maxHeight: guideOpen ? 900 : 0, opacity: guideOpen ? 1 : 0 }}>
          <div style={{ padding: '0 24px 24px' }}>
            <div style={{ display: 'flex', gap: 4, marginBottom: 12 }}>
              {(Object.keys(snippets) as (keyof typeof snippets)[]).map((t) => (
                <button key={t} className={cls('chip', tab === t && 'chip-active')} onClick={() => setTab(t)}>
                  {t}
                </button>
              ))}
            </div>
            <div key={tab} className="anim-fade-in">
              <CodeBlock
                code={snippets[tab]}
                language={tab === 'cURL' ? 'bash' : tab === 'Python' ? 'python' : 'javascript'}
                maxHeight={420}
              />
            </div>
          </div>
        </div>
      </div>

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
