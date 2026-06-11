import { CheckCircle2, Download, Inbox, ShieldCheck, Timer } from 'lucide-react'
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { useApprovedSars, useUsage } from '../../hooks/useTenant'
import { useCountUp } from '../../hooks/useCountUp'
import { useToast } from '../../components/ui/Toast'
import { Button } from '../../components/ui/Button'
import { SkeletonStatCard, SkeletonCard, SkeletonTableRows } from '../../components/ui/Skeleton'
import { formatINR, formatDateTime } from '../../utils/format'

function ChartTooltip({ active, payload, label }: { active?: boolean; payload?: { value: number; name: string }[]; label?: string }) {
  if (!active || !payload?.length) return null
  return (
    <div
      style={{
        background: 'var(--bg-overlay)',
        border: '1px solid var(--border)',
        borderRadius: 'var(--r-md)',
        padding: '8px 12px',
        fontSize: 12,
        boxShadow: 'var(--shadow-md)',
      }}
    >
      <div style={{ color: 'var(--text-3)' }}>{label}</div>
      <div style={{ color: 'var(--text-1)', fontWeight: 600, marginTop: 2 }}>{payload[0].value}</div>
    </div>
  )
}

function Stat({
  icon,
  iconBg,
  value,
  label,
  index,
}: {
  icon: React.ReactNode
  iconBg: string
  value: string
  label: string
  index: number
}) {
  return (
    <div className="stat-card" style={{ animation: `fadeInUp 300ms ease-out ${index * 80}ms both` }}>
      <div
        style={{
          width: 32,
          height: 32,
          borderRadius: '50%',
          background: iconBg,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        {icon}
      </div>
      <div style={{ fontSize: 28, fontWeight: 700, marginTop: 12, letterSpacing: '-0.02em', fontVariantNumeric: 'tabular-nums' }}>
        {value}
      </div>
      <div className="label-upper" style={{ marginTop: 6 }}>
        {label}
      </div>
    </div>
  )
}

export function Usage() {
  const { data: usage, isLoading } = useUsage()
  const { data: sars, isLoading: sarsLoading } = useApprovedSars()
  const { toast } = useToast()

  const alerts = useCountUp(usage?.alerts_ingested ?? 0)
  const approved = useCountUp(usage?.sars_approved ?? 0)
  const cleared = useCountUp(usage?.false_positives_cleared ?? 0)
  const avgTime = useCountUp(usage?.avg_review_time_minutes ?? 0, 1200, 1)

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      <div className="stat-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16 }}>
        {isLoading ? (
          <>
            <SkeletonStatCard />
            <SkeletonStatCard />
            <SkeletonStatCard />
            <SkeletonStatCard />
          </>
        ) : (
          <>
            <Stat index={0} icon={<Inbox size={15} color="var(--accent-text)" />} iconBg="rgba(6,78,59,0.10)" value={alerts} label="Alerts This Month" />
            <Stat index={1} icon={<CheckCircle2 size={15} color="var(--success)" />} iconBg="rgba(6,78,59,0.10)" value={approved} label="SARs Approved" />
            <Stat index={2} icon={<ShieldCheck size={15} color="var(--info)" />} iconBg="rgba(14,116,144,0.10)" value={cleared} label="False Positives Cleared" />
            <Stat index={3} icon={<Timer size={15} color="var(--warning)" />} iconBg="rgba(160,116,26,0.10)" value={`${avgTime} min`} label="Avg. Review Time" />
          </>
        )}
      </div>

      {/* Charts */}
      <div className="chart-grid" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
        {isLoading ? (
          <>
            <SkeletonCard height={240} />
            <SkeletonCard height={240} />
          </>
        ) : (
          <>
            <div className="card" style={{ animation: 'fadeInUp 300ms ease-out 240ms both' }}>
              <h3 style={{ fontSize: 16, fontWeight: 600, letterSpacing: '-0.01em', marginBottom: 16 }}>
                Monthly SAR Approvals
              </h3>
              <div style={{ height: 200 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={usage?.monthly_sars ?? []} margin={{ top: 4, right: 8, bottom: 0, left: -24 }}>
                    <CartesianGrid stroke="var(--border-subtle)" strokeDasharray="3 3" vertical={false} />
                    <XAxis dataKey="month" tick={{ fill: 'var(--text-4)', fontSize: 11 }} axisLine={false} tickLine={false} />
                    <YAxis tick={{ fill: 'var(--text-4)', fontSize: 11 }} axisLine={false} tickLine={false} allowDecimals={false} />
                    <Tooltip content={<ChartTooltip />} cursor={{ fill: 'var(--bg-elevated)' }} />
                    <Bar
                      dataKey="sars"
                      fill="var(--accent)"
                      radius={[4, 4, 0, 0]}
                      isAnimationActive
                      animationDuration={900}
                    />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="card" style={{ animation: 'fadeInUp 300ms ease-out 320ms both' }}>
              <h3 style={{ fontSize: 16, fontWeight: 600, letterSpacing: '-0.01em', marginBottom: 16 }}>
                Daily Alert Volume
              </h3>
              <div style={{ height: 200 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={usage?.daily_breakdown ?? []} margin={{ top: 4, right: 8, bottom: 0, left: -24 }}>
                    <defs>
                      <linearGradient id="alertGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="var(--accent)" stopOpacity={0.2} />
                        <stop offset="100%" stopColor="var(--accent)" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid stroke="var(--border-subtle)" strokeDasharray="3 3" vertical={false} />
                    <XAxis
                      dataKey="date"
                      tick={{ fill: 'var(--text-4)', fontSize: 11 }}
                      axisLine={false}
                      tickLine={false}
                      interval="preserveStartEnd"
                    />
                    <YAxis tick={{ fill: 'var(--text-4)', fontSize: 11 }} axisLine={false} tickLine={false} allowDecimals={false} />
                    <Tooltip content={<ChartTooltip />} cursor={{ stroke: 'var(--border)' }} />
                    <Area
                      type="monotone"
                      dataKey="alerts"
                      stroke="var(--accent)"
                      strokeWidth={2}
                      fill="url(#alertGrad)"
                      dot={false}
                      isAnimationActive
                      animationDuration={1000}
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>
          </>
        )}
      </div>

      {/* Recent SARs */}
      <div className="card" style={{ padding: 0, animation: 'fadeInUp 300ms ease-out 400ms both' }}>
        <div style={{ padding: '20px 24px 12px' }}>
          <h3 style={{ fontSize: 16, fontWeight: 600, letterSpacing: '-0.01em' }}>Recent Approved SARs</h3>
        </div>
        <div className="tbl-scroll">
          <table className="tbl">
            <thead>
              <tr>
                <th style={{ paddingLeft: 24 }}>SAR ID</th>
                <th>Transaction</th>
                <th style={{ textAlign: 'right' }}>Amount</th>
                <th>Approved By</th>
                <th>Approved At</th>
                <th style={{ paddingRight: 24 }}></th>
              </tr>
            </thead>
            <tbody>
              {sarsLoading ? (
                <SkeletonTableRows rows={5} cols={6} />
              ) : (
                (sars ?? []).map((s) => (
                  <tr key={s.sar_id}>
                    <td style={{ paddingLeft: 24, fontFamily: 'var(--font-mono)', fontSize: 13, color: 'var(--text-3)' }}>
                      {s.sar_id}
                    </td>
                    <td style={{ fontFamily: 'var(--font-mono)', fontSize: 13, color: 'var(--text-2)' }}>
                      {s.transaction_id}
                    </td>
                    <td style={{ textAlign: 'right', fontFamily: 'var(--font-mono)', fontWeight: 500 }}>
                      {formatINR(s.amount)}
                    </td>
                    <td style={{ fontSize: 13, color: 'var(--text-2)' }}>{s.approved_by}</td>
                    <td style={{ fontSize: 13, color: 'var(--text-3)' }}>{formatDateTime(s.approved_at)}</td>
                    <td style={{ paddingRight: 24, textAlign: 'right' }}>
                      <Button
                        variant="secondary"
                        size="sm"
                        icon={<Download size={12} />}
                        onClick={() =>
                          toast('info', 'PDF download', 'PDF generation is handled by the backend — available after integration.')
                        }
                      >
                        PDF
                      </Button>
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
