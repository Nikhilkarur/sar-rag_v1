import React, { useEffect } from 'react'
import { createPortal } from 'react-dom'
import { X } from 'lucide-react'

interface ModalProps {
  open: boolean
  onClose: () => void
  title?: React.ReactNode
  width?: number
  dismissible?: boolean
  children: React.ReactNode
  footer?: React.ReactNode
  hideHeader?: boolean
}

export function Modal({
  open,
  onClose,
  title,
  width = 480,
  dismissible = true,
  children,
  footer,
  hideHeader,
}: ModalProps) {
  useEffect(() => {
    if (!open) return
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && dismissible) onClose()
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [open, dismissible, onClose])

  if (!open) return null

  return createPortal(
    <div
      onMouseDown={(e) => {
        if (e.target === e.currentTarget && dismissible) onClose()
      }}
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(0,0,0,0.65)',
        backdropFilter: 'blur(4px)',
        WebkitBackdropFilter: 'blur(4px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1000,
        animation: 'fadeIn 200ms ease-out',
        padding: 20,
      }}
    >
      <div
        style={{
          background: 'var(--bg-surface)',
          border: '1px solid var(--border)',
          boxShadow: 'var(--shadow-lg)',
          borderRadius: 'var(--r-xl)',
          width: '100%',
          maxWidth: width,
          maxHeight: 'calc(100vh - 80px)',
          display: 'flex',
          flexDirection: 'column',
          animation: 'scaleIn 200ms ease-out',
          overflow: 'hidden',
        }}
      >
        {!hideHeader && (title || dismissible) && (
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '16px 20px',
              borderBottom: '1px solid var(--border-subtle)',
              flexShrink: 0,
            }}
          >
            <h3 style={{ fontSize: 16, fontWeight: 600, letterSpacing: '-0.01em' }}>{title}</h3>
            {dismissible && (
              <button
                onClick={onClose}
                aria-label="Close"
                style={{
                  width: 32,
                  height: 32,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  background: 'transparent',
                  border: 'none',
                  borderRadius: 'var(--r-md)',
                  color: 'var(--text-3)',
                  cursor: 'pointer',
                  transition: 'background var(--t-fast), color var(--t-fast)',
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = 'var(--bg-elevated)'
                  e.currentTarget.style.color = 'var(--text-1)'
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = 'transparent'
                  e.currentTarget.style.color = 'var(--text-3)'
                }}
              >
                <X size={16} />
              </button>
            )}
          </div>
        )}
        <div style={{ padding: 20, overflowY: 'auto', flex: 1 }}>{children}</div>
        {footer && (
          <div
            style={{
              display: 'flex',
              justifyContent: 'flex-end',
              gap: 8,
              padding: '16px 20px',
              borderTop: '1px solid var(--border-subtle)',
              flexShrink: 0,
            }}
          >
            {footer}
          </div>
        )}
      </div>
    </div>,
    document.body,
  )
}
