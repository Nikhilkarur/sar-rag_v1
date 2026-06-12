import React from 'react';

export type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger' | 'danger-ghost' | 'success-ghost';
export type ButtonSize = 'sm' | 'md' | 'lg';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  icon?: React.ReactNode;
  fullWidth?: boolean;
  /** Both spellings accepted — pages use either */
  isLoading?: boolean;
  loading?: boolean;
}

const SIZES: Record<ButtonSize, string> = {
  sm: 'h-[28px] px-2.5 text-[12.5px] gap-1.5',
  md: 'h-[32px] px-3.5 text-[13px] gap-2',
  lg: 'h-[38px] px-4 text-[14px] gap-2',
};

export function Button({
  variant = 'primary',
  size = 'md',
  icon,
  fullWidth,
  isLoading,
  loading,
  className = '',
  children,
  disabled,
  ...props
}: ButtonProps) {
  const busy = isLoading || loading;

  const baseStyle =
    'relative inline-flex items-center justify-center rounded-md font-medium whitespace-nowrap ' +
    'transition-colors duration-100 ease-out ' +
    'disabled:opacity-50 disabled:cursor-not-allowed disabled:active:scale-100';

  const variants: Record<ButtonVariant, string> = {
    primary:
      'border border-transparent bg-[#18181A] !text-white ' +
      'shadow-[0_1px_2px_rgba(0,0,0,0.08)] hover:bg-[#2D2D2F]',
    secondary:
      'bg-white border border-border-base text-ink-1 shadow-[0_1px_2px_rgba(0,0,0,0.04)] ' +
      'hover:border-border-strong hover:bg-surface-2',
    ghost:
      'bg-transparent border border-transparent text-ink-2 ' +
      'hover:bg-surface-3 hover:text-ink-1',
    danger:
      'bg-white border border-risk-high/40 text-risk-high shadow-[0_1px_2px_rgba(0,0,0,0.04)] ' +
      'hover:bg-risk-high-dim hover:border-risk-high',
    'danger-ghost':
      'bg-transparent border border-transparent text-risk-high ' +
      'hover:bg-risk-high-dim',
    'success-ghost':
      'bg-transparent border border-transparent text-risk-low ' +
      'hover:bg-risk-low-dim',
  };

  return (
    <button
      className={`${baseStyle} ${SIZES[size]} ${variants[variant]} ${fullWidth ? 'w-full' : ''} ${className}`}
      disabled={disabled || busy}
      {...props}
    >
      {busy ? (
        <svg className="animate-spin h-3.5 w-3.5 text-current shrink-0" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
        </svg>
      ) : (
        icon && <span className="inline-flex items-center justify-center shrink-0">{icon}</span>
      )}
      {children}
    </button>
  );
}
