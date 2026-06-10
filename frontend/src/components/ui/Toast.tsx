import React, { createContext, useCallback, useContext, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { AlertTriangle, CheckCircle2, Info, X, XCircle } from 'lucide-react'

type ToastType = 'success' | 'error' | 'info' | 'warning'

interface ToastItem {
  id: number
  type: ToastType
  title: string
  description?: string
  exiting?: boolean
}

interface ToastContextValue {
  toast: (type: ToastType, title: string, description?: string) => void
}

const ToastContext = createContext<ToastContextValue>({ toast: () => {} })

export const useToast = () => useContext(ToastContext)

const COLORS: Record<ToastType, string> = {
  success: 'var(--success)',
  error: 'var(--danger)',
  warning: 'var(--warning)',
  info: 'var(--accent)',
}

const ICONS: Record<ToastType, React.ReactNode> = {
  success: <CheckCircle2 size={16} color="var(--success)" />,
  error: <XCircle size={16} color="var(--danger)" />,
  warning: <AlertTriangle size={16} color="var(--warning)" />,
  info: <Info size={16} color="var(--accent)" />,
}

const AUTO_DISMISS_MS = 4000
const MAX_TOASTS = 4

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([])
  const idRef = useRef(0)

  const dismiss = useCallback((id: number) => {
    setToasts((prev) => prev.map((t) => (t.id === id ? { ...t, exiting: true } : t)))
    setTimeout(() => setToasts((prev) => prev.filter((t) => t.id !== id)), 220)
  }, [])

  const toast = useCallback(
    (type: ToastType, title: string, description?: string) => {
      const id = ++idRef.current
      setToasts((prev) => {
        const next = [...prev, { id, type, title, description }]
        return next.length > MAX_TOASTS ? next.slice(next.length - MAX_TOASTS) : next
      })
      setTimeout(() => dismiss(id), AUTO_DISMISS_MS)
    },
    [dismiss],
  )

  return (
    <ToastContext.Provider value={{ toast }}>
      {children}
      {createPortal(
        <div
          style={{
            position: 'fixed',
            right: 24,
            bottom: 24,
            display: 'flex',
            flexDirection: 'column-reverse',
            gap: 8,
            zIndex: 9999,
          }}
        >
          {toasts.map((t) => (
            <div
              key={t.id}
              style={{
                width: 320,
                background: 'var(--bg-surface)',
                border: '1px solid var(--border)',
                borderLeft: `3px solid ${COLORS[t.type]}`,
                boxShadow: 'var(--shadow-lg)',
                borderRadius: 'var(--r-lg)',
                overflow: 'hidden',
                position: 'relative',
                animation: t.exiting
                  ? 'toastSlideOut 200ms ease-in forwards'
                  : 'toastSlideIn 300ms cubic-bezier(0.4,0,0.2,1)',
              }}
            >
              <div style={{ display: 'flex', gap: 10, padding: '12px 14px', alignItems: 'flex-start' }}>
                <span style={{ marginTop: 1, flexShrink: 0 }}>{ICONS[t.type]}</span>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 14, fontWeight: 500, color: 'var(--text-1)' }}>{t.title}</div>
                  {t.description && (
                    <div style={{ fontSize: 13, color: 'var(--text-3)', marginTop: 2 }}>
                      {t.description}
                    </div>
                  )}
                </div>
                <button
                  onClick={() => dismiss(t.id)}
                  style={{
                    background: 'none',
                    border: 'none',
                    color: 'var(--text-4)',
                    cursor: 'pointer',
                    padding: 0,
                    display: 'flex',
                    transition: 'color var(--t-fast)',
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.color = 'var(--text-1)')}
                  onMouseLeave={(e) => (e.currentTarget.style.color = 'var(--text-4)')}
                >
                  <X size={14} />
                </button>
              </div>
              <div
                style={{
                  height: 4,
                  background: COLORS[t.type],
                  animation: `progressShrink ${AUTO_DISMISS_MS}ms linear forwards`,
                }}
              />
            </div>
          ))}
        </div>,
        document.body,
      )}
    </ToastContext.Provider>
  )
}
