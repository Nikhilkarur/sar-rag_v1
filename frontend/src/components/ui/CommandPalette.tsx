import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

export function CommandPalette() {
  const [isOpen, setIsOpen] = useState(false);
  const [search, setSearch] = useState('');
  const navigate = useNavigate();

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setIsOpen(true);
      }
      if (e.key === 'Escape') setIsOpen(false);
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-[15vh] animate-fade-in px-4">
      <div className="absolute inset-0 bg-black/70 backdrop-blur-sm" onClick={() => setIsOpen(false)} />
      <div className="relative w-full max-w-[540px] bg-surface border border-border-base rounded-[10px] shadow-modal animate-scale-in overflow-hidden">
        
        <div className="flex items-center h-[44px] border-b border-border-dim px-3">
          <svg className="w-3.5 h-3.5 text-ink-3 mr-2" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
          <input 
            autoFocus
            className="flex-1 bg-transparent text-[14px] text-white placeholder-ink-4 outline-none"
            placeholder="Search alerts, rules, or settings..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>

        <div className="p-2 max-h-[300px] overflow-y-auto">
          <div className="px-2 py-1.5 text-[10px] font-mono text-ink-3 uppercase tracking-widest">Pages</div>
          
          <button onClick={() => { navigate('/queue'); setIsOpen(false); }} className="w-full flex items-center h-[36px] px-2 rounded-md hover:bg-surface-2 text-[13px] text-ink-2 hover:text-white group relative">
            <div className="absolute left-0 top-1.5 bottom-1.5 w-[2px] bg-electric opacity-0 group-hover:opacity-100 rounded-r-sm" />
            <svg className="w-4 h-4 mr-2" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>
            Review Queue
          </button>
          
          <button onClick={() => { navigate('/settings/credentials'); setIsOpen(false); }} className="w-full flex items-center h-[36px] px-2 rounded-md hover:bg-surface-2 text-[13px] text-ink-2 hover:text-white group relative">
            <div className="absolute left-0 top-1.5 bottom-1.5 w-[2px] bg-electric opacity-0 group-hover:opacity-100 rounded-r-sm" />
            <svg className="w-4 h-4 mr-2" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
            API Credentials
          </button>
        </div>
      </div>
    </div>
  );
}
