import { useState } from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
import {
  Activity,
  Building2,
  ChevronLeft,
  ChevronRight,
  ExternalLink,
  LogOut,
  UserCheck,
  Zap,
} from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { useAuthStore } from '../../store/auth'
import { listVerifications } from '../../api/admin'
import { AegisShield } from '../AegisLogo'
import { cls } from '../../utils/format'

export function AdminSidebar() {
  const [collapsed, setCollapsed] = useState(false)
  const { user, clearAuth } = useAuthStore()
  const navigate = useNavigate()
  const { data: verifications } = useQuery({
    queryKey: ['verifications'],
    queryFn: listVerifications,
    refetchInterval: 10000,
  })
  const pendingCount = verifications?.length ?? 0

  const nav = [
    {
      to: '/admin/verifications',
      label: 'Verifications',
      icon: <UserCheck size={16} />,
      badge: pendingCount,
    },
    { to: '/admin/customers', label: 'Customers', icon: <Building2 size={16} /> },
    { to: '/admin/logs', label: 'API Logs', icon: <Activity size={16} /> },
    { to: '/admin/llm', label: 'LLM Usage', icon: <Zap size={16} /> },
  ]

  return (
    <aside
      style={{
        width: collapsed ? 64 : 232,
        height: '100vh',
        background: 'var(--bg-elevated)',
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
          <div>
            <div className="font-logo" style={{ fontSize: 13, lineHeight: 1.3, whiteSpace: 'nowrap' }}>
              <span style={{ color: 'var(--text-1)' }}>AEGIS</span>{' '}
              <span style={{ color: 'var(--accent)' }}>AML</span>
            </div>
            <div style={{ fontSize: 11, color: 'var(--text-3)', whiteSpace: 'nowrap' }}>
              Admin Console
            </div>
          </div>
        )}
      </div>

      <nav style={{ flex: 1, padding: 8, display: 'flex', flexDirection: 'column', gap: 2 }}>
        {nav.map((item) => (
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
        ))}

        <div style={{ height: 1, background: 'var(--border-subtle)', margin: '12px 8px' }} />
        <a
          href="/dashboard"
          target="_blank"
          rel="noreferrer"
          className="nav-item"
          title={collapsed ? 'View Client Portal' : undefined}
          style={collapsed ? { justifyContent: 'center', padding: 0 } : undefined}
        >
          <ExternalLink size={16} />
          {!collapsed && <span>View Client Portal</span>}
        </a>
      </nav>

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
            marginLeft: collapsed ? 12 : 4,
          }}
        >
          {collapsed ? <ChevronRight size={14} /> : <ChevronLeft size={14} />}
        </button>
      </div>

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
            background: 'var(--accent-subtle)',
            color: 'var(--accent-text)',
            fontSize: 13,
            fontWeight: 600,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexShrink: 0,
          }}
        >
          {(user?.fullName ?? 'A').charAt(0).toUpperCase()}
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
              <div style={{ fontSize: 11, color: 'var(--text-3)' }}>Super Admin</div>
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
