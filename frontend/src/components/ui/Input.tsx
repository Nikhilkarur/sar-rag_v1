import React from 'react';

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  error?: boolean | string;
  leftIcon?: React.ReactNode;
  rightSlot?: React.ReactNode;
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className = '', error, leftIcon, rightSlot, style, ...props }, ref) => {
    const field = (
      <input
        ref={ref}
        className={`input ${className}`}
        style={{
          ...(leftIcon ? { paddingLeft: 32 } : null),
          ...(rightSlot ? { paddingRight: 36 } : null),
          ...(error
            ? { borderColor: 'var(--danger)', boxShadow: '0 0 0 3px rgba(192,57,43,0.12)' }
            : null),
          ...style,
        }}
        {...props}
      />
    );

    if (!leftIcon && !rightSlot) return field;
    return (
      <span style={{ position: 'relative', display: 'inline-flex', width: '100%' }}>
        {leftIcon && (
          <span
            style={{
              position: 'absolute',
              left: 10,
              top: '50%',
              transform: 'translateY(-50%)',
              display: 'inline-flex',
              color: 'var(--text-4)',
              pointerEvents: 'none',
              zIndex: 1,
            }}
          >
            {leftIcon}
          </span>
        )}
        {field}
        {rightSlot && (
          <span
            style={{
              position: 'absolute',
              right: 8,
              top: '50%',
              transform: 'translateY(-50%)',
              display: 'inline-flex',
              alignItems: 'center',
              color: 'var(--text-3)',
              zIndex: 1,
            }}
          >
            {rightSlot}
          </span>
        )}
      </span>
    );
  }
);
Input.displayName = 'Input';

/* ── Select — styled native select with custom chevron ─────────────── */

interface SelectOption {
  value: string;
  label: string;
}

interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  options: SelectOption[];
  error?: boolean | string;
}

export const Select = React.forwardRef<HTMLSelectElement, SelectProps>(
  ({ options, className = '', error, style, ...props }, ref) => (
    <span style={{ position: 'relative', display: 'inline-flex', width: '100%' }}>
      <select
        ref={ref}
        className={`input ${className}`}
        style={{
          appearance: 'none',
          WebkitAppearance: 'none',
          paddingRight: 30,
          cursor: 'pointer',
          ...(error
            ? { borderColor: 'var(--danger)', boxShadow: '0 0 0 3px rgba(192,57,43,0.12)' }
            : null),
          ...style,
        }}
        {...props}
      >
        {options.map((o) => (
          <option key={o.value} value={o.value} style={{ background: '#FFFFFF', color: '#151515' }}>
            {o.label}
          </option>
        ))}
      </select>
      <svg
        width="14" height="14" viewBox="0 0 24 24" fill="none"
        stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
        style={{
          position: 'absolute', right: 10, top: '50%', transform: 'translateY(-50%)',
          color: 'var(--text-3)', pointerEvents: 'none',
        }}
      >
        <polyline points="6 9 12 15 18 9" />
      </svg>
    </span>
  )
);
Select.displayName = 'Select';

/* ── Field — label + control + hint/error ──────────────────────────── */

interface FieldProps {
  label?: string;
  hint?: string;
  error?: string;
  children: React.ReactNode;
}

export function Field({ label, hint, error, children }: FieldProps) {
  return (
    <label style={{ display: 'block', marginBottom: 14 }}>
      {label && (
        <span
          className="label-upper"
          style={{ display: 'block', marginBottom: 6, color: error ? 'var(--danger)' : undefined }}
        >
          {label}
        </span>
      )}
      {children}
      {(error || hint) && (
        <span
          style={{
            display: 'block',
            marginTop: 5,
            fontSize: 11,
            lineHeight: 1.4,
            color: error ? 'var(--danger)' : 'var(--text-4)',
          }}
        >
          {error || hint}
        </span>
      )}
    </label>
  );
}
