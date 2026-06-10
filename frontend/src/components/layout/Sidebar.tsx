import { useState } from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
import {
  BarChart2,
  ChevronLeft,
  ChevronRight,
  Cpu,
  Database,
  Inbox,
  KeyRound,
  LayoutDashboard,
  LogOut,
  Webhook,
} from 'lucide-react'
import { useAuthStore } from '../../store/auth'
import { useAlerts } from '../../hooks/useAlerts'
import { AegisShield } from '../AegisLogo'
import { cls } from '../../utils/format'

interface NavEntry {
  to: string
  label: string
  icon: React.ReactNode
  badge?: number
}

export function Sidebar() {
  const [collapsed, setCollapsed] = useState(false)
  const { user, clearAuth } = useAuthStore()
  const navigate = useNavigate()
  const { data: alerts } = useAlerts()
  const pendingCount = alerts?.filter((a) => a.status === 'PENDING_REVIEW').length ?? 0

  const mainNav: NavEntry[] = [
    { to: '/dashboard', label: 'Dashboard', icon: <LayoutDashboard size={16} /> },
    { to: '/queue', label: 'Review Queue', icon: <Inbox size={16} />, badge: pendingCount },
    { to: '/usage', label: 'Usage', icon: <BarChart2 size={16} /> },
  ]

  const settingsNav: NavEntry[] = [
    { to: '/settings/credentials', label: 'API Credentials', icon: <KeyRound size={16} /> },
    { to: '/settings/webhook', label: 'Webhook', icon: <Webhook size={16} /> },
    { to: '/settings/schema', label: 'Alert Schema', icon: <Database size={16} /> },
    { to: '/settings/llm', label: 'LLM Config', icon: <Cpu size={16} /> },
  ]

  const isAdmin = user?.role === 'TENANT_ADMIN'
  const initial = (user?.fullName ?? 'U').charAt(0).toUpperCase()

  const renderItem = (item: NavEntry) => (
    <NavLink
      key={item.to}
      to={item.to}
      className={({ isActive }) => cls('nav-item', isActive && 'active')}
      title={collapsed ? item.label : undefined}
      style={collapsed ? { justifyContent: 'center', padding: 0 } : undefined}
    >
      {item.icon}
      {!collapsed && <span style={{ flex: 1 }}>{item.label}</span>}
      {!collapsed && item.badge !== undefined && item.badge > 0 && (
        <span
          style={{
            minWidth: 20,
            height: 20,
            padding: '0 6px',
            borderRadius: 'var(--r-full)',
            background: item.badge > 2 ? 'var(--danger)' : 'var(--warning)',
            color: '#fff',
            fontSize: 11,
            fontWeight: 500,
            display: 'inline-flex',
            alignItems: 'center',
            justifyContent: 'center',
            animation: 'processingPulse 2s infinite',
          }}
        >
          {item.badge}
        </span>
      )}
    </NavLink>
  )

  return (
    <aside
      style={{
        width: collapsed ? 64 : 240,
        height: '100vh',
        background: 'var(--bg-surface)',
        borderRight: '1px solid var(--border-subtle)',
        display: 'flex',
        flexDirection: 'column',
        flexShrink: 0,
        transition: 'width 250ms cubic-bezier(0.4,0,0.2,1)',
        position: 'sticky',
        top: 0,
        overflow: 'hidden',
      }}
    >
      {/* Logo */}
      <div
        style={{
          height: 64,
          display: 'flex',
          alignItems: 'center',
          padding: collapsed ? '0 0 0 20px' : '0 16px',
          gap: 8,
          flexShrink: 0,
        }}
      >
        <AegisShield size={24} />
        {!collapsed && (
          <div style={{ minWidth: 0 }}>
            <div style={{ fontSize: 16, fontWeight: 700, lineHeight: 1.2, whiteSpace: 'nowrap' }}>
              <span style={{ color: 'var(--text-1)' }}>AEGIS</span>{' '}
              <span style={{ color: 'var(--accent)' }}>AML</span>
            </div>
            <div
              style={{
                fontSize: 12,
                color: 'var(--text-3)',
                whiteSpace: 'nowrap',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
              }}
            >
              {user?.tenant?.name}
            </div>
          </div>
        )}
      </div>

      {/* Nav */}
      <nav style={{ flex: 1, padding: '8px 8px', display: 'flex', flexDirection: 'column', gap: 2, overflowY: 'auto' }}>
        {mainNav.map(renderItem)}
        {isAdmin && (
          <>
            {!collapsed ? (
              <div
                className="label-upper"
                style={{ color: 'var(--text-4)', padding: '8px 12px', marginTop: 8 }}
              >
                Settings
              </div>
            ) : (
              <div style={{ height: 1, background: 'var(--border-subtle)', margin: '12px 8px' }} />
            )}
            {settingsNav.map(renderItem)}
          </>
        )}
      </nav>

      {/* Collapse */}
      <div style={{ padding: '0 8px 8px', flexShrink: 0 }}>
        <button
          onClick={() => setCollapsed((c) => !c)}
          aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          style={{
            width: 24,
            height: 24,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            background: 'transparent',
            border: '1px solid var(--border-subtle)',
            borderRadius: 'var(--r-sm)',
            color: 'var(--text-3)',
            cursor: 'pointer',
            transition: 'background var(--t-fast), color var(--t-fast)',
            marginLeft: collapsed ? 12 : 4,
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
          {collapsed ? <ChevronRight size={14} /> : <ChevronLeft size={14} />}
        </button>
      </div>

      {/* User */}
      <div
        style={{
          height: 64,
          borderTop: '1px solid var(--border-subtle)',
          display: 'flex',
          alignItems: 'center',
          padding: collapsed ? '0 0 0 16px' : '0 16px',
          gap: 10,
          flexShrink: 0,
        }}
      >
        <div
          style={{
            width: 32,
            height: 32,
            borderRadius: '50%',
            background: 'var(--accent)',
            color: '#fff',
            fontSize: 14,
            fontWeight: 600,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexShrink: 0,
          }}
        >
          {initial}
        </div>
        {!collapsed && (
          <>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div
                style={{
                  fontSize: 13,
                  fontWeight: 500,
                  color: 'var(--text-1)',
                  whiteSpace: 'nowrap',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                }}
              >
                {user?.fullName}
              </div>
              <div style={{ fontSize: 11, color: 'var(--text-3)' }}>
                {user?.role === 'TENANT_ADMIN' ? 'Compliance Admin' : 'Compliance Officer'}
              </div>
            </div>
            <button
              onClick={() => {
                clearAuth()
                navigate('/login')
              }}
              aria-label="Log out"
              style={{
                background: 'none',
                border: 'none',
                color: 'var(--text-4)',
                cursor: 'pointer',
                display: 'flex',
                padding: 4,
                transition: 'color var(--t-fast)',
              }}
              onMouseEnter={(e) => (e.currentTarget.style.color = 'var(--danger)')}
              onMouseLeave={(e) => (e.currentTarget.style.color = 'var(--text-4)')}
            >
              <LogOut size={16} />
            </button>
          </>
        )}
      </div>
    </aside>
  )
}
