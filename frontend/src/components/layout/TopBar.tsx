import { useLocation } from 'react-router-dom';

const getPageTitle = (pathname: string) => {
  if (pathname.includes('/queue/')) return null; // Queue detail handles its own header
  if (pathname.startsWith('/dashboard')) return 'Dashboard';
  if (pathname.startsWith('/queue')) return 'Review Queue';
  if (pathname.startsWith('/settings/credentials')) return 'API Credentials';
  if (pathname.startsWith('/settings/webhook')) return 'Webhook Configuration';
  if (pathname.startsWith('/settings/schema')) return 'Ingestion Schema';
  if (pathname.startsWith('/settings/llm')) return 'LLM Configuration';
  if (pathname.startsWith('/usage')) return 'Usage Analytics';
  if (pathname.startsWith('/admin/verifications')) return 'Tenant Verifications';
  if (pathname.startsWith('/admin/customers')) return 'Customers';
  if (pathname.startsWith('/admin/logs')) return 'API Logs';
  if (pathname.startsWith('/admin/llm')) return 'LLM Usage';
  return 'Aegis AML';
};

export default function TopBar() {
  const location = useLocation();
  const title = getPageTitle(location.pathname);

  if (!title) return null; // Don't render topbar on full-screen pages like SAR Workspace

  return (
    <div
      className="h-[48px] px-6 flex items-center justify-between sticky top-0 z-30"
      style={{ background: 'rgba(255,255,255,0.85)', backdropFilter: 'blur(8px)', borderBottom: '1px solid var(--border-subtle)' }}
    >
      <div className="flex items-center">
        <h1 className="text-[14px] font-semibold text-ink-1 tracking-tight">{title}</h1>
      </div>

      <div className="flex items-center space-x-4">
        {/* Command Palette Button */}
        <button className="flex items-center h-[28px] px-2.5 bg-surface border border-border-base rounded-md text-ink-3 hover:border-border-strong hover:text-ink-1 transition-all group">
          <svg className="w-3.5 h-3.5 mr-1.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
          </svg>
          <span className="text-[12px] font-medium mr-2">Search</span>
          <div className="flex items-center space-x-0.5">
            <kbd>⌘</kbd>
            <kbd>K</kbd>
          </div>
        </button>
      </div>
    </div>
  );
}
