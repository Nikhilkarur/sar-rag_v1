import { useState } from 'react'
import { AlertTriangle, CheckCircle2, ChevronDown, Clock, HelpCircle, RotateCcw, XCircle } from 'lucide-react'
import { useQueryClient } from '@tanstack/react-query'
import type { WebhookEvent } from '../types'
import { timeAgo } from '../utils/format'
import { redeliverWebhookEvent } from '../api/tenant'
import { CodeBlock } from './ui/CodeBlock'
import { HttpStatusBadge } from './ui/Badge'
import { Button } from './ui/Button'
import { useToast } from './ui/Toast'

function StatusIcon({ status }: { status: WebhookEvent['status'] }) {
  const style = { flexShrink: 0 }
  switch (status) {
    case 'DELIVERED':
      return <CheckCircle2 size={16} color="var(--success)" style={style} />
    case 'FAILED':
      return <XCircle size={16} color="var(--danger)" style={style} />
    case 'PENDING':
    case 'RETRYING':
      return <Clock size={16} color="var(--text-3)" style={style} />
    case 'STALLED':
      return <AlertTriangle size={16} color="var(--warning)" style={style} />
    default:
      return <HelpCircle size={16} color="var(--text-4)" style={style} />
  }
}

const STATUS_TEXT: Record<WebhookEvent['status'], string> = {
  DELIVERED: 'Delivered',
  FAILED: 'Delivery failed',
  PENDING: 'Sending…',
  RETRYING: 'Retrying…',
  STALLED: 'Interrupted — outcome unknown',
  UNKNOWN: 'Outcome not recorded (sent before delivery tracking)',
}

export function WebhookEventCard({ event }: { event: WebhookEvent }) {
  const [expanded, setExpanded] = useState(false)
  const [redelivering, setRedelivering] = useState(false)
  const qc = useQueryClient()
  const { toast } = useToast()
  const isApproval = (event.event ?? '').startsWith('sar.approved')
  const canRedeliver = isApproval && ['FAILED', 'STALLED', 'UNKNOWN'].includes(event.status)

  const handleRedeliver = async () => {
    setRedelivering(true)
    try {
      const result = await redeliverWebhookEvent(event.id)
      toast('success', 'SAR re-delivery started', `Sending to ${result.destination}.`)
    } catch (err) {
      const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail
      toast('error', 'Re-delivery not started', typeof detail === 'string' ? detail : 'Please try again.')
    } finally {
      setRedelivering(false)
      qc.invalidateQueries({ queryKey: ['webhook-events'] })
    }
  }

  return (
    <div
      style={{
        background: 'var(--bg-surface)',
        border: '1px solid var(--border-subtle)',
        borderRadius: 'var(--r-md)',
        overflow: 'hidden',
        transition: 'border-color var(--t-base)',
      }}
    >
      <button
        onClick={() => setExpanded((e) => !e)}
        title={`${event.status}${event.attempts ? ` after ${event.attempts} attempt(s)` : ''}${event.error ? ` — ${event.error}` : ''}`}
        style={{
          width: '100%',
          height: 48,
          display: 'flex',
          alignItems: 'center',
          gap: 12,
          padding: '0 16px',
          background: 'transparent',
          border: 'none',
          cursor: 'pointer',
          color: 'var(--text-1)',
          transition: 'background var(--t-fast)',
        }}
        onMouseEnter={(e) => (e.currentTarget.style.background = 'var(--bg-elevated)')}
        onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
      >
        <StatusIcon status={event.status} />
        <span style={{ fontSize: 13, color: 'var(--text-3)', width: 80, textAlign: 'left', flexShrink: 0 }}>
          {timeAgo(event.received_at)}
        </span>
        <span
          style={{
            fontSize: 13,
            fontFamily: 'var(--font-mono)',
            color: 'var(--text-2)',
            flex: 1,
            textAlign: 'left',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
          }}
        >
          {event.destination ?? '—'}
        </span>
        {event.http_status != null && <HttpStatusBadge code={event.http_status} />}
        <span
          style={{
            fontSize: 11,
            fontWeight: 500,
            color: event.hmac_valid ? 'var(--success)' : 'var(--danger)',
            display: 'inline-flex',
            alignItems: 'center',
            gap: 4,
            flexShrink: 0,
          }}
        >
          {event.hmac_valid ? 'Verified ✓' : 'Failed ✗'}
        </span>
        <ChevronDown
          size={14}
          color="var(--text-4)"
          style={{
            transition: 'transform 200ms ease-out',
            transform: expanded ? 'rotate(180deg)' : 'rotate(0deg)',
            flexShrink: 0,
          }}
        />
      </button>
      <div
        className="accordion-body"
        style={{ maxHeight: expanded ? 400 : 0, opacity: expanded ? 1 : 0 }}
      >
        <div style={{ padding: '0 16px 16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 10, fontSize: 12.5 }}>
            <span style={{ color: 'var(--text-2)', flex: 1 }}>
              {STATUS_TEXT[event.status] ?? event.status}
              {event.attempts ? ` · ${event.attempts} attempt${event.attempts === 1 ? '' : 's'}` : ''}
              {event.error ? ` · ${event.error}` : ''}
            </span>
            {canRedeliver && (
              <Button variant="secondary" size="sm" icon={<RotateCcw size={13} />} onClick={handleRedeliver} loading={redelivering}>
                Re-deliver
              </Button>
            )}
          </div>
          <CodeBlock code={JSON.stringify(event.payload, null, 2)} language="json" maxHeight={260} />
        </div>
      </div>
    </div>
  )
}
