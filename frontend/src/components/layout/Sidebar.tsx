import React from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { useAuthStore } from '../../store/auth';
import { AegisShield } from '../AegisLogo';

const NavItem = ({ to, icon, label, badgeCount = 0 }: { to: string; icon: React.ReactNode; label: string; badgeCount?: number }) => {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        `relative flex items-center h-8 px-2.5 rounded-md text-[13px] transition-colors duration-100 ${
          isActive
            ? 'bg-surface-3 text-ink-1 font-medium'
            : 'text-ink-2 hover:bg-surface-2 hover:text-ink-1'
        }`
      }
    >
      <span className="w-4 h-4 flex items-center justify-center mr-2.5 text-ink-3">
        {icon}
      </span>
      <span className="flex-1 truncate">{label}</span>
      {badgeCount > 0 && (
        <span
          className="flex items-center justify-center h-[18px] min-w-[18px] px-1.5 text-[11px] font-medium font-mono rounded-full ml-2"
          style={{ background: 'var(--warning-subtle)', color: 'var(--warning)' }}
        >
          {badgeCount}
        </span>
      )}
    </NavLink>
  );
};

const SectionLabel = ({ children }: { children: React.ReactNode }) => (
  <div className="px-2.5 mb-1.5 text-[11px] font-medium text-ink-3">{children}</div>
);

export default function Sidebar() {
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <div
      className="fixed inset-y-0 left-0 w-[232px] flex flex-col z-40"
      style={{ background: 'var(--bg-elevated)', borderRight: '1px solid var(--border-subtle)' }}
    >
      {/* Logo Row */}
      <div className="flex items-center h-[56px] px-4 shrink-0">
        <div className="mr-2">
          <AegisShield size={20} />
        </div>
        <span className="font-logo text-[13px] text-ink-1">
          AEGIS <span style={{ color: 'var(--accent)' }}>AML</span>
        </span>
      </div>

      {/* Navigation */}
      <div className="flex-1 overflow-y-auto px-2.5 py-3 space-y-6 scrollbar-hide">

        <div className="space-y-0.5">
          <SectionLabel>Workspace</SectionLabel>
          <NavItem to="/dashboard" label="Dashboard" icon={
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="3" width="7" height="9" rx="1"/><rect x="14" y="3" width="7" height="5" rx="1"/><rect x="14" y="12" width="7" height="9" rx="1"/><rect x="3" y="16" width="7" height="5" rx="1"/></svg>
          } />
          <NavItem to="/queue" label="Review Queue" icon={
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>
          } />
        </div>

        <div className="space-y-0.5">
          <SectionLabel>Settings</SectionLabel>
          <NavItem to="/settings/credentials" label="Credentials" icon={
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
          } />
          <NavItem to="/settings/webhook" label="Webhook" icon={
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M18 8c0 4.5-6 6-6 12M6 8c0 4.5 6 6 6 12M8 4h8M12 2v2"/></svg>
          } />
          <NavItem to="/settings/schema" label="Ingestion Schema" icon={
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/></svg>
          } />
          <NavItem to="/settings/llm" label="LLM Config" icon={
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>
          } />
          <NavItem to="/settings/billing" label="Billing" icon={
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="2" y="5" width="20" height="14" rx="2"/><line x1="2" y1="10" x2="22" y2="10"/></svg>
          } />
        </div>

        {user?.role === 'SUPER_ADMIN' && (
          <div className="space-y-0.5">
            <SectionLabel>Admin</SectionLabel>
            <NavItem to="/admin/verifications" label="Verifications" icon={
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/></svg>
            } />
            <NavItem to="/admin/customers" label="Customers" icon={
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/></svg>
            } />
          </div>
        )}
      </div>

      {/* User Profile */}
      <div
        className="h-[56px] shrink-0 px-3 py-2.5 flex items-center justify-between hover:bg-surface-2 transition-colors cursor-pointer group"
        style={{ borderTop: '1px solid var(--border-subtle)' }}
        onClick={handleLogout}
        title="Click to logout"
      >
        <div className="flex items-center space-x-2.5 overflow-hidden">
          <div
            className="w-7 h-7 rounded-full flex items-center justify-center shrink-0 font-medium text-[11px]"
            style={{ background: 'var(--accent-subtle)', color: 'var(--accent-text)' }}
          >
            {user?.email?.charAt(0).toUpperCase() || 'U'}
          </div>
          <div className="flex flex-col truncate">
            <span className="text-[13px] font-medium text-ink-1 truncate leading-tight">{user?.fullName || 'User'}</span>
            <span className="text-[11px] text-ink-3 truncate leading-tight">
              {user?.role === 'COMPLIANCE_OFFICER' ? 'Compliance Officer' : user?.role === 'TENANT_ADMIN' ? 'Tenant Admin' : user?.role === 'SUPER_ADMIN' ? 'Super Admin' : user?.role}
            </span>
          </div>
        </div>
        <svg className="w-4 h-4 text-ink-3 opacity-0 group-hover:opacity-100 transition-opacity" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>
      </div>
    </div>
  );
}
