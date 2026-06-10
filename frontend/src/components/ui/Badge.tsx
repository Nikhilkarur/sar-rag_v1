import React from 'react'
import type { AlertStatus, Confidence, TenantStatus } from '../../types'

const ALERT_STYLES: Record<AlertStatus, { bg: string; color: string; label: string; pulse?: boolean }> = {
  PENDING_INGESTION: { bg: 'var(--bg-elevated)', color: 'var(--text-3)', label: 'Pending' },
  PROCESSING: { bg: 'var(--info-subtle)', color: 'var(--info)', label: 'Processing', pulse: true },
  PENDING_REVIEW: { bg: 'var(--warning-subtle)', color: 'var(--warning)', label: 'Pending Review' },
  APPROVED: { bg: 'var(--success-subtle)', color: 'var(--success)', label: 'Approved' },
  REJECTED: { bg: 'var(--danger-subtle)', color: 'var(--danger)', label: 'Rejected' },
  DELIVERED: { bg: 'var(--accent-subtle)', color: 'var(--accent-text)', label: 'Delivered' },
}

const pillBase: React.CSSProperties = {
  height: 22,
  padding: '0 8px',
  borderRadius: 'var(--r-full)',
  fontSize: 11,
  fontWeight: 500,
  display: 'inline-flex',
  alignItems: 'center',
  gap: 6,
  whiteSpace: 'nowrap',
  transition: 'background 250ms ease-out, color 250ms ease-out',
}

export function AlertStatusBadge({ status }: { status: AlertStatus }) {
  const s = ALERT_STYLES[status] ?? ALERT_STYLES.PENDING_INGESTION
  return (
    <span style={{ ...pillBase, background: s.bg, color: s.color }}>
      {s.pulse && <span className="pulse-dot" style={{ background: s.color }} />}
      {s.label}
    </span>
  )
}

const TENANT_STYLES: Record<TenantStatus, { bg: string; color: string; label: string }> = {
  ACTIVE: { bg: 'var(--success-subtle)', color: 'var(--success)', label: 'Active' },
  PENDING_VERIFICATION: { bg: 'var(--warning-subtle)', color: 'var(--warning)', label: 'Pending' },
  SUSPENDED: { bg: 'var(--danger-subtle)', color: 'var(--danger)', label: 'Suspended' },
  REJECTED: { bg: 'var(--bg-elevated)', color: 'var(--text-3)', label: 'Rejected' },
}

export function TenantStatusBadge({ status }: { status: TenantStatus }) {
  const s = TENANT_STYLES[status]
  return <span style={{ ...pillBase, background: s.bg, color: s.color }}>{s.label}</span>
}

const CONFIDENCE_STYLES: Record<Confidence, { bg: string; color: string }> = {
  HIGH: { bg: 'var(--danger-subtle)', color: 'var(--danger)' },
  MEDIUM: { bg: 'var(--warning-subtle)', color: 'var(--warning)' },
  LOW: { bg: 'var(--success-subtle)', color: 'var(--success)' },
}

export function ConfidencePill({ confidence }: { confidence: Confidence }) {
  const s = CONFIDENCE_STYLES[confidence]
  return (
    <span style={{ ...pillBase, background: s.bg, color: s.color, fontWeight: 600 }}>
      {confidence}
    </span>
  )
}

export function RulePill({ rule }: { rule: string }) {
  return (
    <span
      style={{
        ...pillBase,
        height: 20,
        fontSize: 11,
        fontFamily: 'var(--font-mono)',
        background: 'var(--accent-subtle)',
        color: 'var(--accent-text)',
      }}
    >
      {rule}
    </span>
  )
}

export function RulePills({ rules, max = 2 }: { rules: string[]; max?: number }) {
  const shown = rules.slice(0, max)
  const extra = rules.length - shown.length
  if (rules.length === 0) {
    return <span style={{ color: 'var(--text-4)', fontSize: 12 }}>—</span>
  }
  return (
    <span style={{ display: 'inline-flex', gap: 4, alignItems: 'center' }}>
      {shown.map((r) => (
        <RulePill key={r} rule={r} />
      ))}
      {extra > 0 && (
        <span style={{ fontSize: 11, color: 'var(--text-3)', fontFamily: 'var(--font-mono)' }}>
          +{extra}
        </span>
      )}
    </span>
  )
}

export function HttpStatusBadge({ code }: { code: number | null }) {
  if (code === null) {
    return (
      <span style={{ ...pillBase, background: 'var(--accent-subtle)', color: 'var(--accent-text)' }}>
        Internal
      </span>
    )
  }
  const s =
    code < 400
      ? { bg: 'var(--success-subtle)', color: 'var(--success)' }
      : code < 500
        ? { bg: 'var(--warning-subtle)', color: 'var(--warning)' }
        : { bg: 'var(--danger-subtle)', color: 'var(--danger)' }
  return (
    <span style={{ ...pillBase, background: s.bg, color: s.color, fontFamily: 'var(--font-mono)' }}>
      {code}
    </span>
  )
}

export function MethodBadge({ method }: { method: string }) {
  const colors: Record<string, { bg: string; color: string }> = {
    POST: { bg: 'var(--info-subtle)', color: 'var(--info)' },
    GET: { bg: 'var(--bg-elevated)', color: 'var(--text-2)' },
    PUT: { bg: 'var(--warning-subtle)', color: 'var(--warning)' },
    DELETE: { bg: 'var(--danger-subtle)', color: 'var(--danger)' },
  }
  const s = colors[method] ?? colors.GET
  return (
    <span
      style={{
        ...pillBase,
        background: s.bg,
        color: s.color,
        fontFamily: 'var(--font-mono)',
        fontSize: 10,
      }}
    >
      {method}
    </span>
  )
}

export function riskColor(score: number): string {
  if (score < 50) return 'var(--success)'
  if (score < 75) return 'var(--warning)'
  return 'var(--danger)'
}

export function RiskScoreCell({ score }: { score: number }) {
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
      <span
        style={{
          width: 6,
          height: 6,
          borderRadius: '50%',
          background: riskColor(score),
          flexShrink: 0,
        }}
      />
      <span style={{ fontFamily: 'var(--font-mono)', fontSize: 13, color: riskColor(score) }}>
        {score}
      </span>
    </span>
  )
}
