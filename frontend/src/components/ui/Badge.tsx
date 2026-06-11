import React from 'react';

/* ── Shared pill shell ─────────────────────────────────────────────── */

function Pill({
  color,
  bg,
  border,
  glow,
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
        padding: '0 9px',
        borderRadius: 999,
        fontFamily: 'var(--font-mono)',
        fontSize: 11,
        fontWeight: 600,
        whiteSpace: 'nowrap',
        color,
        background: bg,
        border: `1px solid ${border}`,
        boxShadow: glow,
      }}
    >
      {spinning ? (
        <svg className="animate-spin" width="11" height="11" viewBox="0 0 24 24" fill="none">
          <circle style={{ opacity: 0.25 }} cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path style={{ opacity: 0.75 }} fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
      ) : (
        <span style={{ width: 5, height: 5, borderRadius: '50%', background: 'currentColor', opacity: 0.85 }} />
      )}
      {children}
    </span>
  );
}

type Tone = { color: string; bg: string; border: string; glow?: string };

const TONES: Record<string, Tone> = {
  danger:  { color: 'var(--danger)',      bg: 'var(--danger-subtle)',  border: 'rgba(179,56,44,0.35)', glow: '0 1px 8px -2px rgba(179,56,44,0.25)' },
  warning: { color: 'var(--warning)',     bg: 'var(--warning-subtle)', border: 'rgba(160,116,26,0.35)' },
  success: { color: 'var(--success)',     bg: 'var(--success-subtle)', border: 'rgba(6,78,59,0.35)' },
  accent:  { color: 'var(--accent-text)', bg: 'var(--accent-subtle)',  border: 'rgba(6,78,59,0.35)' },
  info:    { color: 'var(--info)',        bg: 'rgba(14,116,144,0.1)',  border: 'rgba(14,116,144,0.35)' },
  neutral: { color: 'var(--text-3)',      bg: 'rgba(23,23,23,0.05)', border: 'var(--border)' },
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
          fontSize: 13,
          fontWeight: 600,
          fontVariantNumeric: 'tabular-nums',
          color,
          minWidth: 24,
          textAlign: 'right',
          textShadow: s >= 75 ? `0 0 12px ${color}` : undefined,
        }}
      >
        {s}
      </span>
      <span style={{ width: 44, height: 4, borderRadius: 2, background: 'rgba(23,23,23,0.08)', overflow: 'hidden' }}>
        <span
          style={{
            display: 'block',
            width: `${s}%`,
            height: '100%',
            borderRadius: 2,
            background: `linear-gradient(90deg, ${color}88, ${color})`,
            boxShadow: `0 0 8px ${color}`,
            transition: 'width 600ms cubic-bezier(0.22, 1, 0.36, 1)',
          }}
        />
      </span>
    </span>
  );
}

/* ── Alert / SAR status ────────────────────────────────────────────── */

const ALERT_STATUS: Record<string, { tone: Tone; label: string; spinning?: boolean }> = {
  PENDING_INGESTION:    { tone: TONES.neutral, label: 'QUEUED' },
  PROCESSING:           { tone: TONES.accent,  label: 'PROCESSING', spinning: true },
  PROCESSING_COMPLETED: { tone: TONES.warning, label: 'PENDING' },
  PENDING_REVIEW:       { tone: TONES.warning, label: 'PENDING' },
  COMPLETED_CLEAN:      { tone: TONES.success, label: 'CLEAN' },
  PROCESSING_FAILED:    { tone: TONES.danger,  label: 'FAILED' },
  APPROVED:             { tone: TONES.success, label: 'APPROVED' },
  REJECTED:             { tone: TONES.danger,  label: 'REJECTED' },
  DELIVERED:            { tone: TONES.info,    label: 'DELIVERED' },
};

export function AlertStatusBadge({ status }: { status: string }) {
  const cfg = ALERT_STATUS[status] ?? { tone: TONES.neutral, label: status };
  return <Pill {...cfg.tone} spinning={cfg.spinning}>{cfg.label}</Pill>;
}

export function StatusBadge({ status }: { status: string }) {
  return <AlertStatusBadge status={status} />;
}

/* ── Compliance rules ──────────────────────────────────────────────── */

export function RulePill({ rule }: { rule: string }) {
  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        height: 20,
        padding: '0 8px',
        borderRadius: 'var(--r-sm)',
        fontFamily: 'var(--font-mono)',
        fontSize: 10,
        letterSpacing: '0.04em',
        color: 'var(--accent-text)',
        background: 'var(--accent-subtle)',
        border: '1px solid rgba(6,78,59,0.3)',
        whiteSpace: 'nowrap',
      }}
    >
      {rule}
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
              borderRadius: 'var(--r-sm)', fontFamily: 'var(--font-mono)', fontSize: 10,
              color: 'var(--text-3)', background: 'rgba(23,23,23,0.05)', border: '1px solid var(--border)',
            }}
          >
            +{extra}
          </span>
          <span className="tip-content">{list.slice(max).join(', ')}</span>
        </span>
      )}
    </span>
  );
}

export function ConfidencePill({ confidence }: { confidence: 'HIGH' | 'MEDIUM' | 'LOW' | string }) {
  const tone = confidence === 'HIGH' ? TONES.danger : confidence === 'MEDIUM' ? TONES.warning : TONES.neutral;
  return <Pill {...tone}>{confidence}</Pill>;
}

/* ── Tenant status (admin) ─────────────────────────────────────────── */

const TENANT_STATUS: Record<string, { tone: Tone; label: string }> = {
  PENDING_VERIFICATION: { tone: TONES.warning, label: 'PENDING' },
  ACTIVE:               { tone: TONES.success, label: 'ACTIVE' },
  REJECTED:             { tone: TONES.danger,  label: 'REJECTED' },
  SUSPENDED:            { tone: TONES.neutral, label: 'SUSPENDED' },
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
