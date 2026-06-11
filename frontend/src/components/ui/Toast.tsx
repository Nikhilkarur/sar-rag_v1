import React, { createContext, useContext, useState, useCallback, useEffect } from 'react';
import { createPortal } from 'react-dom';

type ToastType = 'info' | 'success' | 'warning' | 'error';

interface Toast {
  id: string;
  type: ToastType;
  title: string;
  description?: string;
}

interface ToastContextType {
  addToast: (toast: Omit<Toast, 'id'>) => void;
  /** Positional convenience used across pages: toast('success', 'Title', 'desc?') */
  toast: (type: ToastType, title: string, description?: string) => void;
}

const ToastContext = createContext<ToastContextType | undefined>(undefined);

export function useToast() {
  const context = useContext(ToastContext);
  if (!context) throw new Error('useToast must be used within ToastProvider');
  return context;
}

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const addToast = useCallback((toast: Omit<Toast, 'id'>) => {
    const id = Math.random().toString(36).substring(2, 9);
    setToasts((prev) => [...prev, { ...toast, id }].slice(-3)); // Max 3 toasts
  }, []);

  const toast = useCallback(
    (type: ToastType, title: string, description?: string) => addToast({ type, title, description }),
    [addToast],
  );

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  return (
    <ToastContext.Provider value={{ addToast, toast }}>
      {children}
      {typeof document !== 'undefined' && createPortal(
        <div className="fixed bottom-6 right-6 z-50 flex flex-col gap-2">
          {toasts.map((toast) => (
            <ToastItem key={toast.id} toast={toast} onRemove={() => removeToast(toast.id)} />
          ))}
        </div>,
        document.body
      )}
    </ToastContext.Provider>
  );
}

function ToastItem({ toast, onRemove }: { toast: Toast; onRemove: () => void }) {
  useEffect(() => {
    const timer = setTimeout(() => {
      onRemove();
    }, 4000);
    return () => clearTimeout(timer);
  }, [onRemove]);

  const colors = {
    info: 'border-l-electric',
    success: 'border-l-risk-low',
    warning: 'border-l-risk-med',
    error: 'border-l-risk-high',
  };

  const icons = {
    info: <svg className="w-4 h-4 text-electric" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>,
    success: <svg className="w-4 h-4 text-risk-low" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>,
    warning: <svg className="w-4 h-4 text-risk-med" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>,
    error: <svg className="w-4 h-4 text-risk-high" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>,
  };

  return (
    <div
      className={`w-[320px] border border-border-base border-l-[3px] rounded-lg flex overflow-hidden animate-slide-in-r ${colors[toast.type]}`}
      style={{ background: 'var(--glass-modal-a)', boxShadow: 'var(--shadow-lg)', backdropFilter: 'blur(16px)', WebkitBackdropFilter: 'blur(16px)' }}
    >
      <div className="flex-1 flex p-3">
        <div className="shrink-0 mr-3 mt-0.5">{icons[toast.type]}</div>
        <div className="flex-1">
          <h4 className="text-[13px] font-medium text-white leading-tight mb-1">{toast.title}</h4>
          {toast.description && <p className="text-[12px] text-ink-2 leading-snug">{toast.description}</p>}
        </div>
        <button onClick={onRemove} className="shrink-0 w-6 h-6 flex items-center justify-center text-ink-3 hover:text-white rounded transition-colors -mt-1 -mr-1">
          <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
        </button>
      </div>
      <div className="absolute bottom-0 left-0 h-[2px] bg-border-dim w-full">
        <div className="h-full bg-current opacity-50" style={{ animation: 'linear 4s shrink-width forwards', transformOrigin: 'left' }} />
      </div>
      <style dangerouslySetInnerHTML={{__html: `@keyframes shrink-width { from { width: 100%; } to { width: 0%; } }`}} />
    </div>
  );
}
