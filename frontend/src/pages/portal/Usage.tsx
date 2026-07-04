import type { CSSProperties, ReactNode } from 'react'
import { Activity, AlertTriangle, Clock, Cpu, FileCheck2, Inbox, ShieldCheck, Zap } from 'lucide-react'
import {
  Area,
  AreaChart,
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
import { useUsage } from '../../hooks/useTenant'
import { useCountUp } from '../../hooks/useCountUp'
import { SkeletonStatCard, SkeletonCard } from '../../components/ui/Skeleton'
import { formatINR, formatNumber } from '../../utils/format'

/* Chart palette — kept consistent with the rest of the product. */
const OUTCOME = { filed: '#ec4899', review: '#6366f1', cleared: '#10b981', failed: '#f59e0b' }
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

function SimpleTooltip({ active, payload, label }: { active?: boolean; payload?: { value: number }[]; label?: string }) {
  if (!active || !payload?.length) return null
  return (
    <div style={{ background: 'var(--bg-overlay)', border: '1px solid var(--border)', borderRadius: 'var(--r-md)', padding: '8px 12px', fontSize: 12, boxShadow: 'var(--shadow-md)' }}>
      <div style={{ color: 'var(--text-3)' }}>{label}</div>
      <div style={{ color: 'var(--text-1)', fontWeight: 600, marginTop: 2, fontVariantNumeric: 'tabular-nums' }}>{payload[0].value}</div>
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

/** Month-over-month label. null = no prior-month baseline (don't fake a "+100%"). */
function deltaLabel(delta: number | null): string {
  if (delta === null) return 'new this month'
  if (delta === 0) return 'no change vs last month'
  return `${delta > 0 ? '+' : ''}${delta}% vs last month`
}

function Legend({ color, label }: { color: string; label: string }) {
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 12, color: 'var(--text-3)' }}>
      <span style={{ width: 9, height: 9, borderRadius: 2, background: color }} />
      {label}
    </span>
  )
}

/** Compact metric for the pipeline-usage strip (tokens / requests / failures). */
function MiniStat({ icon, value, label, warn }: { icon: ReactNode; value: string; label: string; warn?: boolean }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 10, minWidth: 0 }}>
      <span
        style={{
          display: 'inline-flex', alignItems: 'center', justifyContent: 'center', width: 32, height: 32,
          borderRadius: 'var(--r-md)', flexShrink: 0,
          background: warn ? 'var(--danger-subtle)' : 'var(--bg-elevated)',
          color: warn ? 'var(--danger)' : 'var(--text-3)',
          border: '1px solid var(--border-subtle)',
        }}
      >
        {icon}
      </span>
      <div style={{ minWidth: 0 }}>
        <div style={{ fontSize: 18, fontWeight: 600, letterSpacing: '-0.01em', color: warn ? 'var(--danger)' : 'var(--text-1)', fontVariantNumeric: 'tabular-nums' }}>
          {value}
        </div>
        <div style={{ fontSize: 12, color: 'var(--text-3)' }}>{label}</div>
      </div>
    </div>
  )
}

export function Usage() {
  const { data: usage, isLoading } = useUsage()

  const alerts = useCountUp(usage?.alerts_ingested ?? 0)
  const approved = useCountUp(usage?.sars_approved ?? 0)
  const cleared = useCountUp(usage?.false_positives_cleared ?? 0)
  const pending = useCountUp(usage?.pending_review ?? 0)
  const avgTime = useCountUp(usage?.avg_review_time_minutes ?? 0, 1200, 1)
  const failed = usage?.failed_count ?? 0

  const typology = usage?.typology ?? []
  const typologyTotal = typology.reduce((s, t) => s + t.count, 0)

  const screened = usage?.amount_screened_inr ?? 0
  const flagged = usage?.amount_flagged_inr ?? 0
  const flaggedPct = screened > 0 ? Math.round((flagged / screened) * 100) : 0

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      {/* KPI row — clean typographic cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 16 }}>
        {isLoading || !usage ? (
          <>
            <SkeletonStatCard />
            <SkeletonStatCard />
            <SkeletonStatCard />
            <SkeletonStatCard />
            <SkeletonStatCard />
          </>
        ) : (
          <>
            <Kpi index={0} icon={<Activity size={14} />} color="#8b5cf6" value={alerts} label="Alerts this month" sub={deltaLabel(usage.delta_alerts)} />
            <Kpi index={1} icon={<FileCheck2 size={14} />} color="#ec4899" value={approved} label="SARs filed" sub={deltaLabel(usage.delta_sars)} />
            <Kpi index={2} icon={<ShieldCheck size={14} />} color="#10b981" value={cleared} label="Cleared — no SAR" sub="below-threshold this month" />
            <Kpi index={3} icon={<Inbox size={14} />} color="#6366f1" value={pending} label="Pending review" sub="awaiting an officer" />
            <Kpi index={4} icon={<Clock size={14} />} color="#f59e0b" value={`${avgTime} min`} label="Avg. processing time" sub="ingest → filed" />
          </>
        )}
      </div>

      {/* Alert outcomes stack + typology mix */}
      <div className="chart-grid" style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1.6fr) minmax(0, 1fr)', gap: 16 }}>
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
                <BarChart data={usage?.outcome_monthly ?? []} margin={{ top: 4, right: 8, bottom: 0, left: -16 }}>
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
            {typology.length === 0 ? (
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 170, fontSize: 12.5, color: 'var(--text-4)' }}>
                No rules have fired yet.
              </div>
            ) : (
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <div style={{ width: 150, height: 170, flexShrink: 0, position: 'relative' }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie data={typology} dataKey="count" nameKey="rule_name" cx="50%" cy="50%" innerRadius={45} outerRadius={70} paddingAngle={2} stroke="none" isAnimationActive animationDuration={800}>
                        {typology.map((_, i) => (
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
                  {typology.slice(0, 6).map((t, i) => (
                    <div key={t.rule_id} style={{ display: 'flex', alignItems: 'center', gap: 7, fontSize: 12 }}>
                      <span style={{ width: 8, height: 8, borderRadius: 2, background: DONUT[i % DONUT.length], flexShrink: 0 }} />
                      <span style={{ color: 'var(--text-2)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{t.rule_name}</span>
                      <b style={{ marginLeft: 'auto', color: 'var(--text-3)', fontVariantNumeric: 'tabular-nums' }}>{t.count}</b>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </ChartCard>
        )}
      </div>

      {/* Classic charts — daily volume + monthly SAR trend */}
      <div className="chart-grid" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
        {isLoading ? (
          <>
            <SkeletonCard height={240} />
            <SkeletonCard height={240} />
          </>
        ) : (
          <>
            <ChartCard title="Daily alert volume" subtitle="Alerts ingested per day — last 30 days" delay={340}>
              <div style={{ height: 200 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={usage?.daily_breakdown ?? []} margin={{ top: 4, right: 8, bottom: 0, left: -24 }}>
                    <defs>
                      <linearGradient id="alertGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#6366f1" stopOpacity={0.25} />
                        <stop offset="100%" stopColor="#6366f1" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid stroke="var(--border-subtle)" strokeDasharray="3 3" vertical={false} />
                    <XAxis dataKey="date" tick={{ fill: 'var(--text-4)', fontSize: 11 }} axisLine={false} tickLine={false} interval="preserveStartEnd" />
                    <YAxis tick={{ fill: 'var(--text-4)', fontSize: 11 }} axisLine={false} tickLine={false} allowDecimals={false} />
                    <Tooltip content={<SimpleTooltip />} cursor={{ stroke: 'var(--border)' }} />
                    <Area type="monotone" dataKey="alerts" stroke="#6366f1" strokeWidth={2} fill="url(#alertGrad)" dot={false} isAnimationActive animationDuration={1000} />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </ChartCard>

            <ChartCard title="SARs filed" subtitle="Reports filed per month — last 6 months" delay={400}>
              <div style={{ height: 200 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={usage?.monthly_sars ?? []} margin={{ top: 4, right: 8, bottom: 0, left: -24 }}>
                    <CartesianGrid stroke="var(--border-subtle)" strokeDasharray="3 3" vertical={false} />
                    <XAxis dataKey="month" tick={{ fill: 'var(--text-4)', fontSize: 11 }} axisLine={false} tickLine={false} />
                    <YAxis tick={{ fill: 'var(--text-4)', fontSize: 11 }} axisLine={false} tickLine={false} allowDecimals={false} />
                    <Tooltip content={<SimpleTooltip />} cursor={{ fill: 'var(--bg-elevated)' }} />
                    <Bar dataKey="sars" name="SARs filed" fill="#ec4899" radius={[4, 4, 0, 0]} barSize={30} isAnimationActive animationDuration={900} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </ChartCard>
          </>
        )}
      </div>

      {/* Amount screened vs flagged (this month) */}
      {!isLoading && (
        <div className="card" style={{ animation: 'fadeInUp 300ms ease-out 460ms both' }}>
          <div style={{ marginBottom: 16 }}>
            <h3 style={{ fontSize: 15, fontWeight: 600, letterSpacing: '-0.01em' }}>Value screened vs flagged</h3>
            <p style={{ fontSize: 12.5, color: 'var(--text-3)', marginTop: 2 }}>Total transaction value assessed this month, and the share that escalated to a SAR.</p>
          </div>
          <div style={{ display: 'flex', gap: 40, flexWrap: 'wrap', marginBottom: 16 }}>
            <div>
              <div style={{ fontSize: 12, color: 'var(--text-3)', marginBottom: 4 }}>Screened</div>
              <div style={{ fontSize: 24, fontWeight: 600, letterSpacing: '-0.02em', fontVariantNumeric: 'tabular-nums' }}>{formatINR(screened)}</div>
            </div>
            <div>
              <div style={{ fontSize: 12, color: 'var(--text-3)', marginBottom: 4 }}>Flagged (→ SAR)</div>
              <div style={{ fontSize: 24, fontWeight: 600, letterSpacing: '-0.02em', color: '#ec4899', fontVariantNumeric: 'tabular-nums' }}>{formatINR(flagged)}</div>
            </div>
            <div>
              <div style={{ fontSize: 12, color: 'var(--text-3)', marginBottom: 4 }}>Flagged share</div>
              <div style={{ fontSize: 24, fontWeight: 600, letterSpacing: '-0.02em', color: 'var(--text-2)', fontVariantNumeric: 'tabular-nums' }}>{flaggedPct}%</div>
            </div>
          </div>
          <div style={{ height: 10, borderRadius: 999, background: 'var(--bg-elevated)', overflow: 'hidden' }} title={`${flaggedPct}% of screened value flagged`}>
            <div style={{ height: '100%', width: `${Math.min(100, flaggedPct)}%`, background: '#ec4899', transition: 'width 600ms ease-out' }} />
          </div>
        </div>
      )}

      {/* Pipeline usage strip — LLM tokens / requests / failures */}
      <div className="card" style={{ padding: '18px 24px', animation: 'fadeInUp 300ms ease-out 520ms both' }}>
        <h3 style={{ fontSize: 13, fontWeight: 600, letterSpacing: '0.02em', textTransform: 'uppercase', color: 'var(--text-3)', marginBottom: 14 }}>
          Pipeline usage
        </h3>
        <div style={{ display: 'flex', gap: 40, flexWrap: 'wrap' }}>
          <MiniStat icon={<Cpu size={15} />} value={(usage?.tokens_used ?? 0).toLocaleString('en-IN')} label="LLM tokens used" />
          <MiniStat icon={<Zap size={15} />} value={(usage?.total_requests ?? 0).toLocaleString('en-IN')} label="LLM requests" />
          <MiniStat icon={<AlertTriangle size={15} />} value={failed.toLocaleString('en-IN')} label="Failed to process" warn={failed > 0} />
        </div>
      </div>
    </div>
  )
}
