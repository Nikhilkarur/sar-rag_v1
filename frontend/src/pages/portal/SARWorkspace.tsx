import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  AlertTriangle,
  Check,
  ChevronDown,
  ChevronLeft,
  Download,
  Eye,
  Lock,
  Send,
  Sparkles,
  X,
  XCircle,
} from 'lucide-react'
import { useAlert, useApproveAlert, useRejectAlert, useUpdateDraft } from '../../hooks/useAlerts'
import { useAuthStore } from '../../store/auth'
import { useToast } from '../../components/ui/Toast'
import { Button } from '../../components/ui/Button'
import { Modal } from '../../components/ui/Modal'
import { CodeBlock } from '../../components/ui/CodeBlock'
import { CopyButton } from '../../components/ui/CopyButton'
import { AlertStatusBadge, ConfidencePill, RiskScoreCell } from '../../components/ui/Badge'
import { Skeleton } from '../../components/ui/Skeleton'
import { AegisShield } from '../../components/AegisLogo'
import { previewRehydrated } from '../../api/alerts'
import { downloadSarPdf } from '../../api/tenant'
import { formatINR, timeAgo, formatDateTime } from '../../utils/format'
import type { ComplianceRule, SARStructured, SARKeyIndicator } from '../../types'

/* ═════════════════════════════════════════════════════════════════════════
   SAR WORKSPACE — Attio-style split screen.
   Left: the record — transaction attributes and AML analysis.
   Right: the document — SAR draft on a quiet canvas.
   Actions live in the header; the divider drags.
   ═════════════════════════════════════════════════════════════════════════ */

// ── Panel sizing ─────────────────────────────────────────────────────────

const STORAGE_KEY = 'aegis-split-width'
const MIN_LEFT_PX = 320
const MAX_LEFT_PX = 600

function loadLeftWidth(): number {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) {
      const n = Number(raw)
      if (Number.isFinite(n)) return Math.min(MAX_LEFT_PX, Math.max(MIN_LEFT_PX, n))
    }
  } catch {
    /* corrupted — use default */
  }
  return 400
}

// ── Helpers ──────────────────────────────────────────────────────────────

function escapeHtml(s: string): string {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
}

function draftToHtml(text: string): string {
  return text
    .split('\n')
    .map((line) =>
      /^[0-9]+\. [A-Z]/.test(line)
        ? `<span class="sar-section-header" contenteditable="false">${escapeHtml(line)}</span>`
        : `${escapeHtml(line)}\n`,
    )
    .join('')
}

const RISK_COLOR: Record<string, string> = {
  HIGH: 'var(--danger)',
  MEDIUM: 'var(--warning)',
  LOW: 'var(--success)',
}

/** Attio-style attribute row: quiet gray label column, value column */
function FieldRow({ label, value, masked }: { label: string; value: string; masked?: boolean }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '5px 0', minHeight: 30 }}>
      <span style={{ width: 120, flexShrink: 0, fontSize: 13, color: 'var(--text-3)' }}>
        {label}
      </span>
      <span
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: 6,
          fontSize: 13,
          fontFamily: masked ? 'var(--font-mono)' : 'var(--font-sans)',
          color: 'var(--text-1)',
          minWidth: 0,
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          whiteSpace: 'nowrap',
        }}
      >
        {masked && (
          <span className="tip" style={{ flexShrink: 0 }}>
            <Lock size={10} color="var(--text-4)" />
            <span className="tip-content">PII masked for analysis security. Restored on approval.</span>
          </span>
        )}
        {value}
      </span>
    </div>
  )
}

/** Section heading inside the record panel */
function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <div
      style={{
        fontSize: 11,
        fontWeight: 500,
        letterSpacing: '0.05em',
        textTransform: 'uppercase',
        color: 'var(--text-3)',
        margin: '20px 0 6px',
      }}
    >
      {children}
    </div>
  )
}

// ── SAR document (structured) ──────────────────────────────────────────────

/** draft_structured may be null or malformed on older/edge drafts — normalize defensively. */
function normalizeStructured(raw: unknown): SARStructured | null {
  if (!raw || typeof raw !== 'object') return null
  const obj = raw as Record<string, unknown>
  const kiRaw = Array.isArray(obj.key_indicators) ? obj.key_indicators : []
  const key_indicators = kiRaw
    .map((k): SARKeyIndicator | null => {
      if (!k || typeof k !== 'object') return null
      const o = k as Record<string, unknown>
      const indicator = String(o.indicator ?? '').trim()
      if (!indicator) return null
      return {
        indicator,
        regulation: String(o.regulation ?? '').trim(),
        description: String(o.description ?? '').trim(),
      }
    })
    .filter((k): k is SARKeyIndicator => k !== null)
  const recommended_action =
    typeof obj.recommended_action === 'string' ? obj.recommended_action.trim() : ''
  if (key_indicators.length === 0 && !recommended_action) return null
  return { key_indicators, recommended_action }
}

/** Uppercase, underlined document section heading. */
function DocH({ children }: { children: React.ReactNode }) {
  return (
    <div
      style={{
        fontSize: 11,
        fontWeight: 600,
        letterSpacing: '0.06em',
        textTransform: 'uppercase',
        color: 'var(--text-3)',
        paddingBottom: 6,
        borderBottom: '1px solid var(--border-subtle)',
      }}
    >
      {children}
    </div>
  )
}

/** Read-only narrative render (used once the alert is no longer editable). */
function ReadOnlyNarrative({ text }: { text: string }) {
  return (
    <div style={{ fontSize: 14.5, lineHeight: 1.75, color: 'var(--text-1)', whiteSpace: 'pre-wrap' }}>
      {text.split('\n').map((line, i) =>
        /^[0-9]+\. [A-Z]/.test(line) ? (
          <div key={i} style={{ fontWeight: 600, marginTop: i ? 16 : 0 }}>
            {line}
          </div>
        ) : (
          <React.Fragment key={i}>
            {line}
            {'\n'}
          </React.Fragment>
        ),
      )}
    </div>
  )
}

/** The structured half of the SAR: cited indicators + recommended action. */
function SARStructuredBlock({ structured }: { structured: SARStructured }) {
  return (
    <>
      {structured.key_indicators.length > 0 && (
        <div style={{ marginTop: 28 }}>
          <DocH>Key indicators</DocH>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14, marginTop: 12 }}>
            {structured.key_indicators.map((k, i) => (
              <div key={i} style={{ display: 'flex', gap: 10 }}>
                <span style={{ color: 'var(--accent-text)', marginTop: 1, flexShrink: 0 }}>•</span>
                <div style={{ minWidth: 0 }}>
                  <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'baseline', gap: 8 }}>
                    <span style={{ fontWeight: 600, fontSize: 14, color: 'var(--text-1)' }}>{k.indicator}</span>
                    {k.regulation && (
                      <span
                        style={{
                          fontSize: 11.5,
                          fontFamily: 'var(--font-mono)',
                          color: 'var(--accent-text)',
                          background: 'var(--accent-subtle)',
                          border: '1px solid var(--border-subtle)',
                          borderRadius: 'var(--r-sm)',
                          padding: '1px 7px',
                        }}
                      >
                        {k.regulation}
                      </span>
                    )}
                  </div>
                  {k.description && (
                    <p style={{ fontSize: 13.5, color: 'var(--text-2)', lineHeight: 1.6, marginTop: 4 }}>
                      {k.description}
                    </p>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
      {structured.recommended_action && (
        <div style={{ marginTop: 28 }}>
          <DocH>Recommended action</DocH>
          <p style={{ fontSize: 14, color: 'var(--text-1)', lineHeight: 1.7, marginTop: 10 }}>
            {structured.recommended_action}
          </p>
        </div>
      )}
    </>
  )
}

// ── Particles ────────────────────────────────────────────────────────────

const PARTICLE_ANGLES = [0, 45, 90, 135, 180, 225, 270, 315]

function ParticleBurst() {
  return (
    <>
      {PARTICLE_ANGLES.map((deg) => {
        const radius = deg % 90 === 0 ? 40 : 35
        const rad = (deg * Math.PI) / 180
        const dx = Math.cos(rad) * radius
        const dy = Math.sin(rad) * radius
        return (
          <span
            key={deg}
            style={
              {
                position: 'absolute',
                left: '50%',
                top: '50%',
                width: 5,
                height: 5,
                marginLeft: -2.5,
                marginTop: -2.5,
                borderRadius: '50%',
                background: 'var(--success)',
                '--dx': `${dx}px`,
                '--dy': `${dy}px`,
                animation: 'particleFly 600ms cubic-bezier(0.4,0,0.2,1) 400ms forwards',
                opacity: 0,
                animationFillMode: 'forwards',
              } as React.CSSProperties
            }
          />
        )
      })}
    </>
  )
}

// ── Approval modal phases ────────────────────────────────────────────────

type ApprovePhase = 'confirm' | 'processing' | 'success'

const PROCESS_STEPS = [
  'Re-hydrating PII tokens',
  'Generating SAR PDF',
  'Delivering via webhook',
]

// ═════════════════════════════════════════════════════════════════════════

export function SARWorkspace() {
  const { alertId } = useParams<{ alertId: string }>()
  const navigate = useNavigate()
  const { user } = useAuthStore()
  const { toast } = useToast()
  const { data: alert, isLoading } = useAlert(alertId)
  const updateDraft = useUpdateDraft(alertId!)
  const approveMutation = useApproveAlert(alertId!)
  const rejectMutation = useRejectAlert(alertId!)

  // Split pane
  const [leftWidth, setLeftWidth] = useState<number>(loadLeftWidth)
  const [dragging, setDragging] = useState(false)
  const dragState = useRef<{ startX: number; startWidth: number } | null>(null)

  // Editor
  const editorRef = useRef<HTMLDivElement>(null)
  const [charCount, setCharCount] = useState(0)
  const [dirty, setDirty] = useState(false)
  const loadedDraftRef = useRef<string>('')

  // Accordions
  const [rawOpen, setRawOpen] = useState(false)
  const [cleanOpen, setCleanOpen] = useState(false)

  // Modals
  const [approveOpen, setApproveOpen] = useState(false)
  const [approvePhase, setApprovePhase] = useState<ApprovePhase>('confirm')
  const [stepProgress, setStepProgress] = useState(0) // how many steps are checked
  const [approvedAt, setApprovedAt] = useState<string | null>(null)
  const [rejectOpen, setRejectOpen] = useState(false)
  const [rejectReason, setRejectReason] = useState('')
  const [previewOpen, setPreviewOpen] = useState(false)
  const [previewText, setPreviewText] = useState<string | null>(null)
  const [previewLoading, setPreviewLoading] = useState(false)

  // ── Drag handlers ──────────────────────────────────────────────────────

  const onHandleDown = (e: React.MouseEvent) => {
    e.preventDefault()
    dragState.current = { startX: e.clientX, startWidth: leftWidth }
    setDragging(true)
    document.body.classList.add('dragging-panels')
  }

  useEffect(() => {
    if (!dragging) return
    const onMove = (e: MouseEvent) => {
      const ds = dragState.current
      if (!ds) return
      const next = Math.min(MAX_LEFT_PX, Math.max(MIN_LEFT_PX, ds.startWidth + (e.clientX - ds.startX)))
      setLeftWidth(next)
    }
    const onUp = () => {
      setDragging(false)
      dragState.current = null
      document.body.classList.remove('dragging-panels')
      setLeftWidth((w) => {
        localStorage.setItem(STORAGE_KEY, String(w))
        return w
      })
    }
    window.addEventListener('mousemove', onMove)
    window.addEventListener('mouseup', onUp)
    return () => {
      window.removeEventListener('mousemove', onMove)
      window.removeEventListener('mouseup', onUp)
    }
  }, [dragging])

  // ── Editor wiring ──────────────────────────────────────────────────────

  const draftText = alert?.sar_draft?.draft_text
  const editorHtml = useMemo(() => (draftText ? draftToHtml(draftText) : ''), [draftText])

  useEffect(() => {
    if (draftText !== undefined && draftText !== loadedDraftRef.current && editorRef.current) {
      // Only rewrite the DOM when server content actually changed (avoids caret jumps)
      if (!dirty) {
        const recovered = localStorage.getItem(`aegis_draft_${alertId}`)
        if (recovered && recovered !== draftText) {
          editorRef.current.innerHTML = draftToHtml(recovered)
          loadedDraftRef.current = recovered
          setCharCount(recovered.length)
          setDirty(true)
        } else {
          editorRef.current.innerHTML = editorHtml
          loadedDraftRef.current = draftText
          setCharCount(draftText.length)
        }
      }
    }
  }, [draftText, editorHtml, dirty, alertId])

  const readEditorText = useCallback((): string => {
    return editorRef.current?.innerText.replace(/\n{3,}/g, '\n\n') ?? ''
  }, [])

  const onEditorInput = () => {
    setDirty(true)
    const text = readEditorText()
    setCharCount(text.length)
    if (alertId) localStorage.setItem(`aegis_draft_${alertId}`, text)
  }

  const saveDraft = useCallback(() => {
    if (!dirty) return
    const text = readEditorText()
    loadedDraftRef.current = text
    updateDraft.mutate(text, {
      onSuccess: () => {
        setDirty(false)
        if (alertId) localStorage.removeItem(`aegis_draft_${alertId}`)
      },
    })
  }, [dirty, readEditorText, updateDraft, alertId])

  // ── Approve sequence ───────────────────────────────────────────────────

  const startApproval = () => {
    setApprovePhase('processing')
    setStepProgress(0)
    approveMutation.mutate(user?.fullName ?? 'Compliance Officer', {
      onSuccess: () => setApprovedAt(new Date().toISOString()),
    })
    // Sequential step animation: a check lands every 700ms
    setTimeout(() => setStepProgress(1), 700)
    setTimeout(() => setStepProgress(2), 1400)
    setTimeout(() => setStepProgress(3), 2100)
    setTimeout(() => setApprovePhase('success'), 2500)
  }

  useEffect(() => {
    if (approvePhase !== 'success') return
    const t = setTimeout(() => navigate('/queue'), 1200 + 4000)
    return () => clearTimeout(t)
  }, [approvePhase, navigate])

  // ── Preview ────────────────────────────────────────────────────────────

  const openPreview = async () => {
    saveDraft()
    setPreviewOpen(true)
    setPreviewLoading(true)
    try {
      setPreviewText(await previewRehydrated(alertId!))
    } finally {
      setPreviewLoading(false)
    }
  }

  // Download the finalized SAR PDF (exists once approved). Fetches the blob (tenant-auth'd)
  // so it saves with a proper filename instead of opening a blank tab.
  const downloadPdf = async (sarId: string) => {
    try {
      const blob = await downloadSarPdf(sarId)
      const href = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = href
      a.download = `SAR-${sarId}.pdf`
      document.body.appendChild(a)
      a.click()
      a.remove()
      URL.revokeObjectURL(href)
    } catch {
      toast('error', 'Download failed', 'The SAR PDF could not be fetched.')
    }
  }

  // ── Reject ─────────────────────────────────────────────────────────────

  const handleReject = () => {
    if (!rejectReason.trim()) return
    rejectMutation.mutate(rejectReason, {
      onSuccess: () => {
        setRejectOpen(false)
        toast('success', 'Alert rejected and cleared.')
        setTimeout(() => navigate('/queue'), 1500)
      },
    })
  }

  // ── Render ─────────────────────────────────────────────────────────────

  if (isLoading || !alert) {
    return (
      <div style={{ height: '100vh', display: 'flex', flexDirection: 'column', background: 'var(--bg-base)' }}>
        <div
          style={{
            height: 52,
            borderBottom: '1px solid var(--border-subtle)',
            display: 'flex',
            alignItems: 'center',
            padding: '0 16px',
            gap: 12,
          }}
        >
          <Skeleton width={28} height={28} />
          <Skeleton width={220} height={14} />
        </div>
        <div style={{ flex: 1, display: 'flex' }}>
          <div style={{ width: 400, padding: 24, display: 'flex', flexDirection: 'column', gap: 14, borderRight: '1px solid var(--border-subtle)' }}>
            <Skeleton width="55%" height={24} />
            <Skeleton width="80%" height={14} />
            <Skeleton width="100%" height={120} />
            <Skeleton width="90%" height={14} />
            <Skeleton width="70%" height={14} />
          </div>
          <div style={{ flex: 1, padding: 40 }}>
            <Skeleton width="40%" height={16} />
            <Skeleton width="100%" height={300} style={{ marginTop: 20 }} />
          </div>
        </div>
      </div>
    )
  }

  const compliance = alert.compliance
  const draft = alert.sar_draft
  const isPending = alert.status === 'PENDING_REVIEW'
  const structured = draft ? normalizeStructured(draft.draft_structured) : null

  return (
    <div style={{ height: '100vh', display: 'flex', flexDirection: 'column', overflow: 'hidden', background: 'var(--bg-base)' }}>
      {/* ── Header — breadcrumb left, actions right ── */}
      <div
        style={{
          height: 52,
          background: 'var(--bg-surface)',
          borderBottom: '1px solid var(--border-subtle)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '0 16px',
          flexShrink: 0,
          gap: 12,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, minWidth: 0 }}>
          <Button variant="ghost" size="sm" icon={<ChevronLeft size={15} />} onClick={() => navigate('/queue')} />
          <span style={{ fontSize: 13, color: 'var(--text-3)', whiteSpace: 'nowrap' }}>
            Alerts <span style={{ color: 'var(--text-4)', padding: '0 4px' }}>/</span>
          </span>
          <span style={{ fontSize: 13, fontFamily: 'var(--font-mono)', color: 'var(--text-1)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {alert.transaction_id}
          </span>
          <AlertStatusBadge status={alert.status} />
          <span style={{ fontSize: 12.5, color: 'var(--text-4)', whiteSpace: 'nowrap' }}>
            Received {timeAgo(alert.created_at)}
          </span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexShrink: 0 }}>
          <Button variant="secondary" size="sm" icon={<Eye size={13} />} onClick={openPreview}>
            Preview
          </Button>
          {/* The finalized SAR PDF exists once the alert is approved (auto or manual). */}
          {alert.status === 'APPROVED' && draft && (
            <Button variant="secondary" size="sm" icon={<Download size={13} />} onClick={() => downloadPdf(draft.id)}>
              Download PDF
            </Button>
          )}
          {/* Approve/Reject appear while an officer review is pending (the default,
              AUTO_APPROVE_SARS off). If auto-approve is on, the SAR arrives already
              delivered, so these controls are hidden. */}
          {isPending && (
            <>
              <Button
                variant="danger-ghost"
                size="sm"
                icon={<XCircle size={13} />}
                onClick={() => setRejectOpen(true)}
              >
                Reject
              </Button>
              <Button
                size="sm"
                icon={<Send size={13} />}
                onClick={() => {
                  saveDraft()
                  setApprovePhase('confirm')
                  setApproveOpen(true)
                }}
              >
                Approve &amp; send
              </Button>
            </>
          )}
        </div>
      </div>

      {/* ── Split body ── */}
      <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
        {/* LEFT — the record */}
        <aside
          style={{
            width: leftWidth,
            flexShrink: 0,
            background: 'var(--bg-surface)',
            overflowY: 'auto',
            padding: '20px 24px 32px',
            animation: 'fadeIn 200ms ease-out both',
          }}
        >
          {/* Amount block */}
          <div style={{ paddingBottom: 16, borderBottom: '1px solid var(--border-subtle)' }}>
            <div style={{ fontSize: 26, fontWeight: 600, letterSpacing: '-0.02em', fontVariantNumeric: 'tabular-nums' }}>
              {formatINR(alert.transaction_amount)}
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 6, flexWrap: 'wrap' }}>
              <span
                style={{
                  height: 20,
                  padding: '0 7px',
                  borderRadius: 'var(--r-sm)',
                  fontSize: 11,
                  fontWeight: 600,
                  letterSpacing: '0.03em',
                  display: 'inline-flex',
                  alignItems: 'center',
                  background: alert.transaction_direction === 'DEBIT' ? 'var(--danger-subtle)' : 'var(--success-subtle)',
                  color: alert.transaction_direction === 'DEBIT' ? 'var(--danger)' : 'var(--success)',
                }}
              >
                {alert.transaction_direction}
              </span>
              <span style={{ fontSize: 13, color: 'var(--text-3)' }}>
                {alert.transaction_type.replace(/_/g, ' ')} · {formatDateTime(alert.transaction_timestamp)}
              </span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 4, marginTop: 8 }}>
              <span style={{ fontSize: 12, fontFamily: 'var(--font-mono)', color: 'var(--text-3)' }}>
                {alert.transaction_id}
              </span>
              <CopyButton value={alert.transaction_id} size={12} />
            </div>
          </div>

          {/* Risk */}
          <SectionLabel>Risk</SectionLabel>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '4px 0' }}>
            <RiskScoreCell score={alert.risk_score} />
            <span
              style={{
                fontSize: 12,
                fontWeight: 600,
                letterSpacing: '0.03em',
                color: RISK_COLOR[compliance.overall_risk],
              }}
            >
              {compliance.overall_risk} RISK
            </span>
          </div>

          {/* Subject */}
          <SectionLabel>Subject</SectionLabel>
          <FieldRow label="Customer ref" value={String(alert.masked_payload.customer_name ?? '—')} masked />
          <FieldRow label="Account ref" value={String(alert.masked_payload.account_id ?? '—')} masked />
          <FieldRow label="IP address" value={String(alert.masked_payload.ip_address ?? '—')} masked />
          <FieldRow label="Device" value={String(alert.masked_payload.device_id ?? '—')} masked />

          {/* Counterparty */}
          <SectionLabel>Counterparty</SectionLabel>
          <FieldRow label="Account" value={String(alert.masked_payload.counterparty_account ?? '—')} masked />
          <FieldRow label="Institution" value={String(alert.masked_payload.counterparty_institution ?? '—')} />

          {/* AML analysis */}
          <SectionLabel>AML analysis</SectionLabel>

          {compliance.triggered_rules.length === 0 && alert.status === 'PROCESSING' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              <Skeleton height={72} />
              <Skeleton height={72} />
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: 'var(--text-3)', fontSize: 13 }}>
                <span className="spinner spinner-accent" />
                Running AML typology checks…
              </div>
            </div>
          )}

          {compliance.triggered_rules.map((rule: ComplianceRule, i: number) => (
            <div
              key={rule.rule_id}
              className="rule-card"
              style={{
                borderLeftColor: RISK_COLOR[rule.confidence] ?? 'var(--accent)',
                animation: `fadeInUp 200ms ease-out ${i * 40}ms both`,
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8 }}>
                <span style={{ fontSize: 13.5, fontWeight: 600, color: 'var(--text-1)' }}>{rule.rule_name}</span>
                <ConfidencePill confidence={rule.confidence} />
              </div>
              {rule.evidence.explanation && (
                <p style={{ fontSize: 13, color: 'var(--text-2)', marginTop: 6, lineHeight: 1.6 }}>
                  {rule.evidence.explanation}
                </p>
              )}
              {rule.evidence.field && (
                <div style={{ marginTop: 8 }}>
                  <span
                    style={{
                      background: 'var(--bg-elevated)',
                      border: '1px solid var(--border-subtle)',
                      fontSize: 11,
                      fontFamily: 'var(--font-mono)',
                      borderRadius: 'var(--r-sm)',
                      padding: '2px 6px',
                      color: 'var(--text-2)',
                    }}
                  >
                    {rule.evidence.field}
                    {rule.evidence.value !== undefined && ` = ${rule.evidence.value}`}
                  </span>
                </div>
              )}
            </div>
          ))}

          {/* Clean checks */}
          {compliance.clean_checks.length > 0 && (
            <div style={{ marginTop: 12 }}>
              <button
                onClick={() => setCleanOpen((o) => !o)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6,
                  background: 'none',
                  border: 'none',
                  color: 'var(--text-3)',
                  fontSize: 13,
                  cursor: 'pointer',
                  padding: 0,
                }}
              >
                <ChevronDown
                  size={14}
                  style={{ transition: 'transform 200ms', transform: cleanOpen ? 'rotate(180deg)' : 'none' }}
                />
                Clean checks ({compliance.clean_checks.length})
              </button>
              <div
                className="accordion-body"
                style={{ maxHeight: cleanOpen ? 300 : 0, opacity: cleanOpen ? 1 : 0 }}
              >
                <div style={{ paddingTop: 10, display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {compliance.clean_checks.map((c) => (
                    <div key={c.rule_id} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <Check size={11} color="var(--success)" style={{ flexShrink: 0 }} />
                      <span style={{ fontSize: 13, color: 'var(--text-3)' }}>{c.rule_name}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Raw JSON accordion */}
          <div style={{ marginTop: 16 }}>
            <button
              onClick={() => setRawOpen((o) => !o)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                background: 'none',
                border: 'none',
                color: 'var(--text-3)',
                fontSize: 13,
                cursor: 'pointer',
                padding: 0,
              }}
            >
              <ChevronDown
                size={14}
                style={{ transition: 'transform 200ms', transform: rawOpen ? 'rotate(180deg)' : 'none' }}
              />
              Raw JSON
            </button>
            <div className="accordion-body" style={{ maxHeight: rawOpen ? 600 : 0, opacity: rawOpen ? 1 : 0 }}>
              <div style={{ paddingTop: 12 }}>
                <CodeBlock code={JSON.stringify(alert.raw_payload, null, 2)} language="json" maxHeight={420} />
              </div>
            </div>
          </div>
        </aside>

        {/* Divider */}
        <div className={`drag-handle${dragging ? ' dragging' : ''}`} onMouseDown={onHandleDown} />

        {/* RIGHT — the document */}
        <section
          style={{
            flex: 1,
            minWidth: 0,
            display: 'flex',
            flexDirection: 'column',
            background: 'var(--bg-elevated)',
            animation: 'fadeIn 200ms ease-out 60ms both',
          }}
        >
          {/* Document toolbar */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '12px 28px',
              borderBottom: '1px solid var(--border-subtle)',
              flexShrink: 0,
              gap: 12,
            }}
          >
            <span style={{ fontSize: 13.5, fontWeight: 600, letterSpacing: '-0.01em' }}>SAR draft</span>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, minWidth: 0 }}>
              <span
                style={{
                  fontSize: 12,
                  color: 'var(--text-4)',
                  whiteSpace: 'nowrap',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                }}
              >
                {dirty
                  ? 'Unsaved edits — click outside to save'
                  : draft?.last_edited_at
                    ? `Last edited ${timeAgo(draft.last_edited_at)}`
                    : 'No edits yet'}
              </span>
              <span
                style={{
                  height: 22,
                  padding: '0 9px',
                  background: 'var(--bg-surface)',
                  border: '1px solid var(--border)',
                  borderRadius: 'var(--r-full)',
                  fontSize: 11,
                  fontFamily: 'var(--font-mono)',
                  color: 'var(--text-2)',
                  display: 'inline-flex',
                  alignItems: 'center',
                  whiteSpace: 'nowrap',
                }}
              >
                {draft ? 'AI-generated' : 'No draft'}
              </span>
            </div>
          </div>

          {/* Document canvas — the draft sits like a page on a desk */}
          <div style={{ flex: 1, overflowY: 'auto', padding: '28px 28px 40px' }}>
            <div
              style={{
                maxWidth: 760,
                margin: '0 auto',
                background: 'var(--bg-surface)',
                border: '1px solid var(--border)',
                borderRadius: 'var(--r-lg)',
                boxShadow: 'var(--shadow-sm)',
                padding: '40px 48px',
                minHeight: '100%',
              }}
            >
              {!draft ? (
                <div style={{ textAlign: 'center', color: 'var(--text-3)', fontSize: 14, padding: '48px 0' }}>
                  No SAR was generated — this alert completed clean.
                </div>
              ) : (
                <>
                  {/* Document title */}
                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'flex-start',
                      justifyContent: 'space-between',
                      gap: 12,
                      paddingBottom: 20,
                      marginBottom: 24,
                      borderBottom: '1px solid var(--border-subtle)',
                    }}
                  >
                    <div style={{ minWidth: 0 }}>
                      <div style={{ fontSize: 18, fontWeight: 700, letterSpacing: '-0.01em' }}>
                        Suspicious Transaction Report
                      </div>
                      <div style={{ fontSize: 12.5, color: 'var(--text-3)', marginTop: 3 }}>
                        {alert.transaction_type.replace(/_/g, ' ')} · {formatINR(alert.transaction_amount)} ·{' '}
                        <span style={{ fontFamily: 'var(--font-mono)' }}>{alert.transaction_id}</span>
                      </div>
                    </div>
                    <span
                      style={{
                        flexShrink: 0,
                        height: 22,
                        padding: '0 10px',
                        borderRadius: 'var(--r-sm)',
                        background: 'var(--accent-subtle)',
                        color: 'var(--accent-text)',
                        border: '1px solid var(--border-subtle)',
                        fontSize: 11,
                        fontWeight: 700,
                        letterSpacing: '0.04em',
                        display: 'inline-flex',
                        alignItems: 'center',
                      }}
                    >
                      STR
                    </span>
                  </div>

                  {/* Narrative — editable only while officer review is pending */}
                  <DocH>Narrative</DocH>
                  <div style={{ marginTop: 12 }}>
                    {isPending ? (
                      <div
                        ref={editorRef}
                        className="sar-editor"
                        contentEditable
                        suppressContentEditableWarning
                        spellCheck={false}
                        onInput={onEditorInput}
                        onBlur={saveDraft}
                      />
                    ) : (
                      <ReadOnlyNarrative text={draftText ?? ''} />
                    )}
                  </div>

                  {/* Structured half — cited indicators + recommended action */}
                  {structured && <SARStructuredBlock structured={structured} />}
                </>
              )}
            </div>
          </div>

          {/* Meta strip */}
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              padding: '8px 28px',
              borderTop: '1px solid var(--border-subtle)',
              fontSize: 12,
              color: 'var(--text-4)',
              flexShrink: 0,
              gap: 12,
            }}
          >
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, minWidth: 0, overflow: 'hidden', whiteSpace: 'nowrap' }}>
              <Sparkles size={12} style={{ flexShrink: 0 }} />
              {draft
                ? `Generated in ${(draft.generation_latency_ms / 1000).toFixed(1)}s · Aegis AI`
                : 'No SAR draft — this alert completed clean'}
            </span>
            <span style={{ whiteSpace: 'nowrap' }}>
              {(isPending ? charCount : draftText?.length ?? 0).toLocaleString('en-IN')} characters
            </span>
          </div>
        </section>
      </div>

      {/* ── Approve modal ── */}
      <Modal
        open={approveOpen}
        onClose={() => approvePhase === 'confirm' && setApproveOpen(false)}
        width={400}
        hideHeader
        dismissible={approvePhase === 'confirm'}
      >
        {approvePhase === 'confirm' && (
          <div className="anim-fade-in">
            <h3 style={{ fontSize: 15, fontWeight: 600, marginBottom: 16 }}>Confirm SAR approval</h3>
            <div
              style={{
                background: 'var(--bg-elevated)',
                border: '1px solid var(--border-subtle)',
                borderRadius: 'var(--r-md)',
                padding: 16,
                display: 'flex',
                flexDirection: 'column',
                gap: 10,
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ fontSize: 13, color: 'var(--text-3)' }}>Amount</span>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: 13, fontWeight: 500 }}>
                  {formatINR(alert.transaction_amount)}
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8 }}>
                <span style={{ fontSize: 13, color: 'var(--text-3)' }}>Rules</span>
                <span style={{ fontSize: 13, textAlign: 'right' }}>
                  {alert.triggered_rules.join(', ') || '—'}
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ fontSize: 13, color: 'var(--text-3)' }}>Officer</span>
                <span style={{ fontSize: 13 }}>{user?.fullName}</span>
              </div>
            </div>
            <div
              style={{
                marginTop: 16,
                padding: '10px 12px',
                background: 'var(--warning-subtle)',
                border: '1px solid rgba(154,103,0,0.25)',
                borderRadius: 'var(--r-md)',
                fontSize: 13,
                color: 'var(--warning)',
                display: 'flex',
                gap: 8,
                alignItems: 'flex-start',
              }}
            >
              <AlertTriangle size={14} style={{ flexShrink: 0, marginTop: 2 }} />
              This will re-hydrate real PII and deliver the SAR via webhook.
            </div>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, marginTop: 20 }}>
              <Button variant="secondary" onClick={() => setApproveOpen(false)}>
                Cancel
              </Button>
              <Button onClick={startApproval}>Confirm approval</Button>
            </div>
          </div>
        )}

        {approvePhase === 'processing' && (
          <div className="anim-fade-in" style={{ padding: '16px 4px', textAlign: 'center' }}>
            <div style={{ display: 'flex', justifyContent: 'center', marginBottom: 24 }}>
              <AegisShield size={32} float />
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 14, textAlign: 'left', maxWidth: 280, margin: '0 auto' }}>
              {PROCESS_STEPS.map((step, i) => {
                const done = stepProgress > i
                const active = stepProgress === i
                if (!done && !active) return null
                return (
                  <div
                    key={step}
                    className="anim-fade-in-up"
                    style={{ display: 'flex', alignItems: 'center', gap: 10, fontSize: 13 }}
                  >
                    {done ? (
                      <Check size={14} color="var(--success)" className="anim-fade-in" style={{ flexShrink: 0 }} />
                    ) : (
                      <span
                        className="pulse-dot"
                        style={{ background: 'var(--accent)', width: 8, height: 8, marginLeft: 3, marginRight: 3 }}
                      />
                    )}
                    <span style={{ color: done ? 'var(--text-2)' : 'var(--text-1)' }}>
                      {i === 2 && done ? 'Delivered — HMAC verified ✓' : `${step}${done ? '' : '...'}`}
                    </span>
                  </div>
                )
              })}
            </div>
          </div>
        )}

        {approvePhase === 'success' && (
          <div
            className="anim-fade-in"
            style={{
              padding: '24px 4px 8px',
              textAlign: 'center',
              position: 'relative',
            }}
          >
            <div style={{ position: 'relative', width: 64, height: 64, margin: '0 auto' }}>
              <svg width="64" height="64" viewBox="0 0 64 64">
                <circle
                  cx="32"
                  cy="32"
                  r="28"
                  stroke="var(--success)"
                  strokeWidth="2"
                  fill="var(--success-subtle)"
                />
                <polyline
                  points="20,33 28,41 44,23"
                  stroke="var(--success)"
                  strokeWidth="3"
                  fill="none"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeDasharray="120"
                  strokeDashoffset="120"
                  style={{ animation: 'drawCheckmark 500ms 200ms ease-out forwards' }}
                />
              </svg>
              <ParticleBurst />
            </div>
            <h3
              style={{
                fontSize: 18,
                fontWeight: 600,
                marginTop: 20,
                animation: 'fadeInUp 250ms ease-out 700ms both',
              }}
            >
              SAR approved &amp; delivered
            </h3>
            <div style={{ animation: 'fadeInUp 250ms ease-out 900ms both', marginTop: 10 }}>
              <div style={{ fontSize: 13, color: 'var(--text-3)' }}>
                {approvedAt ? formatDateTime(approvedAt) : ''}
              </div>
              <span
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: 4,
                  marginTop: 8,
                  height: 22,
                  padding: '0 10px',
                  borderRadius: 'var(--r-full)',
                  background: 'var(--success-subtle)',
                  color: 'var(--success)',
                  fontSize: 11,
                  fontWeight: 600,
                }}
              >
                HMAC verified ✓
              </span>
            </div>
            <div style={{ animation: 'fadeInUp 250ms ease-out 1200ms both', marginTop: 20, display: 'flex', flexDirection: 'column', gap: 10, alignItems: 'center' }}>
              <button
                onClick={() => navigate('/settings/webhook')}
                style={{ background: 'none', border: 'none', color: 'var(--accent-text)', fontSize: 13, cursor: 'pointer' }}
              >
                View delivery receipt →
              </button>
              <Button variant="secondary" onClick={() => navigate('/queue')}>
                Back to queue
              </Button>
            </div>
            <div
              style={{
                marginTop: 20,
                height: 3,
                background: 'var(--border-subtle)',
                borderRadius: 2,
                overflow: 'hidden',
                animation: 'fadeIn 200ms ease-out 1200ms both',
              }}
            >
              <div
                style={{
                  height: '100%',
                  background: 'var(--success)',
                  animation: 'progressShrink 4000ms linear 1200ms forwards',
                }}
              />
            </div>
          </div>
        )}
      </Modal>

      {/* ── Reject modal ── */}
      <Modal
        open={rejectOpen}
        onClose={() => setRejectOpen(false)}
        title="Reject alert"
        width={380}
        footer={
          <>
            <Button variant="secondary" onClick={() => setRejectOpen(false)}>
              Cancel
            </Button>
            <Button
              variant="danger"
              onClick={handleReject}
              loading={rejectMutation.isPending}
              disabled={!rejectReason.trim()}
            >
              Reject alert
            </Button>
          </>
        }
      >
        <p style={{ fontSize: 13, color: 'var(--text-3)', marginBottom: 12 }}>
          The alert will be cleared from the active queue and the reason logged to the audit trail.
        </p>
        <textarea
          className="input"
          style={{ minHeight: 80, width: '100%', padding: 10 }}
          placeholder="e.g. Reviewed — determined to be legitimate payroll disbursement."
          value={rejectReason}
          onChange={(e) => setRejectReason(e.target.value)}
          autoFocus
        />
      </Modal>

      {/* ── Preview rehydrated modal ── */}
      <Modal open={previewOpen} onClose={() => setPreviewOpen(false)} width={720} hideHeader>
        <div style={{ margin: -20 }}>
          <div
            style={{
              height: 44,
              background: 'var(--danger-subtle)',
              borderBottom: '1px solid rgba(192,57,43,0.25)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '0 20px',
              gap: 12,
            }}
          >
            <span style={{ fontSize: 12.5, color: 'var(--danger)', display: 'flex', alignItems: 'center', gap: 8, minWidth: 0 }}>
              <Lock size={13} style={{ flexShrink: 0 }} />
              Confidential — contains real PII. For officer review only. Not stored by Aegis.
            </span>
            <button
              onClick={() => setPreviewOpen(false)}
              aria-label="Close preview"
              style={{ background: 'none', border: 'none', color: 'var(--danger)', cursor: 'pointer', display: 'flex' }}
            >
              <X size={16} />
            </button>
          </div>
          <div style={{ padding: 20, maxHeight: 'calc(100vh - 220px)', overflowY: 'auto', background: 'var(--bg-elevated)' }}>
            {previewLoading ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                <Skeleton height={28} width="50%" />
                <Skeleton height={420} />
              </div>
            ) : (
              <div className="sar-document">
                <div className="sar-watermark">PREVIEW — NOT FOR DISTRIBUTION</div>
                {previewText?.split('\n').map((line, i) =>
                  /^[0-9]+\. [A-Z]/.test(line) ? (
                    <span key={i} className="doc-header">
                      {line}
                    </span>
                  ) : (
                    <React.Fragment key={i}>
                      {line}
                      {'\n'}
                    </React.Fragment>
                  ),
                )}
              </div>
            )}
          </div>
        </div>
      </Modal>
    </div>
  )
}
