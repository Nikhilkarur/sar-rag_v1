import { useState } from 'react'
import { CheckCircle2, ChevronDown, XCircle } from 'lucide-react'
import type { WebhookEvent } from '../types'
import { timeAgo } from '../utils/format'
import { CodeBlock } from './ui/CodeBlock'
import { HttpStatusBadge } from './ui/Badge'

export function WebhookEventCard({ event }: { event: WebhookEvent }) {
  const [expanded, setExpanded] = useState(false)

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
        {event.status === 'DELIVERED' ? (
          <CheckCircle2 size={16} color="var(--success)" style={{ flexShrink: 0 }} />
        ) : (
          <XCircle size={16} color="var(--danger)" style={{ flexShrink: 0 }} />
        )}
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
          {event.destination}
        </span>
        <HttpStatusBadge code={event.http_status} />
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
          <CodeBlock code={JSON.stringify(event.payload, null, 2)} language="json" maxHeight={300} />
        </div>
      </div>
    </div>
  )
}
