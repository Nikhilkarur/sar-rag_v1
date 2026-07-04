import { useState } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import Sidebar from './Sidebar';
import { AdminSidebar } from './AdminSidebar';
import TopBar from './TopBar';
import { CommandPalette } from '../ui/CommandPalette';

export default function AppLayout({ admin = false }: { admin?: boolean }) {
  const location = useLocation();
  const isWorkspace = location.pathname.includes('/queue/');

  // Collapsible sidebar — toggled from the TopBar, remembered across reloads.
  const [collapsed, setCollapsed] = useState(() => {
    try { return localStorage.getItem('aegis-sidebar-collapsed') === '1'; } catch { return false; }
  });
  const toggleSidebar = () =>
    setCollapsed((c) => {
      const next = !c;
      try { localStorage.setItem('aegis-sidebar-collapsed', next ? '1' : '0'); } catch { /* ignore */ }
      return next;
    });

  const showSidebar = !isWorkspace && !collapsed;

  return (
    <div className="min-h-screen flex font-sans" style={{ background: 'var(--bg-base)', color: 'var(--text-1)' }}>
      <CommandPalette />

      {/* Sidebar (hidden on the full-screen workspace, or when collapsed).
          The tenant Sidebar is position:fixed (out of flow) so the content needs a left
          margin to clear it. The AdminSidebar is position:sticky (in-flow flex child), so it
          already reserves its width in the row — adding a margin there double-offsets it. */}
      {showSidebar && (admin ? <AdminSidebar /> : <Sidebar />)}

      {/* Main Content Area */}
      <div className={`flex flex-col flex-1 min-w-0 ${showSidebar && !admin ? 'ml-[232px]' : ''}`}>
        <TopBar onToggleSidebar={isWorkspace ? undefined : toggleSidebar} sidebarCollapsed={collapsed} />

        {/* Scroll container — re-keyed per route for a quiet fade between pages */}
        <main className={`flex-1 overflow-x-hidden ${isWorkspace ? '' : 'px-8 py-8'}`}>
          <div key={location.pathname} className={isWorkspace ? undefined : 'page-enter mx-auto max-w-[1200px]'}>
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}

export { AppLayout };
