import React, { useEffect, useMemo, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { useNavigate } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import {
  Activity,
  BarChart2,
  Building2,
  Cpu,
  Database,
  FileText,
  Inbox,
  KeyRound,
  LayoutDashboard,
  Search,
  UserCheck,
  Webhook,
  Zap,
} from 'lucide-react'
import { useAuthStore } from '../store/auth'
import type { AlertDetail } from '../types'
import { formatINR } from '../utils/format'

interface PaletteProps {
  open: boolean
  onClose: () => void
}

interface ResultItem {
  id: string
  group: 'Pages' | 'Alerts'
  label: string
  icon: React.ReactNode
  right?: string
  to: string
}

/** Subsequence fuzzy match; returns matched indices or null. */
function fuzzyMatch(query: string, text: string): number[] | null {
  const q = query.toLowerCase()
  const t = text.toLowerCase()
  const indices: number[] = []
  let ti = 0
  for (const ch of q) {
    if (ch === ' ') continue
    const found = t.indexOf(ch, ti)
    if (found === -1) return null
    indices.push(found)
    ti = found + 1
  }
  return indices
}

function Highlighted({ text, indices }: { text: string; indices: number[] }) {
  const set = new Set(indices)
  return (
    <span>
      {text.split('').map((ch, i) =>
        set.has(i) ? (
          <span key={i} style={{ color: 'var(--accent-text)', fontWeight: 600 }}>
            {ch}
          </span>
        ) : (
          <span key={i}>{ch}</span>
        ),
      )}
    </span>
  )
}

export function CommandPalette({ open, onClose }: PaletteProps) {
  const [query, setQuery] = useState('')
  const [selected, setSelected] = useState(0)
  const navigate = useNavigate()
  const qc = useQueryClient()
  const { user } = useAuthStore()
  const inputRef = useRef<HTMLInputElement>(null)
  const listRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (open) {
      setQuery('')
      setSelected(0)
      setTimeout(() => inputRef.current?.focus(), 50)
    }
  }, [open])

  const isSuperAdmin = user?.role === 'SUPER_ADMIN'

  const allItems = useMemo<ResultItem[]>(() => {
    const pages: ResultItem[] = isSuperAdmin
      ? [
          { id: 'p-ver', group: 'Pages', label: 'Verifications', icon: <UserCheck size={15} />, to: '/admin/verifications' },
          { id: 'p-cust', group: 'Pages', label: 'Customers', icon: <Building2 size={15} />, to: '/admin/customers' },
          { id: 'p-logs', group: 'Pages', label: 'API Logs', icon: <Activity size={15} />, to: '/admin/logs' },
          { id: 'p-groq', group: 'Pages', label: 'Groq Usage', icon: <Zap size={15} />, to: '/admin/groq' },
        ]
      : [
          { id: 'p-dash', group: 'Pages', label: 'Dashboard', icon: <LayoutDashboard size={15} />, to: '/dashboard' },
          { id: 'p-queue', group: 'Pages', label: 'Review Queue', icon: <Inbox size={15} />, to: '/queue' },
          { id: 'p-usage', group: 'Pages', label: 'Usage', icon: <BarChart2 size={15} />, to: '/usage' },
          { id: 'p-cred', group: 'Pages', label: 'API Credentials', icon: <KeyRound size={15} />, to: '/settings/credentials' },
          { id: 'p-wh', group: 'Pages', label: 'Webhook Settings', icon: <Webhook size={15} />, to: '/settings/webhook' },
          { id: 'p-schema', group: 'Pages', label: 'Alert Schema', icon: <Database size={15} />, to: '/settings/schema' },
          { id: 'p-llm', group: 'Pages', label: 'LLM Config', icon: <Cpu size={15} />, to: '/settings/llm' },
        ]

    const cachedAlerts = qc.getQueryData<AlertDetail[]>(['alerts']) ?? []
    const alerts: ResultItem[] = isSuperAdmin
      ? []
      : cachedAlerts.slice(0, 8).map((a) => ({
          id: `a-${a.id}`,
          group: 'Alerts' as const,
          label: a.transaction_id,
          icon: <FileText size={15} />,
          right: formatINR(a.transaction_amount),
          to: `/queue/${a.id}`,
        }))

    return [...pages, ...alerts]
  }, [isSuperAdmin, qc, open])

  const results = useMemo(() => {
    if (!query.trim()) return allItems.map((item) => ({ item, indices: [] as number[] }))
    return allItems
      .map((item) => ({ item, indices: fuzzyMatch(query, item.label) }))
      .filter((r): r is { item: ResultItem; indices: number[] } => r.indices !== null)
  }, [query, allItems])

  useEffect(() => setSelected(0), [query])

  useEffect(() => {
    const el = listRef.current?.children[selected] as HTMLElement | undefined
    el?.scrollIntoView({ block: 'nearest' })
  }, [selected])

  if (!open) return null

  const go = (item: ResultItem) => {
    navigate(item.to)
    onClose()
  }

  const handleKey = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setSelected((s) => Math.min(s + 1, results.length - 1))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setSelected((s) => Math.max(s - 1, 0))
    } else if (e.key === 'Enter' && results[selected]) {
      go(results[selected].item)
    } else if (e.key === 'Escape') {
      onClose()
    }
  }

  let lastGroup = ''

  return createPortal(
    <div
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose()
      }}
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(0,0,0,0.65)',
        backdropFilter: 'blur(4px)',
        zIndex: 2000,
        animation: 'fadeIn 150ms ease-out',
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'flex-start',
        paddingTop: '18vh',
      }}
    >
      <div
        style={{
          width: 560,
          maxWidth: 'calc(100vw - 40px)',
          background: 'var(--bg-surface)',
          border: '1px solid var(--border)',
          boxShadow: 'var(--shadow-lg)',
          borderRadius: 'var(--r-xl)',
          overflow: 'hidden',
          animation: 'scaleIn 200ms ease-out',
        }}
      >
        <div
          style={{
            height: 48,
            display: 'flex',
            alignItems: 'center',
            gap: 10,
            padding: '0 16px',
            borderBottom: '1px solid var(--border)',
          }}
        >
          <Search size={16} color="var(--text-4)" />
          <input
            ref={inputRef}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKey}
            placeholder="Search pages, alerts..."
            style={{
              flex: 1,
              background: 'transparent',
              border: 'none',
              outline: 'none',
              fontSize: 16,
              color: 'var(--text-1)',
              fontFamily: 'var(--font-sans)',
            }}
          />
          <span className="kbd">esc</span>
        </div>
        <div ref={listRef} style={{ maxHeight: 320, overflowY: 'auto', padding: '4px 0' }}>
          {results.length === 0 ? (
            <div style={{ padding: 32, textAlign: 'center', color: 'var(--text-3)', fontSize: 14 }}>
              No results for “{query}”
            </div>
          ) : (
            results.map(({ item, indices }, i) => {
              const showHeader = item.group !== lastGroup
              lastGroup = item.group
              return (
                <React.Fragment key={item.id}>
                  {showHeader && (
                    <div className="label-upper" style={{ color: 'var(--text-4)', padding: '8px 16px 4px' }}>
                      {item.group}
                    </div>
                  )}
                  <div
                    onClick={() => go(item)}
                    onMouseEnter={() => setSelected(i)}
                    style={{
                      height: 40,
                      padding: '0 16px',
                      display: 'flex',
                      alignItems: 'center',
                      gap: 10,
                      cursor: 'pointer',
                      background: i === selected ? 'var(--bg-elevated)' : 'transparent',
                      color: 'var(--text-2)',
                      fontSize: 14,
                    }}
                  >
                    <span style={{ color: 'var(--text-3)', display: 'flex' }}>{item.icon}</span>
                    <span style={{ flex: 1, color: 'var(--text-1)' }}>
                      {indices.length > 0 ? (
                        <Highlighted text={item.label} indices={indices} />
                      ) : (
                        item.label
                      )}
                    </span>
                    {item.right && (
                      <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12, color: 'var(--text-3)' }}>
                        {item.right}
                      </span>
                    )}
                  </div>
                </React.Fragment>
              )
            })
          )}
        </div>
      </div>
    </div>,
    document.body,
  )
}
