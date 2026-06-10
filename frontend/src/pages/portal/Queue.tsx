import { useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Search, Zap } from 'lucide-react'
import { useAlerts, useSubmitTestAlert } from '../../hooks/useAlerts'
import { useToast } from '../../components/ui/Toast'
import { Button } from '../../components/ui/Button'
import { Input } from '../../components/ui/Input'
import { AlertStatusBadge, RiskScoreCell, RulePills } from '../../components/ui/Badge'
import { EmptyState, ShieldCheckIllustration } from '../../components/ui/EmptyState'
import { SkeletonTableRows } from '../../components/ui/Skeleton'
import { cls, formatINR, timeAgo, truncId } from '../../utils/format'
import type { AlertStatus } from '../../types'

type Filter = 'ALL' | 'PENDING_REVIEW' | 'APPROVED' | 'REJECTED'

const FILTERS: { key: Filter; label: string }[] = [
  { key: 'ALL', label: 'All' },
  { key: 'PENDING_REVIEW', label: 'Pending Review' },
  { key: 'APPROVED', label: 'Approved' },
  { key: 'REJECTED', label: 'Rejected' },
]

const NEW_THRESHOLD_MS = 30_000

export function Queue() {
  const navigate = useNavigate()
  const { toast } = useToast()
  const { data: alerts, isLoading } = useAlerts(true)
  const [filter, setFilter] = useState<Filter>('ALL')
  const [search, setSearch] = useState('')
  const [fromDate, setFromDate] = useState('')
  const [toDate, setToDate] = useState('')
  const submitTest = useSubmitTestAlert()
  const mountTime = useRef(Date.now())

  const filtered = useMemo(() => {
    let list = alerts ?? []
    if (filter !== 'ALL') {
      list = list.filter((a) =>
        filter === 'PENDING_REVIEW'
          ? a.status === 'PENDING_REVIEW' || a.status === 'PROCESSING'
          : a.status === (filter as AlertStatus),
      )
    }
    if (search.trim()) {
      const q = search.trim().toLowerCase()
      list = list.filter((a) => a.transaction_id.toLowerCase().includes(q))
    }
    if (fromDate) list = list.filter((a) => new Date(a.created_at) >= new Date(fromDate))
    if (toDate) list = list.filter((a) => new Date(a.created_at) <= new Date(`${toDate}T23:59:59`))
    return list
  }, [alerts, filter, search, fromDate, toDate])

  const pendingCount = alerts?.filter((a) => a.status === 'PENDING_REVIEW').length ?? 0

  const submitTestAlert = () => {
    submitTest.mutate('STRUCTURING', {
      onSuccess: () => toast('success', 'Test alert injected', 'It will appear here in ~8 seconds.'),
    })
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 0 }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16 }}>
        <h1 style={{ fontSize: 24, fontWeight: 600, letterSpacing: '-0.02em' }}>Review Queue</h1>
        {pendingCount > 0 && (
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
            {pendingCount} pending
          </span>
        )}
      </div>

      {/* Filter bar */}
      <div
        style={{
          position: 'sticky',
          top: 64,
          zIndex: 30,
          height: 56,
          background: 'var(--bg-base)',
          borderBottom: '1px solid var(--border-subtle)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 16,
          flexWrap: 'wrap',
        }}
      >
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
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <div style={{ width: 200 }}>
            <Input
              placeholder="Search by Transaction ID..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              onKeyDown={(e) => e.key === 'Escape' && setSearch('')}
              leftIcon={<Search size={14} />}
              style={{ height: 32, fontSize: 13 }}
            />
          </div>
          <input
            type="date"
            className="input"
            value={fromDate}
            onChange={(e) => setFromDate(e.target.value)}
            style={{ height: 32, fontSize: 12, width: 130, colorScheme: 'dark' }}
            aria-label="From date"
          />
          <input
            type="date"
            className="input"
            value={toDate}
            onChange={(e) => setToDate(e.target.value)}
            style={{ height: 32, fontSize: 12, width: 130, colorScheme: 'dark' }}
            aria-label="To date"
          />
        </div>
      </div>

      {/* Table */}
      {!isLoading && filtered.length === 0 ? (
        <EmptyState
          icon={<ShieldCheckIllustration size={64} />}
          title="All Clear"
          description="No pending alerts. Submit a test alert to try the pipeline."
          action={
            <Button icon={<Zap size={14} />} onClick={submitTestAlert} loading={submitTest.isPending}>
              Submit Test Alert
            </Button>
          }
        />
      ) : (
        <div className="tbl-scroll">
          <table className="tbl tbl-clickable">
            <thead>
              <tr>
                <th>Alert ID</th>
                <th style={{ textAlign: 'right' }}>Amount</th>
                <th>Type</th>
                <th>Risk Score</th>
                <th>Rules Triggered</th>
                <th>Received</th>
                <th>Status</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <SkeletonTableRows rows={6} cols={8} />
              ) : (
                filtered.map((a) => {
                  const isNew =
                    Date.now() - new Date(a.created_at).getTime() < NEW_THRESHOLD_MS &&
                    new Date(a.created_at).getTime() > mountTime.current - NEW_THRESHOLD_MS
                  return (
                    <tr
                      key={a.id}
                      className={isNew ? 'row-new' : undefined}
                      onClick={() => navigate(`/queue/${a.id}`)}
                      onMouseEnter={(e) => {
                        const btn = e.currentTarget.querySelector<HTMLElement>('.row-review-btn')
                        if (btn) btn.style.opacity = '1'
                      }}
                      onMouseLeave={(e) => {
                        const btn = e.currentTarget.querySelector<HTMLElement>('.row-review-btn')
                        if (btn) btn.style.opacity = '0'
                      }}
                    >
                      <td style={{ fontFamily: 'var(--font-mono)', fontSize: 13, color: 'var(--text-3)' }}>
                        {truncId(a.id)}
                      </td>
                      <td
                        style={{
                          textAlign: 'right',
                          fontFamily: 'var(--font-mono)',
                          fontSize: 14,
                          fontWeight: 500,
                          color: 'var(--text-1)',
                        }}
                      >
                        {formatINR(a.transaction_amount)}
                      </td>
                      <td style={{ fontSize: 13, color: 'var(--text-2)' }}>
                        {a.transaction_type.replace(/_/g, ' ')}
                      </td>
                      <td>
                        <RiskScoreCell score={a.risk_score} />
                      </td>
                      <td>
                        <RulePills rules={a.triggered_rules} />
                      </td>
                      <td style={{ fontSize: 13, color: 'var(--text-3)' }}>{timeAgo(a.created_at)}</td>
                      <td>
                        <AlertStatusBadge status={a.status} />
                      </td>
                      <td style={{ width: 80 }}>
                        <span className="row-review-btn" style={{ opacity: 0, transition: 'opacity var(--t-fast)' }}>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={(e) => {
                              e.stopPropagation()
                              navigate(`/queue/${a.id}`)
                            }}
                          >
                            Review
                          </Button>
                        </span>
                      </td>
                    </tr>
                  )
                })
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
