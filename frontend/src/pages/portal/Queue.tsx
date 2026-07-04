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

type Filter = 'ALL' | 'APPROVED' | 'NOT_APPROVED'

// Under auto-approve there is no "pending" state, and an alert that doesn't become a filed
// SAR is either rejected (manual mode) or failed to process — grouped as "Rejected / Not approved".
const FILTERS: { key: Filter; label: string }[] = [
  { key: 'ALL', label: 'All' },
  { key: 'APPROVED', label: 'Approved' },
  { key: 'NOT_APPROVED', label: 'Rejected / Not approved' },
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
        filter === 'APPROVED'
          ? a.status === 'APPROVED'
          : a.status === 'REJECTED' || a.status === 'PROCESSING_FAILED',
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

  const total = alerts?.length ?? 0
  const notApproved = alerts?.filter((a) => a.status === 'REJECTED' || a.status === 'PROCESSING_FAILED').length ?? 0

  const submitTestAlert = () => {
    submitTest.mutate('STRUCTURING', {
      onSuccess: () => toast('success', 'Test alert injected', 'It will appear here in ~8 seconds.'),
    })
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      {/* Header row */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 10 }}>
          <h1 style={{ fontSize: 20, fontWeight: 600, letterSpacing: '-0.02em' }}>Alerts</h1>
          <span style={{ fontSize: 13, color: 'var(--text-3)' }}>
            {total} alert{total === 1 ? '' : 's'}
            {notApproved > 0 ? ` · ${notApproved} not approved` : ''}
          </span>
        </div>
        {/* Dev/demo affordance only — hidden in production builds. */}
        {import.meta.env.DEV && (
          <Button size="sm" variant="secondary" icon={<Zap size={13} />} onClick={submitTestAlert} loading={submitTest.isPending}>
            Submit test alert
          </Button>
        )}
      </div>

      {/* Toolbar — segmented filters left, search + dates right */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 12,
          flexWrap: 'wrap',
        }}
      >
        <div
          style={{
            display: 'inline-flex',
            gap: 2,
            padding: 2,
            background: 'var(--bg-overlay)',
            borderRadius: 'var(--r-md)',
          }}
        >
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
          <div style={{ width: 220 }}>
            <Input
              placeholder="Search by transaction ID…"
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
            style={{ height: 32, fontSize: 12, width: 130, colorScheme: 'light' }}
            aria-label="From date"
          />
          <input
            type="date"
            className="input"
            value={toDate}
            onChange={(e) => setToDate(e.target.value)}
            style={{ height: 32, fontSize: 12, width: 130, colorScheme: 'light' }}
            aria-label="To date"
          />
        </div>
      </div>

      {/* Table — Resend-style bordered panel, hairline rows */}
      {!isLoading && filtered.length === 0 ? (
        <EmptyState
          icon={<ShieldCheckIllustration size={64} />}
          title="All clear"
          description={import.meta.env.DEV ? 'No alerts match. Submit a test alert to try the pipeline.' : 'No alerts match your filters.'}
          action={
            import.meta.env.DEV ? (
              <Button icon={<Zap size={14} />} onClick={submitTestAlert} loading={submitTest.isPending}>
                Submit test alert
              </Button>
            ) : undefined
          }
        />
      ) : (
        <div
          className="tbl-scroll"
          style={{
            border: '1px solid var(--border)',
            borderRadius: 'var(--r-lg)',
            background: 'var(--bg-surface)',
          }}
        >
          <table className="tbl tbl-clickable">
            <thead>
              <tr>
                <th style={{ paddingLeft: 20 }}>Alert ID</th>
                <th style={{ textAlign: 'right' }}>Amount</th>
                <th>Type</th>
                <th>Risk</th>
                <th>Rules</th>
                <th>Status</th>
                <th style={{ textAlign: 'right', paddingRight: 20 }}>Received</th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <SkeletonTableRows rows={6} cols={7} />
              ) : (
                filtered.map((a, i) => {
                  const isNew =
                    Date.now() - new Date(a.created_at).getTime() < NEW_THRESHOLD_MS &&
                    new Date(a.created_at).getTime() > mountTime.current - NEW_THRESHOLD_MS
                  return (
                    <tr
                      key={a.id}
                      className={isNew ? 'row-new' : undefined}
                      style={{
                        animation: `fadeInUp 240ms cubic-bezier(0.22, 1, 0.36, 1) ${Math.min(i, 12) * 25}ms both`,
                      }}
                      onClick={() => navigate(`/queue/${a.id}`)}
                    >
                      <td
                        style={{
                          paddingLeft: 20,
                          fontFamily: 'var(--font-mono)',
                          fontSize: 12.5,
                          color: 'var(--text-2)',
                        }}
                      >
                        {truncId(a.id)}
                      </td>
                      <td
                        style={{
                          textAlign: 'right',
                          fontFamily: 'var(--font-mono)',
                          fontSize: 13,
                          fontWeight: 500,
                          color: 'var(--text-1)',
                          fontVariantNumeric: 'tabular-nums',
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
                      <td>
                        <AlertStatusBadge status={a.status} />
                      </td>
                      <td
                        style={{
                          textAlign: 'right',
                          paddingRight: 20,
                          fontSize: 12.5,
                          color: 'var(--text-3)',
                          whiteSpace: 'nowrap',
                        }}
                      >
                        {timeAgo(a.created_at)}
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
