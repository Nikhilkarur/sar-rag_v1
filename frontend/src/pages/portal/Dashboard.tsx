import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  CheckCircle2,
  Clock,
  Inbox,
  Timer,
  TrendingDown,
  TrendingUp,
  Zap,
} from 'lucide-react'
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { useAuthStore } from '../../store/auth'
import { useAlerts, useSubmitTestAlert } from '../../hooks/useAlerts'
import { useUsage } from '../../hooks/useTenant'
import { useCountUp } from '../../hooks/useCountUp'
import { useTilt } from '../../hooks/useTilt'
import { useToast } from '../../components/ui/Toast'
import { Button } from '../../components/ui/Button'
import { Modal } from '../../components/ui/Modal'
import { Select, Field } from '../../components/ui/Input'
import { AlertStatusBadge, RiskScoreCell, RulePills } from '../../components/ui/Badge'
import { SkeletonStatCard, SkeletonCard, SkeletonTableRows } from '../../components/ui/Skeleton'
import { formatINR, greeting, timeAgo } from '../../utils/format'
import type { SimulatorScenario } from '../../types'

const SCENARIOS = [
  { value: 'STRUCTURING', label: 'Structuring — ₹9.9L near-threshold transfer' },
  { value: 'RAPID_MOVEMENT', label: 'Rapid Movement — ₹5L reversal' },
  { value: 'HIGH_RISK_TYPE', label: 'High-Risk Type — international wire' },
  { value: 'VELOCITY', label: 'Velocity — 8 txns in 1 hour' },
  { value: 'DEFAULT', label: 'Default scenario' },
]

interface StatCardProps {
  icon: React.ReactNode
  iconBg: string
  value: string
  label: string
  delta?: { value: number; positiveIsGood?: boolean }
  warn?: boolean
  index: number
}

function StatCard({ icon, iconBg, value, label, delta, warn, index }: StatCardProps) {
  const tilt = useTilt<HTMLDivElement>(5)
  return (
    <div
      ref={tilt.ref}
      onMouseMove={tilt.onMouseMove}
      onMouseLeave={tilt.onMouseLeave}
      className="stat-card tilt-card"
      style={{ animation: `springRise 560ms cubic-bezier(0.22, 1, 0.36, 1) ${index * 90}ms both` }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
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
        {delta !== undefined && (
          <span
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 4,
              fontSize: 11,
              fontWeight: 500,
              padding: '2px 8px',
              borderRadius: 'var(--r-full)',
              background: delta.value >= 0 ? 'var(--success-subtle)' : 'var(--danger-subtle)',
              color: delta.value >= 0 ? 'var(--success)' : 'var(--danger)',
            }}
          >
            {delta.value >= 0 ? <TrendingUp size={11} /> : <TrendingDown size={11} />}
            {delta.value >= 0 ? '+' : ''}
            {delta.value}% vs last month
          </span>
        )}
        {warn && (
          <span
            className="pulse-dot"
            style={{ background: 'var(--warning)', width: 8, height: 8, marginTop: 4 }}
          />
        )}
      </div>
      <div
        style={{
          fontSize: 34,
          fontWeight: 700,
          marginTop: 16,
          fontFamily: 'var(--font-display)',
          color: warn ? 'var(--warning)' : 'var(--text-1)',
          fontVariantNumeric: 'tabular-nums',
          letterSpacing: '-0.02em',
        }}
      >
        {value}
      </div>
      <div className="label-upper" style={{ marginTop: 10 }}>
        {label}
      </div>
    </div>
  )
}

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
        {payload[0].value} alerts
      </div>
    </div>
  )
}

export function Dashboard() {
  const { user } = useAuthStore()
  const navigate = useNavigate()
  const { toast } = useToast()
  const { data: alerts, isLoading: alertsLoading } = useAlerts()
  const { data: usage, isLoading: usageLoading } = useUsage()
  const [modalOpen, setModalOpen] = useState(false)
  const [scenario, setScenario] = useState<SimulatorScenario>('STRUCTURING')
  const submitTest = useSubmitTestAlert()

  const firstName = (user?.fullName ?? '').split(' ')[0]
  const pending = usage?.pending_review ?? 0

  const alertsCount = useCountUp(usage?.alerts_ingested ?? 0)
  const pendingCount = useCountUp(pending)
  const approvedCount = useCountUp(usage?.sars_approved ?? 0)
  const avgTime = useCountUp(usage?.avg_review_time_minutes ?? 0, 1200, 1)

  const chartData = usage?.daily_breakdown.slice(-14) ?? []
  const recent = alerts?.slice(0, 5) ?? []

  const handleInject = () => {
    submitTest.mutate(scenario, {
      onSuccess: () => {
        setModalOpen(false)
        toast('success', 'Test alert injected', 'Check the queue in ~8 seconds.')
      },
      onError: () => toast('error', 'Injection failed', 'Please try again.'),
    })
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      {/* Greeting */}
      <div
        style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 16, flexWrap: 'wrap' }}
      >
        <div>
          <h1 style={{ fontSize: 28, fontWeight: 700, letterSpacing: '-0.02em', fontFamily: 'var(--font-display)' }}>
            {greeting()}, {firstName}
            {pending > 0 && (
              <span style={{ color: 'var(--text-3)', fontWeight: 400 }}>
                {' '}
                — {pending} alert{pending === 1 ? '' : 's'} need{pending === 1 ? 's' : ''} your review
              </span>
            )}
          </h1>
          <p style={{ fontSize: 13, color: 'var(--text-3)', marginTop: 4 }}>AML Pipeline Status</p>
        </div>
        <Button size="sm" icon={<Zap size={14} />} onClick={() => setModalOpen(true)}>
          Submit Test Alert
        </Button>
      </div>

      {/* Stat cards */}
      <div
        className="stat-grid"
        style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16 }}
      >
        {usageLoading ? (
          <>
            <SkeletonStatCard />
            <SkeletonStatCard />
            <SkeletonStatCard />
            <SkeletonStatCard />
          </>
        ) : (
          <>
            <StatCard
              index={0}
              icon={<Inbox size={15} color="var(--accent-text)" />}
              iconBg="rgba(6,78,59,0.10)"
              value={alertsCount}
              label="Alerts This Month"
              delta={{ value: usage?.delta_alerts ?? 0 }}
            />
            <StatCard
              index={1}
              icon={<Clock size={15} color="var(--warning)" />}
              iconBg="rgba(160,116,26,0.10)"
              value={pendingCount}
              label="Pending Review"
              warn={pending > 0}
            />
            <StatCard
              index={2}
              icon={<CheckCircle2 size={15} color="var(--success)" />}
              iconBg="rgba(6,78,59,0.10)"
              value={approvedCount}
              label="Approved SARs"
              delta={{ value: usage?.delta_sars ?? 0 }}
            />
            <StatCard
              index={3}
              icon={<Timer size={15} color="var(--info)" />}
              iconBg="rgba(14,116,144,0.10)"
              value={`${avgTime} min`}
              label="Avg. Review Time"
            />
          </>
        )}
      </div>

      {/* Chart */}
      {usageLoading ? (
        <SkeletonCard height={240} />
      ) : (
        <div className="card" style={{ animation: 'springRise 560ms cubic-bezier(0.22, 1, 0.36, 1) 280ms both' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 24 }}>
            <h3 style={{ fontSize: 18, fontWeight: 600, letterSpacing: '-0.01em' }}>
              Alerts Ingested — Last 14 Days
            </h3>
            <span style={{ fontSize: 12, color: 'var(--text-3)', fontFamily: 'var(--font-mono)' }}>
              {chartData[0]?.date} – {chartData[chartData.length - 1]?.date}
            </span>
          </div>
          <div style={{ height: 220 }}>
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData} margin={{ top: 4, right: 8, bottom: 0, left: -24 }}>
                <defs>
                  {/* Clean emerald mesh under the curve — no gold, no mud */}
                  <linearGradient id="beaconFill" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#064E3B" stopOpacity={0.3} />
                    <stop offset="60%" stopColor="#0E8A66" stopOpacity={0.12} />
                    <stop offset="100%" stopColor="#0E7490" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="beaconStroke" x1="0" y1="0" x2="1" y2="0">
                    <stop offset="0%" stopColor="#064E3B" />
                    <stop offset="100%" stopColor="#0E7490" />
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
                <YAxis
                  tick={{ fill: 'var(--text-4)', fontSize: 11 }}
                  axisLine={false}
                  tickLine={false}
                  allowDecimals={false}
                />
                <Tooltip content={<ChartTooltip />} cursor={{ stroke: 'var(--border)', strokeWidth: 1 }} />
                <Area
                  type="monotone"
                  dataKey="alerts"
                  stroke="url(#beaconStroke)"
                  strokeWidth={2.5}
                  fill="url(#beaconFill)"
                  dot={false}
                  activeDot={{ r: 5, fill: 'var(--accent)', stroke: '#fff', strokeWidth: 2 }}
                  isAnimationActive={true}
                  animationDuration={1400}
                  animationEasing="ease-out"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* Recent activity */}
      <div className="card" style={{ padding: 0, animation: 'springRise 560ms cubic-bezier(0.22, 1, 0.36, 1) 380ms both' }}>
        <div style={{ padding: '28px 32px 16px' }}>
          <h3 style={{ fontSize: 18, fontWeight: 600, letterSpacing: '-0.01em' }}>Recent Activity</h3>
        </div>
        <div className="tbl-scroll">
          <table className="tbl tbl-clickable">
            <thead>
              <tr>
                <th style={{ paddingLeft: 24 }}>Transaction ID</th>
                <th style={{ textAlign: 'right' }}>Amount</th>
                <th>Risk Score</th>
                <th>Rules Fired</th>
                <th>Status</th>
                <th style={{ paddingRight: 24 }}>Time</th>
              </tr>
            </thead>
            <tbody>
              {alertsLoading ? (
                <SkeletonTableRows rows={5} cols={6} />
              ) : (
                recent.map((a, i) => (
                  <tr
                    key={a.id}
                    onClick={() => navigate(`/queue/${a.id}`)}
                    style={{ animation: `fadeInUp 420ms cubic-bezier(0.22, 1, 0.36, 1) ${480 + i * 60}ms both` }}
                  >
                    <td style={{ paddingLeft: 24, fontFamily: 'var(--font-mono)', fontSize: 13, color: 'var(--text-2)' }}>
                      {a.transaction_id}
                    </td>
                    <td style={{ textAlign: 'right', fontFamily: 'var(--font-mono)', fontWeight: 500 }}>
                      {formatINR(a.transaction_amount)}
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
                    <td style={{ paddingRight: 24, color: 'var(--text-3)', fontSize: 13 }}>
                      {timeAgo(a.created_at)}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
        <div style={{ padding: '16px 32px', borderTop: '1px solid var(--border-subtle)' }}>
          <button
            onClick={() => navigate('/queue')}
            style={{
              background: 'none',
              border: 'none',
              color: 'var(--accent-text)',
              fontSize: 13,
              fontWeight: 600,
              cursor: 'pointer',
              padding: 0,
            }}
          >
            View all in Queue →
          </button>
        </div>
      </div>

      {/* Test alert modal */}
      <Modal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        title="Submit Test Alert"
        width={380}
        footer={
          <>
            <Button variant="secondary" onClick={() => setModalOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleInject} loading={submitTest.isPending} icon={<Zap size={14} />}>
              Inject Alert
            </Button>
          </>
        }
      >
        <p style={{ fontSize: 13, color: 'var(--text-3)', marginBottom: 16 }}>
          Injects a synthetic transaction alert through the full pipeline — PII masking, AML
          analysis, and Groq draft generation.
        </p>
        <Field label="Scenario">
          <Select
            options={SCENARIOS}
            value={scenario}
            onChange={(e) => setScenario(e.target.value as SimulatorScenario)}
          />
        </Field>
      </Modal>
    </div>
  )
}
