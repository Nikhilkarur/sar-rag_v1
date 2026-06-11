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
  sm: 'h-[28px] px-2.5 text-[12px] gap-1.5',
  md: 'h-[34px] px-[14px] text-[13px] gap-2',
  lg: 'h-[40px] px-5 text-[14px] gap-2',
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
    'transition-all duration-150 ease-out overflow-hidden ' +
    'disabled:opacity-50 disabled:cursor-not-allowed disabled:active:scale-100';

  const variants: Record<ButtonVariant, string> = {
    primary:
      'font-semibold border border-transparent ' +
      'bg-[#064E3B] !text-[#FDFBF7] ' +
      'shadow-[0_1px_2px_rgba(6,78,59,0.3),0_4px_14px_-6px_rgba(6,78,59,0.5)] ' +
      'hover:bg-[#0A6B50] hover:shadow-[0_1px_2px_rgba(6,78,59,0.3),0_8px_22px_-6px_rgba(6,78,59,0.55)]',
    secondary:
      'bg-white border border-[rgba(23,23,23,0.16)] text-[#171717] shadow-sm ' +
      'hover:border-[rgba(6,78,59,0.4)] hover:text-[#064E3B]',
    ghost:
      'bg-transparent border border-transparent text-ink-2 ' +
      'hover:bg-[rgba(23,23,23,0.05)] hover:text-[#171717]',
    danger:
      'bg-transparent border border-risk-high/40 text-risk-high ' +
      'hover:bg-risk-high/10 hover:border-risk-high hover:shadow-glow-red',
    'danger-ghost':
      'bg-transparent border border-transparent text-risk-high ' +
      'hover:bg-risk-high/10 hover:border-risk-high/30',
    'success-ghost':
      'bg-transparent border border-transparent text-risk-low ' +
      'hover:bg-risk-low/10 hover:border-risk-low/30',
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
