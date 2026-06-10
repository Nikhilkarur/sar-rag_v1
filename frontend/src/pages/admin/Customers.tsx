import React, { useMemo, useState } from 'react'
import { Ban, CheckCircle2, ChevronRight, MoreHorizontal, Search } from 'lucide-react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { listCustomers, reinstateTenant, suspendTenant } from '../../api/admin'
import { Button } from '../../components/ui/Button'
import { Modal } from '../../components/ui/Modal'
import { Input } from '../../components/ui/Input'
import { TenantStatusBadge } from '../../components/ui/Badge'
import { SkeletonTableRows } from '../../components/ui/Skeleton'
import { useToast } from '../../components/ui/Toast'
import { cls, formatDate, timeAgo } from '../../utils/format'
import type { CustomerItem, TenantStatus } from '../../types'

type Filter = 'ALL' | TenantStatus

const FILTERS: { key: Filter; label: string }[] = [
  { key: 'ALL', label: 'All' },
  { key: 'ACTIVE', label: 'Active' },
  { key: 'PENDING_VERIFICATION', label: 'Pending' },
  { key: 'SUSPENDED', label: 'Suspended' },
  { key: 'REJECTED', label: 'Rejected' },
]

export function Customers() {
  const { data: customers, isLoading } = useQuery({ queryKey: ['customers'], queryFn: listCustomers })
  const qc = useQueryClient()
  const { toast } = useToast()

  const [filter, setFilter] = useState<Filter>('ALL')
  const [search, setSearch] = useState('')
  const [menuFor, setMenuFor] = useState<string | null>(null)
  const [expanded, setExpanded] = useState<string | null>(null)
  const [suspendTarget, setSuspendTarget] = useState<CustomerItem | null>(null)
  const [busy, setBusy] = useState(false)

  const filtered = useMemo(() => {
    let list = customers ?? []
    if (filter !== 'ALL') list = list.filter((c) => c.status === filter)
    if (search.trim()) {
      const q = search.trim().toLowerCase()
      list = list.filter(
        (c) => c.name.toLowerCase().includes(q) || c.tenant_id_public.toLowerCase().includes(q),
      )
    }
    return list
  }, [customers, filter, search])

  const handleSuspend = async () => {
    if (!suspendTarget) return
    setBusy(true)
    try {
      await suspendTenant(suspendTarget.id)
      qc.invalidateQueries({ queryKey: ['customers'] })
      toast('warning', 'Tenant suspended', `${suspendTarget.name}'s API key is now inactive.`)
      setSuspendTarget(null)
    } finally {
      setBusy(false)
    }
  }

  const handleReinstate = async (c: CustomerItem) => {
    setMenuFor(null)
    await reinstateTenant(c.id)
    qc.invalidateQueries({ queryKey: ['customers'] })
    toast('success', 'Tenant reinstated', `${c.name}'s API key is active again.`)
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }} onClick={() => setMenuFor(null)}>
      {/* Filter bar */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 16, flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', gap: 4 }}>
          {FILTERS.map((f) => (
            <button
              key={f.key}
              className={cls('chip', filter === f.key && 'chip-active')}
              onClick={() => setFilter(f.key)}
            >
              {f.label}
            </button>
          ))}
        </div>
        <div style={{ width: 220 }}>
          <Input
            placeholder="Search tenants..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            leftIcon={<Search size={14} />}
            style={{ height: 32, fontSize: 13 }}
          />
        </div>
      </div>

      <div className="card" style={{ padding: 0, overflow: 'visible' }}>
        <div className="tbl-scroll" style={{ overflow: 'visible' }}>
          <table className="tbl">
            <thead>
              <tr>
                <th style={{ paddingLeft: 24 }}>Tenant</th>
                <th>ID</th>
                <th>Type</th>
                <th>Status</th>
                <th style={{ textAlign: 'right' }}>Alerts</th>
                <th style={{ textAlign: 'right' }}>SARs</th>
                <th>Joined</th>
                <th style={{ paddingRight: 24, width: 50 }}></th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <SkeletonTableRows rows={4} cols={8} />
              ) : (
                filtered.map((c) => (
                  <React.Fragment key={c.id}>
                    <tr
                      onMouseEnter={(e) => {
                        const btn = e.currentTarget.querySelector<HTMLElement>('.kebab')
                        if (btn) btn.style.opacity = '1'
                      }}
                      onMouseLeave={(e) => {
                        const btn = e.currentTarget.querySelector<HTMLElement>('.kebab')
                        if (btn && menuFor !== c.id) btn.style.opacity = '0'
                      }}
                    >
                      <td style={{ paddingLeft: 24, fontWeight: 500, color: 'var(--text-1)' }}>{c.name}</td>
                      <td style={{ fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--text-3)' }}>
                        {c.tenant_id_public}
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
                          {c.company_type}
                        </span>
                      </td>
                      <td>
                        <TenantStatusBadge status={c.status} />
                      </td>
                      <td style={{ textAlign: 'right', fontFamily: 'var(--font-mono)', fontSize: 13 }}>
                        {c.total_alerts}
                      </td>
                      <td style={{ textAlign: 'right', fontFamily: 'var(--font-mono)', fontSize: 13 }}>
                        {c.approved_sars}
                      </td>
                      <td style={{ fontSize: 13, color: 'var(--text-3)' }}>{formatDate(c.joined_at)}</td>
                      <td style={{ paddingRight: 24, position: 'relative' }}>
                        <button
                          className="kebab"
                          onClick={(e) => {
                            e.stopPropagation()
                            setMenuFor(menuFor === c.id ? null : c.id)
                          }}
                          style={{
                            opacity: menuFor === c.id ? 1 : 0,
                            transition: 'opacity var(--t-fast)',
                            background: 'none',
                            border: 'none',
                            color: 'var(--text-3)',
                            cursor: 'pointer',
                            padding: 6,
                            borderRadius: 'var(--r-sm)',
                            display: 'flex',
                          }}
                        >
                          <MoreHorizontal size={16} />
                        </button>
                        {menuFor === c.id && (
                          <div
                            className="anim-scale-in"
                            onClick={(e) => e.stopPropagation()}
                            style={{
                              position: 'absolute',
                              right: 24,
                              top: 40,
                              zIndex: 50,
                              background: 'var(--bg-overlay)',
                              border: '1px solid var(--border)',
                              boxShadow: 'var(--shadow-lg)',
                              borderRadius: 'var(--r-md)',
                              minWidth: 160,
                              overflow: 'hidden',
                              padding: 4,
                            }}
                          >
                            {c.status !== 'SUSPENDED' ? (
                              <MenuItem
                                icon={<Ban size={14} />}
                                label="Suspend"
                                color="var(--warning)"
                                onClick={() => {
                                  setMenuFor(null)
                                  setSuspendTarget(c)
                                }}
                              />
                            ) : (
                              <MenuItem
                                icon={<CheckCircle2 size={14} />}
                                label="Reinstate"
                                color="var(--success)"
                                onClick={() => handleReinstate(c)}
                              />
                            )}
                            <MenuItem
                              icon={<ChevronRight size={14} />}
                              label="View Details"
                              color="var(--text-2)"
                              onClick={() => {
                                setMenuFor(null)
                                setExpanded(expanded === c.id ? null : c.id)
                              }}
                            />
                          </div>
                        )}
                      </td>
                    </tr>
                    {expanded === c.id && (
                      <tr>
                        <td colSpan={8} style={{ padding: 0, height: 'auto' }}>
                          <div
                            className="anim-slide-top"
                            style={{
                              padding: '20px 24px',
                              background: 'var(--bg-base)',
                              display: 'grid',
                              gridTemplateColumns: '1fr 1fr',
                              gap: '12px 32px',
                            }}
                          >
                            <DetailRow label="CIN" value={c.cin} mono />
                            <DetailRow label="Website" value={c.website} />
                            <DetailRow label="Admin Email" value={c.admin_email} />
                            <DetailRow label="Last Active" value={timeAgo(c.last_active_at)} />
                          </div>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Suspend confirmation */}
      <Modal
        open={!!suspendTarget}
        onClose={() => setSuspendTarget(null)}
        title={`Suspend ${suspendTarget?.name}?`}
        width={420}
        footer={
          <>
            <Button variant="secondary" onClick={() => setSuspendTarget(null)}>
              Cancel
            </Button>
            <Button variant="danger" onClick={handleSuspend} loading={busy}>
              Suspend
            </Button>
          </>
        }
      >
        <p style={{ fontSize: 13, color: 'var(--text-3)', lineHeight: 1.6 }}>
          Their API key flips to inactive immediately and all ingestion requests will be rejected
          with <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12 }}>TENANT_SUSPENDED</span>.
          Data is preserved — you can reinstate at any time.
        </p>
      </Modal>
    </div>
  )
}

function MenuItem({
  icon,
  label,
  color,
  onClick,
}: {
  icon: React.ReactNode
  label: string
  color: string
  onClick: () => void
}) {
  return (
    <button
      onClick={onClick}
      style={{
        width: '100%',
        display: 'flex',
        alignItems: 'center',
        gap: 10,
        padding: '8px 12px',
        background: 'transparent',
        border: 'none',
        borderRadius: 'var(--r-sm)',
        color,
        fontSize: 13,
        cursor: 'pointer',
        transition: 'background var(--t-fast)',
        textAlign: 'left',
      }}
      onMouseEnter={(e) => (e.currentTarget.style.background = 'var(--bg-elevated)')}
      onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
    >
      {icon}
      {label}
    </button>
  )
}

function DetailRow({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
      <span className="label-upper" style={{ minWidth: 110 }}>
        {label}
      </span>
      <span
        style={{
          fontSize: 13,
          color: 'var(--text-1)',
          fontFamily: mono ? 'var(--font-mono)' : 'var(--font-sans)',
        }}
      >
        {value}
      </span>
    </div>
  )
}
