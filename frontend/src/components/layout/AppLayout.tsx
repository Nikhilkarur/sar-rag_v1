import { Outlet, useLocation } from 'react-router-dom';
import Sidebar from './Sidebar';
import { AdminSidebar } from './AdminSidebar';
import TopBar from './TopBar';
import { CommandPalette } from '../ui/CommandPalette';

export default function AppLayout({ admin = false }: { admin?: boolean }) {
  const location = useLocation();
  const isWorkspace = location.pathname.includes('/queue/');

  return (
    <div className="min-h-screen flex font-sans" style={{ background: 'var(--bg-base)', color: 'var(--text-1)' }}>
      <CommandPalette />

      {/* Fixed Sidebar */}
      {!isWorkspace && (admin ? <AdminSidebar /> : <Sidebar />)}

      {/* Main Content Area */}
      <div className={`flex flex-col flex-1 min-w-0 ${isWorkspace ? '' : 'ml-[232px]'}`}>
        <TopBar />

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
