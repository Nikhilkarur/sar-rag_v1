import { useState } from 'react'
import { AlertTriangle, Check, Copy, UserCheck, X } from 'lucide-react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { approveTenant, listVerifications, rejectTenant } from '../../api/admin'
import { Button } from '../../components/ui/Button'
import { Modal } from '../../components/ui/Modal'
import { CopyButton } from '../../components/ui/CopyButton'
import { EmptyState } from '../../components/ui/EmptyState'
import { SkeletonTableRows } from '../../components/ui/Skeleton'
import { useToast } from '../../components/ui/Toast'
import { formatDateTime } from '../../utils/format'
import type { VerificationItem } from '../../types'

interface ApprovedCreds {
  name: string
  api_key: string
  tenant_id: string
}

export function Verifications() {
  const { data: items, isLoading } = useQuery({
    queryKey: ['verifications'],
    queryFn: listVerifications,
  })
  const qc = useQueryClient()
  const { toast } = useToast()

  const [approveTarget, setApproveTarget] = useState<VerificationItem | null>(null)
  const [rejectTarget, setRejectTarget] = useState<VerificationItem | null>(null)
  const [rejectReason, setRejectReason] = useState('')
  const [busy, setBusy] = useState(false)
  const [creds, setCreds] = useState<ApprovedCreds | null>(null)
  const [exitingRows, setExitingRows] = useState<Set<string>>(new Set())

  const dismissRow = (id: string, after: () => void) => {
    setExitingRows((s) => new Set(s).add(id))
    setTimeout(() => {
      after()
      setExitingRows((s) => {
        const next = new Set(s)
        next.delete(id)
        return next
      })
    }, 300)
  }

  const handleApprove = async () => {
    if (!approveTarget) return
    setBusy(true)
    try {
      const result = await approveTenant(approveTarget.id)
      const target = approveTarget
      setApproveTarget(null)
      setCreds({ name: target.name, api_key: result.api_key, tenant_id: result.tenant_id })
      dismissRow(target.id, () => {
        qc.invalidateQueries({ queryKey: ['verifications'] })
        qc.invalidateQueries({ queryKey: ['customers'] })
      })
    } finally {
      setBusy(false)
    }
  }

  const handleReject = async () => {
    if (!rejectTarget || !rejectReason.trim()) return
    setBusy(true)
    try {
      await rejectTenant(rejectTarget.id, rejectReason)
      const target = rejectTarget
      setRejectTarget(null)
      setRejectReason('')
      toast('info', 'Application rejected', `${target.name} has been notified.`)
      dismissRow(target.id, () => qc.invalidateQueries({ queryKey: ['verifications'] }))
    } finally {
      setBusy(false)
    }
  }

  const visible = items ?? []

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <h1 style={{ fontSize: 24, fontWeight: 600, letterSpacing: '-0.02em' }}>Verification Queue</h1>
        {visible.length > 0 && (
          <span
            style={{
              height: 22,
              padding: '0 10px',
              borderRadius: 'var(--r-full)',
              background: 'var(--warning-subtle)',
              color: 'var(--warning)',
              fontSize: 12,
              fontWeight: 500,
              display: 'inline-flex',
              alignItems: 'center',
            }}
          >
            {visible.length} pending
          </span>
        )}
      </div>

      {!isLoading && visible.length === 0 ? (
        <EmptyState
          icon={<UserCheck size={48} />}
          title="All caught up"
          description="No pending verifications. New registrations will appear here."
        />
      ) : (
        <div className="card" style={{ padding: 0 }}>
          <div className="tbl-scroll">
            <table className="tbl">
              <thead>
                <tr>
                  <th style={{ paddingLeft: 24 }}>Company</th>
                  <th>Type</th>
                  <th>CIN</th>
                  <th>Contact</th>
                  <th>Website</th>
                  <th>Submitted</th>
                  <th style={{ paddingRight: 24 }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {isLoading ? (
                  <SkeletonTableRows rows={3} cols={7} />
                ) : (
                  visible.map((v) => (
                    <tr key={v.id} className={exitingRows.has(v.id) ? 'row-exit' : undefined}>
                      <td style={{ paddingLeft: 24 }}>
                        <div style={{ fontWeight: 500, color: 'var(--text-1)' }}>{v.name}</div>
                        <div style={{ fontSize: 12, color: 'var(--text-4)' }}>{v.admin_name}</div>
                      </td>
                      <td>
                        <span
                          style={{
                            background: 'var(--bg-elevated)',
                            borderRadius: 'var(--r-sm)',
                            padding: '2px 8px',
                            fontSize: 11,
                            fontWeight: 500,
                            color: 'var(--text-2)',
                          }}
                        >
                          {v.company_type}
                        </span>
                      </td>
                      <td style={{ fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--text-3)' }}>
                        {v.cin}
                      </td>
                      <td style={{ fontSize: 13, color: 'var(--text-2)' }}>{v.admin_email}</td>
                      <td>
                        <a
                          href={v.website}
                          target="_blank"
                          rel="noreferrer"
                          style={{ fontSize: 13, color: 'var(--accent-text)', textDecoration: 'none' }}
                          onClick={(e) => e.stopPropagation()}
                        >
                          {v.website.replace(/^https?:\/\//, '')}
                        </a>
                      </td>
                      <td style={{ fontSize: 13, color: 'var(--text-3)' }}>{formatDateTime(v.created_at)}</td>
                      <td style={{ paddingRight: 24 }}>
                        <div style={{ display: 'flex', gap: 6 }}>
                          <Button
                            variant="success-ghost"
                            size="sm"
                            icon={<Check size={13} />}
                            onClick={() => setApproveTarget(v)}
                          >
                            Approve
                          </Button>
                          <Button
                            variant="danger-ghost"
                            size="sm"
                            icon={<X size={13} />}
                            onClick={() => setRejectTarget(v)}
                          >
                            Reject
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Approve confirmation */}
      <Modal
        open={!!approveTarget}
        onClose={() => setApproveTarget(null)}
        title={`Approve ${approveTarget?.name}?`}
        width={420}
        footer={
          <>
            <Button variant="secondary" onClick={() => setApproveTarget(null)}>
              Cancel
            </Button>
            <Button
              style={{ background: 'var(--success)', color: '#fff' }}
              onClick={handleApprove}
              loading={busy}
            >
              Confirm Approval
            </Button>
          </>
        }
      >
        <p style={{ fontSize: 13, color: 'var(--text-3)', lineHeight: 1.6 }}>
          This will activate the tenant, auto-provision their API key and Tenant ID, and create
          default webhook and LLM configurations. The API key is shown <strong>once</strong> on the
          next screen.
        </p>
      </Modal>

      {/* Credentials success modal */}
      <Modal open={!!creds} onClose={() => setCreds(null)} width={460} hideHeader dismissible={false}>
        {creds && (
          <div style={{ margin: -20 }}>
            <div
              style={{
                background: 'var(--success-subtle)',
                borderBottom: '1px solid rgba(34,197,94,0.3)',
                padding: '20px 24px',
                display: 'flex',
                alignItems: 'center',
                gap: 10,
              }}
            >
              <span
                style={{
                  width: 28,
                  height: 28,
                  borderRadius: '50%',
                  background: 'var(--success)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  animation: 'scaleIn 300ms cubic-bezier(0.34,1.56,0.64,1)',
                }}
              >
                <Check size={15} color="#fff" />
              </span>
              <span style={{ fontSize: 16, fontWeight: 600, color: 'var(--text-1)' }}>
                {creds.name} Approved
              </span>
            </div>

            <div style={{ padding: 24, display: 'flex', flexDirection: 'column', gap: 16 }}>
              <div>
                <div className="label-upper" style={{ marginBottom: 8 }}>
                  Tenant ID
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <span
                    style={{
                      background: 'var(--bg-base)',
                      border: '1px solid var(--border)',
                      borderRadius: 'var(--r-sm)',
                      padding: '4px 10px',
                      fontFamily: 'var(--font-mono)',
                      fontSize: 13,
                    }}
                  >
                    {creds.tenant_id}
                  </span>
                  <CopyButton value={creds.tenant_id} />
                </div>
              </div>
              <div>
                <div className="label-upper" style={{ marginBottom: 8 }}>
                  API Key — shown once
                </div>
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 8,
                    background: 'var(--warning-subtle)',
                    border: '1px solid var(--warning)',
                    borderRadius: 'var(--r-md)',
                    padding: '10px 12px',
                  }}
                >
                  <span
                    style={{
                      fontFamily: 'var(--font-mono)',
                      fontSize: 13,
                      color: 'var(--text-1)',
                      wordBreak: 'break-all',
                      flex: 1,
                    }}
                  >
                    {creds.api_key}
                  </span>
                  <CopyButton value={creds.api_key} />
                </div>
              </div>

              <div
                style={{
                  display: 'flex',
                  gap: 8,
                  alignItems: 'flex-start',
                  background: 'var(--warning-subtle)',
                  borderRadius: 'var(--r-md)',
                  padding: '10px 12px',
                  fontSize: 12,
                  color: 'var(--warning)',
                }}
              >
                <AlertTriangle size={13} style={{ flexShrink: 0, marginTop: 1 }} />
                Copy these now — the API key will not be shown again.
              </div>

              <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
                <Button
                  variant="secondary"
                  icon={<Copy size={13} />}
                  onClick={() => {
                    navigator.clipboard.writeText(
                      `Tenant ID: ${creds.tenant_id}\nAPI Key: ${creds.api_key}`,
                    )
                    toast('success', 'Credentials copied')
                  }}
                >
                  Copy All Credentials
                </Button>
                <Button onClick={() => setCreds(null)}>Done</Button>
              </div>
            </div>
          </div>
        )}
      </Modal>

      {/* Reject modal */}
      <Modal
        open={!!rejectTarget}
        onClose={() => setRejectTarget(null)}
        title={`Reject ${rejectTarget?.name}?`}
        width={420}
        footer={
          <>
            <Button variant="secondary" onClick={() => setRejectTarget(null)}>
              Cancel
            </Button>
            <Button
              variant="danger"
              onClick={handleReject}
              loading={busy}
              disabled={!rejectReason.trim()}
            >
              Confirm Rejection
            </Button>
          </>
        }
      >
        <p style={{ fontSize: 13, color: 'var(--text-3)', marginBottom: 12 }}>
          The reason is shown to the applicant on their status page.
        </p>
        <textarea
          className="input"
          style={{ minHeight: 80, width: '100%' }}
          placeholder="e.g. Unable to verify corporate registration number."
          value={rejectReason}
          onChange={(e) => setRejectReason(e.target.value)}
          autoFocus
        />
      </Modal>
    </div>
  )
}
