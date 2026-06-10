import { useEffect, useState } from 'react'
import { Outlet, useLocation } from 'react-router-dom'
import { Sidebar } from './Sidebar'
import { AdminSidebar } from './AdminSidebar'
import { TopBar } from './TopBar'
import { CommandPalette } from '../CommandPalette'

const TITLES: Record<string, string> = {
  '/dashboard': 'Dashboard',
  '/queue': 'Review Queue',
  '/usage': 'Usage & Analytics',
  '/settings/credentials': 'API Credentials',
  '/settings/webhook': 'Webhook',
  '/settings/schema': 'Alert Schema',
  '/settings/llm': 'LLM Configuration',
  '/admin/verifications': 'Verification Queue',
  '/admin/customers': 'Customers',
  '/admin/logs': 'API Logs',
  '/admin/groq': 'Groq Usage',
}

interface AppLayoutProps {
  admin?: boolean
}

export function AppLayout({ admin }: AppLayoutProps) {
  const [paletteOpen, setPaletteOpen] = useState(false)
  const location = useLocation()

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault()
        setPaletteOpen((o) => !o)
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [])

  const title = TITLES[location.pathname] ?? 'Aegis AML'
  const isWorkspace = /^\/queue\/.+/.test(location.pathname)

  return (
    <div style={{ display: 'flex', minHeight: '100vh' }}>
      {!isWorkspace && (admin ? <AdminSidebar /> : <Sidebar />)}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
        {!isWorkspace && <TopBar title={title} onOpenPalette={() => setPaletteOpen(true)} />}
        <main
          key={location.pathname}
          className="page-enter"
          style={
            isWorkspace
              ? { flex: 1, minWidth: 0 }
              : {
                  flex: 1,
                  padding: '40px 24px',
                  maxWidth: 1400,
                  width: '100%',
                  margin: '0 auto',
                  minWidth: 0,
                }
          }
        >
          <Outlet />
        </main>
      </div>
      <CommandPalette open={paletteOpen} onClose={() => setPaletteOpen(false)} />
    </div>
  )
}
