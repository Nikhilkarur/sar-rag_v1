import React from 'react'

interface EmptyStateProps {
  icon: React.ReactNode
  title: string
  description: string
  action?: React.ReactNode
}

export function EmptyState({ icon, title, description, action }: EmptyStateProps) {
  return (
    <div
      className="anim-fade-in"
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 48,
        textAlign: 'center',
        gap: 8,
      }}
    >
      <div style={{ color: 'var(--text-4)', marginBottom: 8 }}>{icon}</div>
      <h3 style={{ fontSize: 16, fontWeight: 600, color: 'var(--text-2)' }}>{title}</h3>
      <p style={{ fontSize: 14, color: 'var(--text-3)', maxWidth: 360 }}>{description}</p>
      {action && <div style={{ marginTop: 16 }}>{action}</div>}
    </div>
  )
}

export function ShieldCheckIllustration({ size = 64 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" fill="none">
      <path
        d="M32 4 L56 14 V30 C56 44 46 55 32 60 C18 55 8 44 8 30 V14 Z"
        stroke="currentColor"
        strokeWidth="2.5"
        strokeLinejoin="round"
        fill="none"
      />
      <path
        d="M22 32 L29 39 L43 24"
        stroke="currentColor"
        strokeWidth="3"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}
