import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  AlertTriangle,
  Check,
  ChevronDown,
  ChevronLeft,
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
import { RiskGauge } from '../../components/ui/RiskGauge'
import { CopyButton } from '../../components/ui/CopyButton'
import { AlertStatusBadge, ConfidencePill, RulePill } from '../../components/ui/Badge'
import { Skeleton } from '../../components/ui/Skeleton'
import { AegisShield } from '../../components/AegisLogo'
import { previewRehydrated } from '../../api/alerts'
import { formatINR, timeAgo, formatDateTime } from '../../utils/format'
import type { ComplianceRule } from '../../types'

// ── Panel sizing ─────────────────────────────────────────────────────────

const STORAGE_KEY = 'aegis-panel-widths'
const MIN_PANEL_PX = 280

function loadWidths(): [number, number, number] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) {
      const parsed = JSON.parse(raw)
      if (Array.isArray(parsed) && parsed.length === 3) return parsed as [number, number, number]
    }
  } catch {
    /* corrupted — use defaults */
  }
  return [1, 1, 1.4]
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

const RISK_BADGE: Record<string, { bg: string; color: string }> = {
  HIGH: { bg: 'var(--danger-subtle)', color: 'var(--danger)' },
  MEDIUM: { bg: 'var(--warning-subtle)', color: 'var(--warning)' },
  LOW: { bg: 'var(--success-subtle)', color: 'var(--success)' },
}

const CONF_BORDER: Record<string, string> = {
  HIGH: 'var(--danger)',
  MEDIUM: 'var(--warning)',
  LOW: 'var(--success)',
}

function FieldRow({ label, value, masked }: { label: string; value: string; masked?: boolean }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '6px 0' }}>
      <span className="label-upper" style={{ minWidth: 96, flexShrink: 0 }}>
        {label}
      </span>
      <span
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: 6,
          fontSize: masked ? 13 : 14,
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

  // Panels
  const [widths, setWidths] = useState<[number, number, number]>(loadWidths)
  const containerRef = useRef<HTMLDivElement>(null)
  const [draggingHandle, setDraggingHandle] = useState<number | null>(null)
  const dragState = useRef<{ handle: number; startX: number; startWidths: [number, number, number] } | null>(null)

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

  const onHandleDown = (handle: number) => (e: React.MouseEvent) => {
    e.preventDefault()
    dragState.current = { handle, startX: e.clientX, startWidths: [...widths] as [number, number, number] }
    setDraggingHandle(handle)
    document.body.classList.add('dragging-panels')
  }

  useEffect(() => {
    if (draggingHandle === null) return
    const onMove = (e: MouseEvent) => {
      const ds = dragState.current
      const container = containerRef.current
      if (!ds || !container) return
      const totalPx = container.clientWidth - 12 // minus two 6px handles
      const totalFr = ds.startWidths[0] + ds.startWidths[1] + ds.startWidths[2]
      const deltaFr = ((e.clientX - ds.startX) / totalPx) * totalFr
      const minFr = (MIN_PANEL_PX / totalPx) * totalFr
      const next: [number, number, number] = [...ds.startWidths] as [number, number, number]
      const i = ds.handle
      let d = deltaFr
      d = Math.max(d, minFr - ds.startWidths[i])
      d = Math.min(d, ds.startWidths[i + 1] - minFr)
      next[i] = ds.startWidths[i] + d
      next[i + 1] = ds.startWidths[i + 1] - d
      setWidths(next)
    }
    const onUp = () => {
      setDraggingHandle(null)
      dragState.current = null
      document.body.classList.remove('dragging-panels')
      setWidths((w) => {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(w))
        return w
      })
    }
    window.addEventListener('mousemove', onMove)
    window.addEventListener('mouseup', onUp)
    return () => {
      window.removeEventListener('mousemove', onMove)
      window.removeEventListener('mouseup', onUp)
    }
  }, [draggingHandle])

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
      <div style={{ height: '100vh', display: 'flex', flexDirection: 'column' }}>
        <div
          style={{
            height: 48,
            background: 'var(--bg-surface)',
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
        <div style={{ flex: 1, display: 'grid', gridTemplateColumns: '1fr 6px 1fr 6px 1.4fr' }}>
          {[0, 1, 2].map((i) => (
            <React.Fragment key={i}>
              {i > 0 && <div className="drag-handle" />}
              <div style={{ padding: 24, display: 'flex', flexDirection: 'column', gap: 14 }}>
                <Skeleton width="55%" height={22} />
                <Skeleton width="80%" height={14} />
                <Skeleton width="100%" height={120} />
                <Skeleton width="90%" height={14} />
                <Skeleton width="70%" height={14} />
                <Skeleton width="100%" height={180} />
              </div>
            </React.Fragment>
          ))}
        </div>
      </div>
    )
  }

  const compliance = alert.compliance
  const draft = alert.sar_draft
  const isPending = alert.status === 'PENDING_REVIEW'
  const overallStyle = RISK_BADGE[compliance.overall_risk]

  return (
    <div style={{ height: '100vh', display: 'flex', flexDirection: 'column', overflow: 'hidden', background: 'var(--bg-base)' }}>
      {/* Header bar */}
      <div
        style={{
          height: 48,
          background: 'var(--bg-surface)',
          borderBottom: '1px solid var(--border-subtle)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '0 16px',
          flexShrink: 0,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <Button variant="ghost" size="sm" icon={<ChevronLeft size={15} />} onClick={() => navigate('/queue')} />
          <span style={{ fontSize: 13, fontFamily: 'var(--font-mono)', color: 'var(--text-3)' }}>
            Queue <span style={{ color: 'var(--text-4)' }}>/</span>{' '}
            <span style={{ color: 'var(--text-1)' }}>{alert.transaction_id}</span>
          </span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <AlertStatusBadge status={alert.status} />
          <span style={{ fontSize: 12, color: 'var(--text-4)' }}>Received {timeAgo(alert.created_at)}</span>
        </div>
      </div>

      {/* 3-panel grid */}
      <div
        ref={containerRef}
        style={{
          display: 'grid',
          gridTemplateColumns: `${widths[0]}fr 6px ${widths[1]}fr 6px ${widths[2]}fr`,
          height: 'calc(100vh - 48px)',
          overflow: 'hidden',
        }}
      >
        {/* ── PANEL 1 — Transaction Intelligence ── */}
        <section
          style={{
            background: 'var(--bg-surface)',
            overflowY: 'auto',
            padding: 24,
            animation: 'fadeInUp 300ms ease-out 0ms both',
            minWidth: 0,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 20 }}>
            <span
              className="label-upper"
              style={{
                background: 'var(--bg-elevated)',
                padding: '3px 8px',
                borderRadius: 'var(--r-sm)',
              }}
            >
              Transaction Data
            </span>
          </div>

          {/* Amount block */}
          <div style={{ marginBottom: 20 }}>
            <div style={{ fontSize: 28, fontWeight: 700, letterSpacing: '-0.02em', fontVariantNumeric: 'tabular-nums' }}>
              {formatINR(alert.transaction_amount)}
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 8 }}>
              <span
                style={{
                  height: 22,
                  padding: '0 8px',
                  borderRadius: 'var(--r-full)',
                  fontSize: 11,
                  fontWeight: 600,
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

          {/* Risk gauge */}
          <div style={{ display: 'flex', justifyContent: 'center', padding: '8px 0 20px' }}>
            <RiskGauge score={alert.risk_score} />
          </div>

          <div style={{ height: 1, background: 'var(--border-subtle)', margin: '4px 0 16px' }} />
          <div className="label-upper" style={{ marginBottom: 8 }}>
            Subject
          </div>
          <FieldRow label="Customer Ref" value={String(alert.masked_payload.customer_name ?? '—')} masked />
          <FieldRow label="Account Ref" value={String(alert.masked_payload.account_id ?? '—')} masked />
          <FieldRow label="IP Address" value={String(alert.masked_payload.ip_address ?? '—')} masked />
          <FieldRow label="Device" value={String(alert.masked_payload.device_id ?? '—')} masked />

          <div style={{ height: 1, background: 'var(--border-subtle)', margin: '16px 0' }} />
          <div className="label-upper" style={{ marginBottom: 8 }}>
            Counterparty
          </div>
          <FieldRow label="Account" value={String(alert.masked_payload.counterparty_account ?? '—')} masked />
          <FieldRow label="Institution" value={String(alert.masked_payload.counterparty_institution ?? '—')} />

          {/* Raw JSON accordion */}
          <div style={{ marginTop: 24 }}>
            <button
              onClick={() => setRawOpen((o) => !o)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                background: 'none',
                border: 'none',
                color: 'var(--text-2)',
                fontSize: 13,
                cursor: 'pointer',
                padding: 0,
              }}
            >
              <ChevronDown
                size={14}
                style={{ transition: 'transform 200ms', transform: rawOpen ? 'rotate(180deg)' : 'none' }}
              />
              View Raw JSON
            </button>
            <div className="accordion-body" style={{ maxHeight: rawOpen ? 600 : 0, opacity: rawOpen ? 1 : 0 }}>
              <div style={{ paddingTop: 12 }}>
                <CodeBlock code={JSON.stringify(alert.raw_payload, null, 2)} language="json" maxHeight={420} />
              </div>
            </div>
          </div>
        </section>

        {/* Handle 1 */}
        <div
          className={`drag-handle${draggingHandle === 0 ? ' dragging' : ''}`}
          onMouseDown={onHandleDown(0)}
        />

        {/* ── PANEL 2 — Compliance Analysis ── */}
        <section
          style={{
            background: 'var(--bg-base)',
            overflowY: 'auto',
            padding: 24,
            animation: 'fadeInUp 300ms ease-out 80ms both',
            minWidth: 0,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20 }}>
            <h3 style={{ fontSize: 16, fontWeight: 600, letterSpacing: '-0.01em' }}>AML Analysis</h3>
            <span
              style={{
                height: 26,
                padding: '0 10px',
                borderRadius: 'var(--r-full)',
                fontSize: 12,
                fontWeight: 600,
                display: 'inline-flex',
                alignItems: 'center',
                gap: 6,
                background: overallStyle.bg,
                color: overallStyle.color,
              }}
            >
              {compliance.overall_risk === 'HIGH' && <AlertTriangle size={12} />}
              {compliance.overall_risk} RISK
            </span>
          </div>

          {compliance.triggered_rules.length === 0 && alert.status === 'PROCESSING' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              <Skeleton height={86} />
              <Skeleton height={86} />
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
                borderLeftColor: CONF_BORDER[rule.confidence],
                animation: `fadeInUp 250ms ease-out ${i * 60}ms both`,
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8 }}>
                <span style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-1)' }}>{rule.rule_name}</span>
                <ConfidencePill confidence={rule.confidence} />
              </div>
              {rule.evidence.explanation && (
                <p style={{ fontSize: 13, fontStyle: 'italic', color: 'var(--text-3)', marginTop: 6, lineHeight: 1.6 }}>
                  {rule.evidence.explanation}
                </p>
              )}
              {rule.evidence.field && (
                <div style={{ marginTop: 10 }}>
                  <span
                    style={{
                      background: 'var(--bg-elevated)',
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
            <div style={{ marginTop: 16 }}>
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
                Clean Checks ({compliance.clean_checks.length})
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
        </section>

        {/* Handle 2 */}
        <div
          className={`drag-handle${draggingHandle === 1 ? ' dragging' : ''}`}
          onMouseDown={onHandleDown(1)}
        />

        {/* ── PANEL 3 — SAR Draft ── */}
        <section
          style={{
            background: 'var(--bg-surface)',
            display: 'flex',
            flexDirection: 'column',
            animation: 'fadeInUp 300ms ease-out 160ms both',
            minWidth: 0,
            overflow: 'hidden',
          }}
        >
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '16px 24px',
              borderBottom: '1px solid var(--border-subtle)',
              flexShrink: 0,
            }}
          >
            <h3 style={{ fontSize: 16, fontWeight: 600, letterSpacing: '-0.01em' }}>SAR Draft</h3>
            <span
              style={{
                height: 22,
                padding: '0 10px',
                background: 'var(--bg-elevated)',
                border: '1px solid var(--border)',
                borderRadius: 'var(--r-full)',
                fontSize: 11,
                fontFamily: 'var(--font-mono)',
                color: 'var(--text-2)',
                display: 'inline-flex',
                alignItems: 'center',
              }}
            >
              {draft ? `Groq · ${draft.llm_model.replace('-versatile', '')}` : 'No draft'}
            </span>
          </div>

          <div style={{ flex: 1, overflowY: 'auto', padding: '8px 16px 0' }}>
            <div
              ref={editorRef}
              className="sar-editor"
              contentEditable={isPending}
              suppressContentEditableWarning
              spellCheck={false}
              onInput={onEditorInput}
              onBlur={saveDraft}
            />
          </div>

          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              padding: '6px 24px',
              fontSize: 12,
              color: 'var(--text-4)',
              flexShrink: 0,
            }}
          >
            <span>{charCount.toLocaleString('en-IN')} characters</span>
            <span>
              {dirty
                ? 'Unsaved edits — click outside to save'
                : draft?.last_edited_at
                  ? `Last edited by you, ${timeAgo(draft.last_edited_at)}`
                  : 'No edits yet'}
            </span>
          </div>

          {/* Action bar */}
          <div
            style={{
              height: 64,
              borderTop: '1px solid var(--border-subtle)',
              padding: '0 24px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              flexShrink: 0,
              gap: 12,
            }}
          >
            <span style={{ fontSize: 12, color: 'var(--text-4)', display: 'inline-flex', alignItems: 'center', gap: 6, minWidth: 0, overflow: 'hidden', whiteSpace: 'nowrap' }}>
              <Sparkles size={12} style={{ flexShrink: 0 }} />
              {draft
                ? `Generated in ${(draft.generation_latency_ms / 1000).toFixed(1)}s · Groq ${draft.llm_model.replace('-versatile', '')}`
                : 'No SAR draft — this alert completed clean'}
            </span>
            <div style={{ display: 'flex', gap: 8, flexShrink: 0 }}>
              <Button variant="secondary" size="sm" icon={<Eye size={13} />} onClick={openPreview}>
                Preview
              </Button>
              <Button
                variant="danger-ghost"
                size="sm"
                icon={<XCircle size={13} />}
                onClick={() => setRejectOpen(true)}
                disabled={!isPending}
              >
                Reject
              </Button>
              <Button
                icon={<Send size={14} />}
                onClick={() => {
                  saveDraft()
                  setApprovePhase('confirm')
                  setApproveOpen(true)
                }}
                disabled={!isPending}
              >
                Approve & Send ↗
              </Button>
            </div>
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
            <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 16 }}>Confirm SAR Approval</h3>
            <div
              style={{
                background: 'var(--bg-base)',
                border: '1px solid var(--border-subtle)',
                borderRadius: 'var(--r-md)',
                padding: 16,
                display: 'flex',
                flexDirection: 'column',
                gap: 10,
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span className="label-upper">Amount</span>
                <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 500 }}>
                  {formatINR(alert.transaction_amount)}
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8 }}>
                <span className="label-upper">Rules</span>
                <span style={{ display: 'flex', gap: 4, flexWrap: 'wrap', justifyContent: 'flex-end' }}>
                  {alert.triggered_rules.map((r) => (
                    <RulePill key={r} rule={r} />
                  ))}
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span className="label-upper">Officer</span>
                <span style={{ fontSize: 13 }}>{user?.fullName}</span>
              </div>
            </div>
            <div
              style={{
                marginTop: 16,
                padding: '10px 12px',
                background: 'var(--warning-subtle)',
                border: '1px solid rgba(160,116,26,0.3)',
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
              <Button
                style={{ background: 'var(--success)', color: '#fff' }}
                onClick={startApproval}
              >
                Confirm Approval
              </Button>
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
                      {i === 2 && done ? 'Delivered — HMAC Verified ✓' : `${step}${done ? '' : '...'}`}
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
              animation: 'successGlow 2s ease-in-out infinite',
              borderRadius: 'var(--r-lg)',
            }}
          >
            <div style={{ position: 'relative', width: 64, height: 64, margin: '0 auto' }}>
              <svg width="64" height="64" viewBox="0 0 64 64">
                <circle
                  cx="32"
                  cy="32"
                  r="28"
                  stroke="var(--success)"
                  strokeWidth="2.5"
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
                fontSize: 20,
                fontWeight: 600,
                marginTop: 20,
                animation: 'fadeInUp 250ms ease-out 700ms both',
              }}
            >
              SAR Approved & Delivered
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
                HMAC Verified ✓
              </span>
            </div>
            <div style={{ animation: 'fadeInUp 250ms ease-out 1200ms both', marginTop: 20, display: 'flex', flexDirection: 'column', gap: 10, alignItems: 'center' }}>
              <button
                onClick={() => navigate('/settings/webhook')}
                style={{ background: 'none', border: 'none', color: 'var(--accent-text)', fontSize: 13, cursor: 'pointer' }}
              >
                View Delivery Receipt →
              </button>
              <Button variant="secondary" onClick={() => navigate('/queue')}>
                Back to Queue
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
        title="Reject Alert"
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
              Reject Alert
            </Button>
          </>
        }
      >
        <p style={{ fontSize: 13, color: 'var(--text-3)', marginBottom: 12 }}>
          The alert will be cleared from the active queue and the reason logged to the audit trail.
        </p>
        <textarea
          className="input"
          style={{ minHeight: 80, width: '100%' }}
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
              height: 48,
              background: 'var(--danger-subtle)',
              borderBottom: '1px solid rgba(179,56,44,0.3)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '0 20px',
              gap: 12,
            }}
          >
            <span style={{ fontSize: 13, color: 'var(--danger)', display: 'flex', alignItems: 'center', gap: 8, minWidth: 0 }}>
              <Lock size={14} style={{ flexShrink: 0 }} />
              Confidential — Contains Real PII. For officer review only. Not stored by Aegis.
            </span>
            <button
              onClick={() => setPreviewOpen(false)}
              aria-label="Close preview"
              style={{ background: 'none', border: 'none', color: 'var(--danger)', cursor: 'pointer', display: 'flex' }}
            >
              <X size={16} />
            </button>
          </div>
          <div style={{ padding: 20, maxHeight: 'calc(100vh - 220px)', overflowY: 'auto' }}>
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
