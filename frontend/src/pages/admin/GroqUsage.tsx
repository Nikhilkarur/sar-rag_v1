import { DollarSign, Hash, Zap } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { getGroqUsage } from '../../api/admin'
import { useCountUp } from '../../hooks/useCountUp'
import { SkeletonStatCard, SkeletonCard, SkeletonTableRows } from '../../components/ui/Skeleton'
import { formatNumber, timeAgo } from '../../utils/format'

function ChartTooltip({ active, payload, label }: { active?: boolean; payload?: { value: number }[]; label?: string }) {
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
      <div style={{ color: 'var(--text-1)', fontWeight: 600, marginTop: 2 }}>
        {formatNumber(payload[0].value)} tokens
      </div>
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

export function GroqUsage() {
  const { data, isLoading } = useQuery({ queryKey: ['groq-usage'], queryFn: getGroqUsage })

  const allTime = useCountUp(data?.total_tokens_all_time ?? 0)
  const thisMonth = useCountUp(data?.total_tokens_this_month ?? 0)
  const cost = useCountUp(data?.estimated_cost_usd_this_month ?? 0, 1200, 2)

  const top5 = (data?.per_tenant ?? []).slice(0, 5).map((t) => ({
    name: t.tenant_name.length > 18 ? `${t.tenant_name.slice(0, 17)}…` : t.tenant_name,
    tokens: t.tokens_this_month,
  }))

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      {/* Stat cards */}
      <div className="stat-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16 }}>
        {isLoading ? (
          <>
            <SkeletonStatCard />
            <SkeletonStatCard />
            <SkeletonStatCard />
          </>
        ) : (
          <>
            <Stat
              index={0}
              icon={<Zap size={15} color="var(--accent-text)" />}
              iconBg="rgba(6,78,59,0.10)"
              value={allTime}
              label="Total Tokens — All Time"
            />
            <Stat
              index={1}
              icon={<Hash size={15} color="var(--info)" />}
              iconBg="rgba(14,116,144,0.12)"
              value={thisMonth}
              label="Tokens This Month"
            />
            <Stat
              index={2}
              icon={<DollarSign size={15} color="var(--success)" />}
              iconBg="rgba(6,78,59,0.12)"
              value={`$${cost}`}
              label="Est. Cost This Month"
            />
          </>
        )}
      </div>

      {/* Top-5 bar chart */}
      {isLoading ? (
        <SkeletonCard height={260} />
      ) : (
        <div className="card" style={{ animation: 'fadeInUp 300ms ease-out 240ms both' }}>
          <h3 style={{ fontSize: 16, fontWeight: 600, letterSpacing: '-0.01em', marginBottom: 16 }}>
            Top Tenants by Token Usage — This Month
          </h3>
          <div style={{ height: Math.max(180, top5.length * 48) }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={top5} layout="vertical" margin={{ top: 0, right: 24, bottom: 0, left: 40 }}>
                <CartesianGrid stroke="var(--border-subtle)" strokeDasharray="3 3" horizontal={false} />
                <XAxis
                  type="number"
                  tick={{ fill: 'var(--text-4)', fontSize: 11 }}
                  axisLine={false}
                  tickLine={false}
                  tickFormatter={(v: number) => `${Math.round(v / 1000)}K`}
                />
                <YAxis
                  type="category"
                  dataKey="name"
                  width={120}
                  tick={{ fill: 'var(--text-3)', fontSize: 12 }}
                  axisLine={false}
                  tickLine={false}
                />
                <Tooltip content={<ChartTooltip />} cursor={{ fill: 'var(--bg-elevated)' }} />
                <Bar
                  dataKey="tokens"
                  fill="var(--accent)"
                  radius={[0, 4, 4, 0]}
                  barSize={18}
                  isAnimationActive
                  animationDuration={900}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* Per-tenant table */}
      <div className="card" style={{ padding: 0, animation: 'fadeInUp 300ms ease-out 320ms both' }}>
        <div style={{ padding: '20px 24px 8px' }}>
          <h3 style={{ fontSize: 16, fontWeight: 600, letterSpacing: '-0.01em' }}>Per-Tenant Breakdown</h3>
        </div>
        <div className="tbl-scroll">
          <table className="tbl">
            <thead>
              <tr>
                <th style={{ paddingLeft: 24 }}>Tenant</th>
                <th style={{ textAlign: 'right' }}>Tokens This Month</th>
                <th style={{ textAlign: 'right' }}>Requests</th>
                <th style={{ textAlign: 'right' }}>Est. Cost</th>
                <th style={{ paddingRight: 24 }}>Last Active</th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <SkeletonTableRows rows={4} cols={5} />
              ) : (
                (data?.per_tenant ?? []).map((t) => (
                  <tr key={t.tenant_id}>
                    <td style={{ paddingLeft: 24, fontWeight: 500, color: 'var(--text-1)' }}>
                      {t.tenant_name}
                    </td>
                    <td style={{ textAlign: 'right', fontFamily: 'var(--font-mono)', fontSize: 13 }}>
                      {formatNumber(t.tokens_this_month)}
                    </td>
                    <td style={{ textAlign: 'right', fontFamily: 'var(--font-mono)', fontSize: 13, color: 'var(--text-2)' }}>
                      {t.total_requests}
                    </td>
                    <td style={{ textAlign: 'right', fontFamily: 'var(--font-mono)', fontSize: 13, color: 'var(--success)' }}>
                      ${t.est_cost.toFixed(2)}
                    </td>
                    <td style={{ paddingRight: 24, fontSize: 13, color: 'var(--text-3)' }}>
                      {timeAgo(t.last_active)}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
        <div
          style={{
            padding: '12px 24px',
            borderTop: '1px solid var(--border-subtle)',
            fontSize: 12,
            color: 'var(--text-4)',
          }}
        >
          Costs estimated at $0.0015/1K input tokens, $0.002/1K output tokens (Groq pricing). Actual
          billing may vary.
        </div>
      </div>
    </div>
  )
}
