import React, { useEffect } from 'react';
import { createPortal } from 'react-dom';

interface ModalProps {
  /** Both spellings accepted — pages use either */
  open?: boolean;
  isOpen?: boolean;
  onClose: () => void;
  title?: string;
  children: React.ReactNode;
  footer?: React.ReactNode;
  width?: number;
  fullScreen?: boolean;
  hideHeader?: boolean;
  /** When false, Esc / backdrop clicks do not dismiss (forced acknowledgement) */
  dismissible?: boolean;
}

export function Modal({
  open,
  isOpen,
  onClose,
  title,
  children,
  footer,
  width = 480,
  fullScreen = false,
  hideHeader = false,
  dismissible = true,
}: ModalProps) {
  const visible = open ?? isOpen ?? false;

  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && dismissible) onClose();
    };
    if (visible) {
      document.addEventListener('keydown', handleEscape);
      document.body.style.overflow = 'hidden';
    }
    return () => {
      document.removeEventListener('keydown', handleEscape);
      document.body.style.overflow = 'unset';
    };
  }, [visible, onClose, dismissible]);

  if (!visible) return null;

  const backdropClick = dismissible ? onClose : undefined;

  if (fullScreen) {
    return createPortal(
      <div className="fixed inset-0 z-50 flex items-center justify-center animate-fade-in">
        <div className="absolute inset-0 bg-black/80 backdrop-blur-md" onClick={backdropClick} />
        <div className="relative w-full h-full bg-[#F7F6F4] text-[#1a1a1a] flex flex-col animate-scale-in overflow-hidden">
          {/* Top banner for fullscreen (preview) */}
          <div className="h-[48px] bg-risk-high/10 border-b border-risk-high/30 flex items-center justify-center relative shrink-0">
            <svg className="w-3.5 h-3.5 text-risk-high mr-2" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
            <span className="text-[12px] font-mono text-risk-high uppercase">CONFIDENTIAL — CONTAINS REAL PII. NOT RETAINED BY AEGIS.</span>
            <button onClick={onClose} className="absolute right-2 top-2 w-9 h-9 flex items-center justify-center text-risk-high hover:bg-risk-high/10 rounded-md transition-colors">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
            </button>
          </div>
          <div className="flex-1 overflow-y-auto">
            {children}
          </div>
        </div>
      </div>,
      document.body
    );
  }

  return createPortal(
    <div className="fixed inset-0 z-50 flex items-center justify-center animate-fade-in px-4">
      {/* The whole command center falls out of focus behind the action */}
      <div
        className="absolute inset-0"
        style={{
          background: 'rgba(42,42,42,0.35)',
          backdropFilter: 'blur(10px) saturate(120%)',
          WebkitBackdropFilter: 'blur(10px) saturate(120%)',
        }}
        onClick={backdropClick}
      />
      <div
        className="relative w-full flex flex-col"
        style={{
          maxWidth: width,
          background: 'linear-gradient(180deg, var(--glass-modal-a), var(--glass-modal-b))',
          border: '1px solid rgba(201,162,39,0.3)',
          borderRadius: 'var(--r-xl)',
          boxShadow: 'var(--shadow-lg), 0 0 90px -20px rgba(6,78,59,0.25)',
          backdropFilter: 'blur(24px)',
          WebkitBackdropFilter: 'blur(24px)',
          overflow: 'hidden',
          animation: 'modalSnap 460ms cubic-bezier(0.34, 1.56, 0.64, 1) both',
        }}
      >
        {/* top hairline glow */}
        <div style={{ position: 'absolute', top: 0, left: '15%', right: '15%', height: 1, background: 'linear-gradient(90deg, transparent, var(--hairline), transparent)' }} />
        {!hideHeader && (
          <div className="flex items-center justify-between px-5 h-[52px]" style={{ borderBottom: '1px solid var(--border-subtle)' }}>
            <h2 className="text-[15px] font-semibold text-white">{title}</h2>
            <button onClick={onClose} className="w-8 h-8 flex items-center justify-center text-ink-3 hover:text-white hover:bg-white/[0.07] rounded-md transition-colors">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
            </button>
          </div>
        )}
        <div className="p-5 overflow-y-auto max-h-[70vh]">
          {children}
        </div>
        {footer && (
          <div className="px-5 py-4 flex items-center justify-end gap-2" style={{ borderTop: '1px solid var(--border-subtle)', background: 'rgba(23,23,23,0.02)' }}>
            {footer}
          </div>
        )}
      </div>
    </div>,
    document.body
  );
}
