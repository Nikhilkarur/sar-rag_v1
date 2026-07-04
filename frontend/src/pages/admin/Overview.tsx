import type { CSSProperties, ReactNode } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  Activity,
  AlertTriangle,
  Building2,
  FileCheck2,
  ShieldAlert,
  Upload,
  Zap,
} from 'lucide-react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { getPlatformOverview } from '../../api/admin'
import { useCountUp } from '../../hooks/useCountUp'
import { SkeletonStatCard, SkeletonCard } from '../../components/ui/Skeleton'
import { formatNumber } from '../../utils/format'

/* Colorful palette — mirrors the landing "Usage & reports" visual */
const OUTCOME = { filed: '#ec4899', review: '#6366f1', cleared: '#10b981', failed: '#f59e0b' }
const TRAFFIC = { ok: '#10b981', client_err: '#f59e0b', server_err: '#ef4444' }
const DONUT = ['#ec4899', '#6366f1', '#10b981', '#f59e0b', '#8b5cf6', '#06b6d4', '#ef4444', '#84cc16']

function ChartCard({ title, subtitle, children, delay = 0, style }: { title: string; subtitle?: string; children: ReactNode; delay?: number; style?: CSSProperties }) {
  return (
    <div className="card" style={{ animation: `fadeInUp 300ms ease-out ${delay}ms both`, ...style }}>
      <div style={{ marginBottom: 16 }}>
        <h3 style={{ fontSize: 15, fontWeight: 600, letterSpacing: '-0.01em' }}>{title}</h3>
        {subtitle && <p style={{ fontSize: 12.5, color: 'var(--text-3)', marginTop: 2 }}>{subtitle}</p>}
      </div>
      {children}
    </div>
  )
}

function StackTooltip({ active, payload, label }: { active?: boolean; payload?: { name: string; value: number; color: string }[]; label?: string }) {
  if (!active || !payload?.length) return null
  return (
    <div style={{ background: 'var(--bg-overlay)', border: '1px solid var(--border)', borderRadius: 'var(--r-md)', padding: '8px 12px', fontSize: 12, boxShadow: 'var(--shadow-md)' }}>
      <div style={{ color: 'var(--text-3)', marginBottom: 4 }}>{label}</div>
      {payload.map((p) => (
        <div key={p.name} style={{ display: 'flex', alignItems: 'center', gap: 6, color: 'var(--text-1)' }}>
          <span style={{ width: 8, height: 8, borderRadius: 2, background: p.color }} />
          <span style={{ textTransform: 'capitalize' }}>{p.name}</span>
          <b style={{ marginLeft: 'auto', fontVariantNumeric: 'tabular-nums' }}>{p.value}</b>
        </div>
      ))}
    </div>
  )
}

/** Clean typographic KPI card — colored inline icon, no sticker tile. */
function Kpi({ icon, color, value, label, sub, index }: { icon: ReactNode; color: string; value: string; label: string; sub?: string; index: number }) {
  return (
    <div className="stat-card" style={{ padding: '18px 20px', animation: `fadeInUp 240ms ease-out ${index * 50}ms both` }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 7, fontSize: 12.5, color: 'var(--text-3)' }}>
        <span style={{ display: 'inline-flex', color }}>{icon}</span>
        {label}
      </div>
      <div style={{ fontSize: 25, fontWeight: 600, marginTop: 10, letterSpacing: '-0.02em', fontVariantNumeric: 'tabular-nums' }}>{value}</div>
      {sub && <div style={{ fontSize: 12, color: 'var(--text-4)', marginTop: 3 }}>{sub}</div>}
    </div>
  )
}

export function Overview() {
  const { data, isLoading } = useQuery({ queryKey: ['platform-overview'], queryFn: getPlatformOverview, refetchInterval: 30_000 })
  const k = data?.kpis

  const alerts = useCountUp(k?.alerts_this_month ?? 0)
  const sars = useCountUp(k?.sars_this_month ?? 0)
  const ingests = useCountUp(k?.ingest_requests_7d ?? 0)

  const typologyTotal = (data?.typology ?? []).reduce((s, t) => s + t.count, 0)

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      {/* KPI row */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 16 }}>
        {isLoading || !k ? (
          <>
            <SkeletonStatCard />
            <SkeletonStatCard />
            <SkeletonStatCard />
            <SkeletonStatCard />
            <SkeletonStatCard />
          </>
        ) : (
          <>
            <Kpi index={0} icon={<Building2 size={14} />} color="#6366f1" value={String(k.tenants_active)} label="Active tenants" sub={`${k.tenants_pending} pending · ${k.tenants_suspended} suspended`} />
            <Kpi index={1} icon={<Activity size={14} />} color="#8b5cf6" value={alerts} label="Alerts this month" sub={`${formatNumber(k.total_alerts)} all time`} />
            <Kpi index={2} icon={<FileCheck2 size={14} />} color="#ec4899" value={sars} label="SARs filed this month" sub={`${formatNumber(k.total_sars)} all time`} />
            <Kpi index={3} icon={<Zap size={14} />} color="#10b981" value={formatNumber(k.tokens_this_month)} label="LLM tokens this month" sub={`${k.sars_this_month} SARs this month · free-tier keys`} />
            <Kpi index={4} icon={<Upload size={14} />} color="#f59e0b" value={ingests} label="Ingestion API · 7d" sub="alerts received via API" />
          </>
        )}
      </div>

      {/* Alert outcomes + typology mix */}
      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1.6fr) minmax(0, 1fr)', gap: 16 }}>
        {isLoading ? (
          <SkeletonCard height={300} />
        ) : (
          <ChartCard title="Alert outcomes" subtitle="Filed · in review · cleared (no SAR needed) · failed — last 6 months" delay={200}>
            <div style={{ display: 'flex', gap: 16, marginBottom: 12, flexWrap: 'wrap' }}>
              <Legend color={OUTCOME.filed} label="Filed" />
              <Legend color={OUTCOME.review} label="In review" />
              <Legend color={OUTCOME.cleared} label="Cleared · no SAR" />
              <Legend color={OUTCOME.failed} label="Failed" />
            </div>
            <div style={{ height: 250 }}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={data?.monthly ?? []} margin={{ top: 4, right: 8, bottom: 0, left: -16 }}>
                  <CartesianGrid stroke="var(--border-subtle)" strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="label" tick={{ fill: 'var(--text-4)', fontSize: 11 }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fill: 'var(--text-4)', fontSize: 11 }} axisLine={false} tickLine={false} allowDecimals={false} />
                  <Tooltip content={<StackTooltip />} cursor={{ fill: 'var(--bg-elevated)' }} />
                  <Bar dataKey="filed" name="Filed" stackId="a" fill={OUTCOME.filed} barSize={30} isAnimationActive animationDuration={800} />
                  <Bar dataKey="review" name="In review" stackId="a" fill={OUTCOME.review} barSize={30} isAnimationActive animationDuration={800} />
                  <Bar dataKey="cleared" name="Cleared (no SAR)" stackId="a" fill={OUTCOME.cleared} barSize={30} isAnimationActive animationDuration={800} />
                  <Bar dataKey="failed" name="Failed" stackId="a" fill={OUTCOME.failed} radius={[4, 4, 0, 0]} barSize={30} isAnimationActive animationDuration={800} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </ChartCard>
        )}

        {isLoading ? (
          <SkeletonCard height={300} />
        ) : (
          <ChartCard title="Typology mix" subtitle="Which AML rules fire most — one alert can trigger several rules" delay={280}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <div style={{ width: 150, height: 170, flexShrink: 0, position: 'relative' }}>
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie data={data?.typology ?? []} dataKey="count" nameKey="rule_name" cx="50%" cy="50%" innerRadius={45} outerRadius={70} paddingAngle={2} stroke="none" isAnimationActive animationDuration={800}>
                      {(data?.typology ?? []).map((_, i) => (
                        <Cell key={i} fill={DONUT[i % DONUT.length]} />
                      ))}
                    </Pie>
                    <Tooltip content={<StackTooltip />} />
                  </PieChart>
                </ResponsiveContainer>
                <div style={{ position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', pointerEvents: 'none' }}>
                  <span style={{ fontSize: 20, fontWeight: 600, fontVariantNumeric: 'tabular-nums' }}>{formatNumber(typologyTotal)}</span>
                  <span style={{ fontSize: 10, color: 'var(--text-4)' }}>rule fires</span>
                </div>
              </div>
              <div style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', gap: 6 }}>
                {(data?.typology ?? []).slice(0, 6).map((t, i) => (
                  <div key={t.rule_id} style={{ display: 'flex', alignItems: 'center', gap: 7, fontSize: 12 }}>
                    <span style={{ width: 8, height: 8, borderRadius: 2, background: DONUT[i % DONUT.length], flexShrink: 0 }} />
                    <span style={{ color: 'var(--text-2)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{t.rule_name}</span>
                    <b style={{ marginLeft: 'auto', color: 'var(--text-3)', fontVariantNumeric: 'tabular-nums' }}>{t.count}</b>
                  </div>
                ))}
              </div>
            </div>
          </ChartCard>
        )}
      </div>

      {/* API traffic */}
      {isLoading ? (
        <SkeletonCard height={220} />
      ) : (
        <ChartCard title="API traffic — last 7 days" subtitle="Live request volume by response status" delay={360}>
          <div style={{ display: 'flex', gap: 16, marginBottom: 12 }}>
            <Legend color={TRAFFIC.ok} label="2xx / 3xx" />
            <Legend color={TRAFFIC.client_err} label="4xx client" />
            <Legend color={TRAFFIC.server_err} label="5xx server" />
          </div>
          <div style={{ height: 200 }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data?.api_daily ?? []} margin={{ top: 4, right: 8, bottom: 0, left: -16 }}>
                <CartesianGrid stroke="var(--border-subtle)" strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="label" tick={{ fill: 'var(--text-4)', fontSize: 11 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: 'var(--text-4)', fontSize: 11 }} axisLine={false} tickLine={false} allowDecimals={false} />
                <Tooltip content={<StackTooltip />} cursor={{ fill: 'var(--bg-elevated)' }} />
                <Bar dataKey="ok" stackId="t" fill={TRAFFIC.ok} barSize={26} isAnimationActive animationDuration={800} />
                <Bar dataKey="client_err" stackId="t" fill={TRAFFIC.client_err} barSize={26} isAnimationActive animationDuration={800} />
                <Bar dataKey="server_err" stackId="t" fill={TRAFFIC.server_err} radius={[4, 4, 0, 0]} barSize={26} isAnimationActive animationDuration={800} />
              </BarChart>
            </ResponsiveContainer>
          </div>
          {(data?.api_daily ?? []).length === 0 && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12.5, color: 'var(--text-4)', marginTop: 8 }}>
              <ShieldAlert size={13} /> No API traffic recorded in the last 7 days.
            </div>
          )}
        </ChartCard>
      )}

      {!isLoading && k && k.failed_total > 0 && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12.5, color: 'var(--warning)', background: 'var(--warning-subtle)', border: '1px solid var(--warning)', borderRadius: 'var(--r-md)', padding: '10px 14px' }}>
          <AlertTriangle size={14} style={{ flexShrink: 0 }} />
          {k.failed_total} alert{k.failed_total === 1 ? '' : 's'} failed to process (LLM/pipeline error) across all tenants — visible in the amber segments above.
        </div>
      )}
    </div>
  )
}

function Legend({ color, label }: { color: string; label: string }) {
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 12, color: 'var(--text-3)' }}>
      <span style={{ width: 9, height: 9, borderRadius: 2, background: color }} />
      {label}
    </span>
  )
}
