import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { TrendingDown, TrendingUp, Zap } from 'lucide-react'
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
import { useToast } from '../../components/ui/Toast'
import { Button } from '../../components/ui/Button'
import { Modal } from '../../components/ui/Modal'
import { Select, Field } from '../../components/ui/Input'
import { AlertStatusBadge, RiskScoreCell, RulePills } from '../../components/ui/Badge'
import { SkeletonTableRows, Skeleton } from '../../components/ui/Skeleton'
import { formatINR, greeting, timeAgo } from '../../utils/format'
import type { SimulatorScenario } from '../../types'

const SCENARIOS = [
  { value: 'STRUCTURING', label: 'Structuring — ₹9.9L near-threshold transfer' },
  { value: 'RAPID_MOVEMENT', label: 'Rapid Movement — ₹5L reversal' },
  { value: 'HIGH_RISK_TYPE', label: 'High-Risk Type — international wire' },
  { value: 'VELOCITY', label: 'Velocity — 8 txns in 1 hour' },
  { value: 'DEFAULT', label: 'Default scenario' },
]

interface StatCellProps {
  value: string
  label: string
  delta?: { value: number }
  warn?: boolean
}

/** Attio-style stat: a cell in a shared hairline band, not a floating card */
function StatCell({ value, label, delta, warn }: StatCellProps) {
  return (
    <div
      style={{
        padding: '20px 24px',
        display: 'flex',
        flexDirection: 'column',
        gap: 6,
        minWidth: 0,
      }}
    >
      <span style={{ fontSize: 13, color: 'var(--text-3)', display: 'flex', alignItems: 'center', gap: 6 }}>
        {label}
        {warn && <span className="pulse-dot" style={{ background: 'var(--warning)', width: 6, height: 6 }} />}
      </span>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 10, flexWrap: 'wrap' }}>
        <span
          style={{
            fontSize: 26,
            fontWeight: 600,
            letterSpacing: '-0.02em',
            color: 'var(--text-1)',
            fontVariantNumeric: 'tabular-nums',
            lineHeight: 1.2,
          }}
        >
          {value}
        </span>
        {delta !== undefined && (
          <span
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 3,
              fontSize: 12,
              fontWeight: 500,
              color: delta.value >= 0 ? 'var(--success)' : 'var(--danger)',
            }}
          >
            {delta.value >= 0 ? <TrendingUp size={12} /> : <TrendingDown size={12} />}
            {delta.value >= 0 ? '+' : ''}
            {delta.value}%
          </span>
        )}
      </div>
    </div>
  )
}

function ChartTooltip({ active, payload, label }: { active?: boolean; payload?: { value: number }[]; label?: string }) {
  if (!active || !payload?.length) return null
  return (
    <div
      style={{
        background: 'var(--bg-surface)',
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

  const panelStyle: React.CSSProperties = {
    background: 'var(--bg-surface)',
    border: '1px solid var(--border)',
    borderRadius: 'var(--r-lg)',
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      {/* Greeting */}
      <div
        style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 16, flexWrap: 'wrap' }}
      >
        <div>
          <h1 style={{ fontSize: 20, fontWeight: 600, letterSpacing: '-0.02em' }}>
            {greeting()}, {firstName}
          </h1>
          <p style={{ fontSize: 13, color: 'var(--text-3)', marginTop: 2 }}>
            {pending > 0
              ? `${pending} alert${pending === 1 ? '' : 's'} need${pending === 1 ? 's' : ''} your review`
              : 'AML pipeline is clear'}
          </p>
        </div>
        <Button size="sm" variant="secondary" icon={<Zap size={13} />} onClick={() => setModalOpen(true)}>
          Submit test alert
        </Button>
      </div>

      {/* Stat band — one bordered strip, hairline-divided cells */}
      <div
        style={{
          ...panelStyle,
          display: 'grid',
          gridTemplateColumns: 'repeat(4, 1fr)',
          overflow: 'hidden',
        }}
        className="stat-band"
      >
        {usageLoading ? (
          [0, 1, 2, 3].map((i) => (
            <div key={i} style={{ padding: '20px 24px', borderRight: i < 3 ? '1px solid var(--border-subtle)' : 'none' }}>
              <Skeleton width="60%" height={12} />
              <Skeleton width="40%" height={26} style={{ marginTop: 10 }} />
            </div>
          ))
        ) : (
          <>
            <div style={{ borderRight: '1px solid var(--border-subtle)' }}>
              <StatCell value={alertsCount} label="Alerts this month" delta={{ value: usage?.delta_alerts ?? 0 }} />
            </div>
            <div style={{ borderRight: '1px solid var(--border-subtle)' }}>
              <StatCell value={pendingCount} label="Pending review" warn={pending > 0} />
            </div>
            <div style={{ borderRight: '1px solid var(--border-subtle)' }}>
              <StatCell value={approvedCount} label="Approved SARs" delta={{ value: usage?.delta_sars ?? 0 }} />
            </div>
            <StatCell value={`${avgTime} min`} label="Avg. review time" />
          </>
        )}
      </div>

      {/* Chart */}
      <div style={{ ...panelStyle, padding: 24 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 20 }}>
          <h3 style={{ fontSize: 14, fontWeight: 600, letterSpacing: '-0.01em' }}>
            Alerts ingested — last 14 days
          </h3>
          <span style={{ fontSize: 12, color: 'var(--text-4)', fontFamily: 'var(--font-mono)' }}>
            {chartData[0]?.date} – {chartData[chartData.length - 1]?.date}
          </span>
        </div>
        {usageLoading ? (
          <Skeleton height={200} />
        ) : (
          <div style={{ height: 220 }}>
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData} margin={{ top: 4, right: 8, bottom: 0, left: -24 }}>
                <defs>
                  <linearGradient id="alertFill" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#064E3B" stopOpacity={0.16} />
                    <stop offset="100%" stopColor="#064E3B" stopOpacity={0} />
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
                  stroke="#064E3B"
                  strokeWidth={1.75}
                  fill="url(#alertFill)"
                  dot={false}
                  activeDot={{ r: 4, fill: 'var(--accent)', stroke: '#fff', strokeWidth: 2 }}
                  isAnimationActive={true}
                  animationDuration={900}
                  animationEasing="ease-out"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      {/* Recent activity */}
      <div style={{ ...panelStyle, overflow: 'hidden' }}>
        <div
          style={{
            padding: '14px 20px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            borderBottom: '1px solid var(--border-subtle)',
          }}
        >
          <h3 style={{ fontSize: 14, fontWeight: 600, letterSpacing: '-0.01em' }}>Recent activity</h3>
          <button
            onClick={() => navigate('/queue')}
            style={{
              background: 'none',
              border: 'none',
              color: 'var(--text-3)',
              fontSize: 13,
              fontWeight: 500,
              cursor: 'pointer',
              padding: 0,
            }}
            onMouseEnter={(e) => (e.currentTarget.style.color = 'var(--text-1)')}
            onMouseLeave={(e) => (e.currentTarget.style.color = 'var(--text-3)')}
          >
            View all →
          </button>
        </div>
        <div className="tbl-scroll">
          <table className="tbl tbl-clickable">
            <thead>
              <tr>
                <th style={{ paddingLeft: 20 }}>Transaction ID</th>
                <th style={{ textAlign: 'right' }}>Amount</th>
                <th>Risk</th>
                <th>Rules</th>
                <th>Status</th>
                <th style={{ textAlign: 'right', paddingRight: 20 }}>Time</th>
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
                    style={{ animation: `fadeInUp 240ms cubic-bezier(0.22, 1, 0.36, 1) ${i * 30}ms both` }}
                  >
                    <td style={{ paddingLeft: 20, fontFamily: 'var(--font-mono)', fontSize: 12.5, color: 'var(--text-2)' }}>
                      {a.transaction_id}
                    </td>
                    <td style={{ textAlign: 'right', fontFamily: 'var(--font-mono)', fontSize: 13, fontWeight: 500, color: 'var(--text-1)' }}>
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
                    <td style={{ textAlign: 'right', paddingRight: 20, color: 'var(--text-3)', fontSize: 12.5 }}>
                      {timeAgo(a.created_at)}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Test alert modal */}
      <Modal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        title="Submit test alert"
        width={380}
        footer={
          <>
            <Button variant="secondary" onClick={() => setModalOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleInject} loading={submitTest.isPending} icon={<Zap size={14} />}>
              Inject alert
            </Button>
          </>
        }
      >
        <p style={{ fontSize: 13, color: 'var(--text-3)', marginBottom: 16 }}>
          Injects a synthetic transaction alert through the full pipeline — PII masking, AML
          analysis, and AI draft generation.
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
