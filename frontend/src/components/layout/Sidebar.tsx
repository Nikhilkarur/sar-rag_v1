import React from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { useAuthStore } from '../../store/auth';
import { useAlerts } from '../../hooks/useAlerts';

const ShieldIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path d="M12 22S19.5 18 19.5 10V5L12 2L4.5 5V10C4.5 18 12 22 12 22Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
  </svg>
);

const NavItem = ({ to, icon, label, badgeCount = 0 }: { to: string; icon: React.ReactNode; label: string; badgeCount?: number }) => {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        `relative flex items-center h-9 px-3 rounded-md font-medium text-[13px] transition-all duration-100 ease-in-out ${
          isActive
            ? 'bg-surface-3 text-white'
            : 'text-ink-2 hover:bg-surface-2 hover:text-white'
        }`
      }
    >
      {({ isActive }) => (
        <>
          {isActive && (
            <div className="absolute left-0 top-1/2 -translate-y-1/2 w-[2px] h-4 bg-electric rounded-r-sm shadow-[0_0_8px_rgba(6,78,59,0.5)]" />
          )}
          <span className="w-5 h-5 flex items-center justify-center mr-2.5 opacity-80">
            {icon}
          </span>
          <span className="flex-1 truncate">{label}</span>
          {badgeCount > 0 && (
            <span className="flex items-center justify-center h-[18px] min-w-[18px] px-1 bg-risk-high text-white text-[11px] font-bold font-mono rounded-full animate-glow-pulse ml-2">
              {badgeCount}
            </span>
          )}
        </>
      )}
    </NavLink>
  );
};

export default function Sidebar() {
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();

  // Live pending-review count (shares the queue's cached query)
  const { data: alerts } = useAlerts(false);
  const pendingCount = alerts?.filter((a) => a.status === 'PENDING_REVIEW').length ?? 0;

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <div className="fixed inset-y-0 left-0 w-[240px] bg-surface border-r border-border-dim flex flex-col z-40">
      {/* Logo Row */}
      <div className="flex items-center h-[60px] px-5 shrink-0">
        <div className="text-electric mr-2">
          <ShieldIcon />
        </div>
        <div className="flex items-center space-x-1 font-display">
          <span className="text-[16px] font-bold text-white tracking-wide">AEGIS</span>
          <span className="text-[16px] font-bold text-electric tracking-wide">AML</span>
        </div>
      </div>

      {/* Navigation */}
      <div className="flex-1 overflow-y-auto px-3 py-4 space-y-8 scrollbar-hide">
        
        <div className="space-y-1">
          <div className="px-3 mb-2 text-[10px] uppercase font-mono tracking-widest text-ink-3">Main</div>
          <NavItem to="/dashboard" label="Dashboard" icon={
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="3" width="7" height="9" rx="1"/><rect x="14" y="3" width="7" height="5" rx="1"/><rect x="14" y="12" width="7" height="9" rx="1"/><rect x="3" y="16" width="7" height="5" rx="1"/></svg>
          } />
          <NavItem to="/queue" label="Review Queue" badgeCount={pendingCount} icon={
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>
          } />
          <NavItem to="/usage" label="Usage" icon={
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 20V10M18 20V4M6 20v-4"/></svg>
          } />
        </div>

        <div className="space-y-1">
          <div className="px-3 mb-2 text-[10px] uppercase font-mono tracking-widest text-ink-3 border-t border-border-dim pt-6">Settings</div>
          <NavItem to="/settings/credentials" label="Credentials" icon={
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
          } />
          <NavItem to="/settings/webhook" label="Webhook" icon={
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M18 8c0 4.5-6 6-6 12M6 8c0 4.5 6 6 6 12M8 4h8M12 2v2"/></svg>
          } />
          <NavItem to="/settings/schema" label="Ingestion Schema" icon={
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/></svg>
          } />
          <NavItem to="/settings/llm" label="LLM Config" icon={
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>
          } />
        </div>

        {user?.role === 'SUPER_ADMIN' && (
          <div className="space-y-1">
            <div className="px-3 mb-2 text-[10px] uppercase font-mono tracking-widest text-ink-3 border-t border-border-dim pt-6">Admin</div>
            <NavItem to="/admin/verifications" label="Verifications" icon={
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/></svg>
            } />
            <NavItem to="/admin/customers" label="Customers" icon={
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/></svg>
            } />
          </div>
        )}
      </div>

      {/* User Profile */}
      <div className="h-[56px] shrink-0 border-t border-border-dim px-4 py-3 flex items-center justify-between hover:bg-surface-2 transition-colors cursor-pointer group" onClick={handleLogout} title="Click to logout">
        <div className="flex items-center space-x-3 overflow-hidden">
          <div className="w-8 h-8 rounded-full bg-border-strong flex items-center justify-center shrink-0 text-white font-medium text-[11px]">
            {user?.email?.charAt(0).toUpperCase() || 'U'}
          </div>
          <div className="flex flex-col truncate">
            <span className="text-[13px] font-medium text-white truncate">{user?.fullName || 'User'}</span>
            <span className="text-[11px] font-mono text-ink-3 truncate">{user?.role}</span>
          </div>
        </div>
        <svg className="w-4 h-4 text-ink-3 opacity-0 group-hover:opacity-100 transition-opacity" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>
      </div>
    </div>
  );
}
