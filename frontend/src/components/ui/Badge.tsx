import React from 'react';

/* ── Shared pill shell — Resend-style: white chip, hairline border,
      colored status dot, quiet sans label ─────────────────────────── */

function Pill({
  color,
  bg,
  border,
  children,
  spinning,
}: {
  color: string;
  bg: string;
  border: string;
  glow?: string;
  children: React.ReactNode;
  spinning?: boolean;
}) {
  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 6,
        height: 22,
        padding: '0 8px',
        borderRadius: 999,
        fontFamily: 'var(--font-sans)',
        fontSize: 12,
        fontWeight: 500,
        whiteSpace: 'nowrap',
        color: 'var(--text-2)',
        background: bg,
        border: `1px solid ${border}`,
      }}
    >
      {spinning ? (
        <svg className="animate-spin" width="11" height="11" viewBox="0 0 24 24" fill="none" style={{ color }}>
          <circle style={{ opacity: 0.25 }} cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path style={{ opacity: 0.75 }} fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
      ) : (
        <span style={{ width: 6, height: 6, borderRadius: '50%', background: color, flexShrink: 0 }} />
      )}
      {children}
    </span>
  );
}

type Tone = { color: string; bg: string; border: string };

const TONES: Record<string, Tone> = {
  danger:  { color: 'var(--danger)',        bg: '#FFFFFF', border: 'var(--border)' },
  warning: { color: 'var(--warning)',       bg: '#FFFFFF', border: 'var(--border)' },
  success: { color: 'var(--success)',       bg: '#FFFFFF', border: 'var(--border)' },
  accent:  { color: 'var(--accent-bright)', bg: '#FFFFFF', border: 'var(--border)' },
  info:    { color: 'var(--info)',          bg: '#FFFFFF', border: 'var(--border)' },
  neutral: { color: 'var(--text-4)',        bg: '#FFFFFF', border: 'var(--border)' },
};

/* ── Risk ──────────────────────────────────────────────────────────── */

type RiskLevel = 'HIGH' | 'MEDIUM' | 'LOW' | 'CRITICAL';

export function RiskBadge({ score, level }: { score?: number; level?: RiskLevel }) {
  let riskLevel: RiskLevel = level ?? 'LOW';
  if (score !== undefined && !level) {
    if (score >= 75) riskLevel = 'HIGH';
    else if (score >= 50) riskLevel = 'MEDIUM';
    else riskLevel = 'LOW';
  }
  const tone =
    riskLevel === 'CRITICAL' || riskLevel === 'HIGH' ? TONES.danger
    : riskLevel === 'MEDIUM' ? TONES.warning
    : TONES.success;
  const displayText = score !== undefined ? `${score}  ${riskLevel}` : riskLevel;
  return <Pill {...tone}>{displayText}</Pill>;
}

/** Score + thermometer micro-bar, for table cells */
export function RiskScoreCell({ score }: { score: number }) {
  const s = Math.max(0, Math.min(100, score ?? 0));
  const color = s >= 75 ? 'var(--danger)' : s >= 50 ? 'var(--warning)' : 'var(--success)';
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}>
      <span
        style={{
          fontFamily: 'var(--font-mono)',
          fontSize: 12.5,
          fontWeight: 500,
          fontVariantNumeric: 'tabular-nums',
          color: 'var(--text-1)',
          minWidth: 24,
          textAlign: 'right',
        }}
      >
        {s}
      </span>
      <span style={{ width: 44, height: 4, borderRadius: 2, background: 'var(--bg-overlay)', overflow: 'hidden' }}>
        <span
          style={{
            display: 'block',
            width: `${s}%`,
            height: '100%',
            borderRadius: 2,
            background: color,
            transition: 'width 400ms cubic-bezier(0.22, 1, 0.36, 1)',
          }}
        />
      </span>
    </span>
  );
}

/* ── Alert / SAR status ────────────────────────────────────────────── */

const ALERT_STATUS: Record<string, { tone: Tone; label: string; spinning?: boolean }> = {
  PENDING_INGESTION:    { tone: TONES.neutral, label: 'Queued' },
  PROCESSING:           { tone: TONES.accent,  label: 'Processing', spinning: true },
  PROCESSING_COMPLETED: { tone: TONES.warning, label: 'Pending' },
  PENDING_REVIEW:       { tone: TONES.warning, label: 'Pending' },
  COMPLETED_CLEAN:      { tone: TONES.success, label: 'Clean' },
  PROCESSING_FAILED:    { tone: TONES.danger,  label: 'Failed' },
  APPROVED:             { tone: TONES.success, label: 'Approved' },
  REJECTED:             { tone: TONES.danger,  label: 'Rejected' },
  DELIVERED:            { tone: TONES.info,    label: 'Delivered' },
};

export function AlertStatusBadge({ status }: { status: string }) {
  const cfg = ALERT_STATUS[status] ?? { tone: TONES.neutral, label: status };
  return <Pill {...cfg.tone} spinning={cfg.spinning}>{cfg.label}</Pill>;
}

export function StatusBadge({ status }: { status: string }) {
  return <AlertStatusBadge status={status} />;
}

/* ── Compliance rules ──────────────────────────────────────────────── */

// Human labels for the raw rule ids (compliance_analyzer.py). Anything unmapped falls back
// to a de-underscored, capitalized form so a new rule still reads cleanly.
const RULE_LABELS: Record<string, string> = {
  STRUCTURING: 'Structuring',
  RAPID_MOVEMENT: 'Rapid movement',
  ROUND_NUMBER: 'Round number',
  DORMANT_ACTIVATION: 'Dormant activation',
  HIGH_RISK_TYPE: 'High-risk type',
  VELOCITY: 'Velocity',
  COUNTERPARTY_RISK: 'Counterparty risk',
  RISK_SCORE_THRESHOLD: 'Risk score',
};

export function prettyRule(rule: string): string {
  return RULE_LABELS[rule] ?? rule.replace(/_/g, ' ').toLowerCase().replace(/^./, (c) => c.toUpperCase());
}

export function RulePill({ rule }: { rule: string }) {
  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        height: 20,
        padding: '0 8px',
        borderRadius: 'var(--r-sm)',
        fontSize: 11.5,
        color: 'var(--text-2)',
        background: 'var(--bg-elevated)',
        border: '1px solid var(--border)',
        whiteSpace: 'nowrap',
      }}
    >
      {prettyRule(rule)}
    </span>
  );
}

export function RulePills({ rules, max = 2 }: { rules?: string[]; max?: number }) {
  const list = rules ?? [];
  if (list.length === 0) return <span style={{ color: 'var(--text-4)', fontSize: 12 }}>—</span>;
  const shown = list.slice(0, max);
  const extra = list.length - shown.length;
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, flexWrap: 'wrap' }}>
      {shown.map((r) => <RulePill key={r} rule={r} />)}
      {extra > 0 && (
        <span className="tip" style={{ cursor: 'default' }}>
          <span
            style={{
              display: 'inline-flex', alignItems: 'center', height: 20, padding: '0 7px',
              borderRadius: 'var(--r-sm)', fontFamily: 'var(--font-mono)', fontSize: 10.5,
              color: 'var(--text-3)', background: 'var(--bg-elevated)', border: '1px solid var(--border)',
            }}
          >
            +{extra}
          </span>
          <span className="tip-content">{list.slice(max).map(prettyRule).join(', ')}</span>
        </span>
      )}
    </span>
  );
}

export function ConfidencePill({ confidence }: { confidence: 'HIGH' | 'MEDIUM' | 'LOW' | string }) {
  const tone = confidence === 'HIGH' ? TONES.danger : confidence === 'MEDIUM' ? TONES.warning : TONES.neutral;
  const label = typeof confidence === 'string'
    ? confidence.charAt(0) + confidence.slice(1).toLowerCase()
    : confidence;
  return <Pill {...tone}>{label}</Pill>;
}

/* ── Tenant status (admin) ─────────────────────────────────────────── */

const TENANT_STATUS: Record<string, { tone: Tone; label: string }> = {
  PENDING_VERIFICATION: { tone: TONES.warning, label: 'Pending' },
  ACTIVE:               { tone: TONES.success, label: 'Active' },
  REJECTED:             { tone: TONES.danger,  label: 'Rejected' },
  SUSPENDED:            { tone: TONES.neutral, label: 'Suspended' },
};

export function TenantStatusBadge({ status }: { status: string }) {
  const cfg = TENANT_STATUS[status] ?? { tone: TONES.neutral, label: status };
  return <Pill {...cfg.tone}>{cfg.label}</Pill>;
}

/* ── HTTP (admin logs) ─────────────────────────────────────────────── */

const METHOD_COLOR: Record<string, string> = {
  GET: 'var(--info)',
  POST: 'var(--success)',
  PUT: 'var(--warning)',
  PATCH: 'var(--warning)',
  DELETE: 'var(--danger)',
};

export function MethodBadge({ method }: { method: string }) {
  const color = METHOD_COLOR[method?.toUpperCase()] ?? 'var(--text-3)';
  return (
    <span
      style={{
        fontFamily: 'var(--font-mono)', fontSize: 11, fontWeight: 600, letterSpacing: '0.04em',
        color, minWidth: 44, display: 'inline-block',
      }}
    >
      {method}
    </span>
  );
}

export function HttpStatusBadge({ code, status }: { code?: number | null; status?: number | null }) {
  const n = code ?? status ?? 0;
  const tone = n >= 500 ? TONES.danger : n >= 400 ? TONES.warning : n >= 200 && n < 300 ? TONES.success : TONES.neutral;
  return <Pill {...tone}>{n}</Pill>;
}
