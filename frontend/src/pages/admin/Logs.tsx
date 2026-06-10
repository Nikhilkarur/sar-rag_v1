import { useMemo, useState } from 'react'
import { RefreshCw } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { listApiLogs, listCustomers } from '../../api/admin'
import { Input, Select } from '../../components/ui/Input'
import { MethodBadge, HttpStatusBadge } from '../../components/ui/Badge'
import { SkeletonTableRows } from '../../components/ui/Skeleton'
import { Toggle } from '../../components/ui/Toggle'
import { cls, formatDateTime } from '../../utils/format'

type StatusFilter = 'ALL' | '2xx' | '4xx' | '5xx'

const STATUS_FILTERS: StatusFilter[] = ['ALL', '2xx', '4xx', '5xx']

function latencyColor(ms: number): string {
  if (ms < 200) return 'var(--success)'
  if (ms <= 500) return 'var(--warning)'
  return 'var(--danger)'
}

export function Logs() {
  const [autoRefresh, setAutoRefresh] = useState(false)
  const [tenant, setTenant] = useState('ALL')
  const [endpoint, setEndpoint] = useState('')
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('ALL')
  const [fromDate, setFromDate] = useState('')
  const [toDate, setToDate] = useState('')

  const { data: logs, isLoading, isFetching } = useQuery({
    queryKey: ['api-logs'],
    queryFn: listApiLogs,
    refetchInterval: autoRefresh ? 10_000 : false,
  })
  const { data: customers } = useQuery({ queryKey: ['customers'], queryFn: listCustomers })

  const tenantOptions = [
    { value: 'ALL', label: 'All tenants' },
    ...(customers ?? []).map((c) => ({ value: c.name, label: c.name })),
  ]

  const filtered = useMemo(() => {
    let list = logs ?? []
    if (tenant !== 'ALL') list = list.filter((l) => l.tenant_name === tenant)
    if (endpoint.trim())
      list = list.filter((l) => l.endpoint.toLowerCase().includes(endpoint.trim().toLowerCase()))
    if (statusFilter !== 'ALL') {
      const range = Number(statusFilter[0]) * 100
      list = list.filter((l) => l.status_code >= range && l.status_code < range + 100)
    }
    if (fromDate) list = list.filter((l) => new Date(l.created_at) >= new Date(fromDate))
    if (toDate) list = list.filter((l) => new Date(l.created_at) <= new Date(`${toDate}T23:59:59`))
    return list
  }, [logs, tenant, endpoint, statusFilter, fromDate, toDate])

  const reset = () => {
    setTenant('ALL')
    setEndpoint('')
    setStatusFilter('ALL')
    setFromDate('')
    setToDate('')
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      {/* Filter bar */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 12,
          flexWrap: 'wrap',
        }}
      >
        <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
          <div style={{ width: 180 }}>
            <Select
              options={tenantOptions}
              value={tenant}
              onChange={(e) => setTenant(e.target.value)}
              style={{ height: 32, fontSize: 13 }}
            />
          </div>
          <div style={{ width: 200 }}>
            <Input
              placeholder="Filter endpoint..."
              value={endpoint}
              onChange={(e) => setEndpoint(e.target.value)}
              style={{ height: 32, fontSize: 13, fontFamily: 'var(--font-mono)' }}
            />
          </div>
          <div style={{ display: 'flex', gap: 4 }}>
            {STATUS_FILTERS.map((s) => (
              <button
                key={s}
                className={cls('chip', statusFilter === s && 'chip-active')}
                onClick={() => setStatusFilter(s)}
              >
                {s === 'ALL' ? 'All' : s}
              </button>
            ))}
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
          <button
            onClick={reset}
            style={{
              background: 'none',
              border: 'none',
              color: 'var(--text-3)',
              fontSize: 13,
              cursor: 'pointer',
              textDecoration: 'underline',
              textUnderlineOffset: 3,
            }}
          >
            Reset
          </button>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <RefreshCw
            size={14}
            color="var(--text-3)"
            style={isFetching ? { animation: 'spin 1s linear infinite' } : undefined}
          />
          <span style={{ fontSize: 13, color: 'var(--text-2)' }}>Auto-refresh</span>
          <Toggle checked={autoRefresh} onChange={setAutoRefresh} />
          {autoRefresh && (
            <span
              className="anim-fade-in"
              style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 12, color: 'var(--success)' }}
            >
              <span className="pulse-dot" style={{ background: 'var(--success)' }} />
              Updates every 10s
            </span>
          )}
        </div>
      </div>

      <div className="card" style={{ padding: 0 }}>
        <div className="tbl-scroll">
          <table className="tbl">
            <thead>
              <tr>
                <th style={{ paddingLeft: 24 }}>Timestamp</th>
                <th>Tenant</th>
                <th>Method</th>
                <th>Endpoint</th>
                <th>Status</th>
                <th style={{ paddingRight: 24, textAlign: 'right' }}>Latency</th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <SkeletonTableRows rows={8} cols={6} />
              ) : filtered.length === 0 ? (
                <tr>
                  <td colSpan={6} style={{ textAlign: 'center', color: 'var(--text-4)', height: 80 }}>
                    No log entries match the current filters.
                  </td>
                </tr>
              ) : (
                filtered.map((log) => (
                  <tr key={log.id}>
                    <td style={{ paddingLeft: 24, fontSize: 13, color: 'var(--text-3)', fontFamily: 'var(--font-mono)' }}>
                      {formatDateTime(log.created_at)}
                    </td>
                    <td style={{ fontSize: 13, color: 'var(--text-2)' }}>{log.tenant_name}</td>
                    <td>
                      <MethodBadge method={log.method} />
                    </td>
                    <td style={{ fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--text-2)' }}>
                      {log.endpoint}
                    </td>
                    <td>
                      <HttpStatusBadge code={log.status_code} />
                    </td>
                    <td
                      style={{
                        paddingRight: 24,
                        textAlign: 'right',
                        fontFamily: 'var(--font-mono)',
                        fontSize: 13,
                        color: latencyColor(log.latency_ms),
                      }}
                    >
                      {log.latency_ms}ms
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
