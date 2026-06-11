import { Outlet, useLocation } from 'react-router-dom';
import Sidebar from './Sidebar';
import { AdminSidebar } from './AdminSidebar';
import TopBar from './TopBar';
import { CommandPalette } from '../ui/CommandPalette';

export default function AppLayout({ admin = false }: { admin?: boolean }) {
  const location = useLocation();
  const isWorkspace = location.pathname.includes('/queue/');

  return (
    <div className="min-h-screen bg-obsidian flex text-white font-sans selection:bg-electric-dim selection:text-white">
      <CommandPalette />

      {/* Fixed Sidebar */}
      {!isWorkspace && (admin ? <AdminSidebar /> : <Sidebar />)}

      {/* Main Content Area */}
      <div className={`flex flex-col flex-1 min-w-0 ${isWorkspace ? '' : 'ml-[240px]'}`}>
        <TopBar />
        
        {/* The main scrollable container — re-keyed per route so every
            page sweeps in like a new chamber of the citadel */}
        <main className={`flex-1 overflow-x-hidden ${isWorkspace ? '' : 'p-10'}`}>
          <div key={location.pathname} className={isWorkspace ? undefined : 'page-enter'}>
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}

export { AppLayout };
