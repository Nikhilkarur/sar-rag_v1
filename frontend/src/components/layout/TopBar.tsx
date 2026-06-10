import { Bell } from 'lucide-react'
import { useAuthStore } from '../../store/auth'

interface TopBarProps {
  title: string
  onOpenPalette: () => void
}

export function TopBar({ title, onOpenPalette }: TopBarProps) {
  const { user } = useAuthStore()
  const isMac = typeof navigator !== 'undefined' && /Mac/i.test(navigator.platform)

  return (
    <header
      style={{
        height: 64,
        background: 'var(--bg-base)',
        borderBottom: '1px solid var(--border-subtle)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0 24px',
        flexShrink: 0,
        position: 'sticky',
        top: 0,
        zIndex: 40,
      }}
    >
      <h2 style={{ fontSize: 20, fontWeight: 600, letterSpacing: '-0.015em', color: 'var(--text-1)' }}>
        {title}
      </h2>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <button
          onClick={onOpenPalette}
          style={{
            height: 28,
            padding: '0 10px',
            background: 'var(--bg-elevated)',
            border: '1px solid var(--border)',
            borderRadius: 'var(--r-md)',
            color: 'var(--text-3)',
            fontFamily: 'var(--font-mono)',
            fontSize: 12,
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: 6,
            transition: 'border-color var(--t-fast), color var(--t-fast)',
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.borderColor = 'var(--border-strong)'
            e.currentTarget.style.color = 'var(--text-1)'
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.borderColor = 'var(--border)'
            e.currentTarget.style.color = 'var(--text-3)'
          }}
        >
          {isMac ? '⌘K' : 'Ctrl K'}
        </button>
        <button
          aria-label="Notifications"
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
          <Bell size={16} />
        </button>
        <div
          style={{
            width: 28,
            height: 28,
            borderRadius: '50%',
            background: user?.role === 'SUPER_ADMIN' ? 'var(--warning)' : 'var(--accent)',
            color: user?.role === 'SUPER_ADMIN' ? '#000' : '#fff',
            fontSize: 12,
            fontWeight: 600,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          {(user?.fullName ?? 'U').charAt(0).toUpperCase()}
        </div>
      </div>
    </header>
  )
}
