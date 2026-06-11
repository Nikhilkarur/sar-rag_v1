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
  if (pathname.startsWith('/admin/groq')) return 'Groq Usage';
  return 'Aegis AML';
};

export default function TopBar() {
  const location = useLocation();
  const title = getPageTitle(location.pathname);

  if (!title) return null; // Don't render topbar on full-screen pages like SAR Workspace

  return (
    <div className="h-[52px] bg-surface border-b border-border-dim px-6 flex items-center justify-between sticky top-0 z-30">
      <div className="flex items-center">
        <h1 className="text-[16px] font-semibold text-white tracking-tight">{title}</h1>
      </div>

      <div className="flex items-center space-x-4">
        {/* Command Palette Button */}
        <button className="flex items-center h-[28px] px-2.5 bg-transparent border border-border-base rounded text-ink-2 hover:bg-surface-2 hover:border-border-strong hover:text-white transition-all group">
          <svg className="w-3.5 h-3.5 mr-1.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
          </svg>
          <span className="text-[11px] font-medium mr-2">Search</span>
          <div className="flex items-center space-x-0.5">
            <kbd className="bg-surface-3 border border-border-dim rounded-sm px-1 font-mono text-[9px] text-ink-3 group-hover:text-ink-2">⌘</kbd>
            <kbd className="bg-surface-3 border border-border-dim rounded-sm px-1 font-mono text-[9px] text-ink-3 group-hover:text-ink-2">K</kbd>
          </div>
        </button>
      </div>
    </div>
  );
}
