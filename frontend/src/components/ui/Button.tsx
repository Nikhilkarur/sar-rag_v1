import React from 'react'
import { cls } from '../../utils/format'

type Variant = 'primary' | 'secondary' | 'ghost' | 'danger' | 'danger-ghost' | 'success' | 'success-ghost'
type Size = 'sm' | 'md' | 'lg'

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant
  size?: Size
  loading?: boolean
  icon?: React.ReactNode
  fullWidth?: boolean
}

const base: React.CSSProperties = {
  display: 'inline-flex',
  alignItems: 'center',
  justifyContent: 'center',
  gap: 8,
  borderRadius: 'var(--r-md)',
  fontWeight: 500,
  cursor: 'pointer',
  border: '1px solid transparent',
  transition: 'background var(--t-fast), transform var(--t-fast), border-color var(--t-fast), color var(--t-fast)',
  whiteSpace: 'nowrap',
  userSelect: 'none',
}

const sizes: Record<Size, React.CSSProperties> = {
  sm: { height: 28, padding: '0 10px', fontSize: 13 },
  md: { height: 36, padding: '0 16px', fontSize: 14 },
  lg: { height: 42, padding: '0 20px', fontSize: 15 },
}

const variants: Record<Variant, React.CSSProperties> = {
  primary: { background: 'var(--accent)', color: '#fff' },
  secondary: {
    background: 'var(--bg-elevated)',
    borderColor: 'var(--border)',
    color: 'var(--text-1)',
  },
  ghost: { background: 'transparent', color: 'var(--text-2)' },
  danger: {
    background: 'var(--danger-subtle)',
    borderColor: 'rgba(239,68,68,0.3)',
    color: 'var(--danger)',
  },
  'danger-ghost': { background: 'transparent', color: 'var(--danger)' },
  success: {
    background: 'var(--success-subtle)',
    borderColor: 'rgba(34,197,94,0.3)',
    color: 'var(--success)',
  },
  'success-ghost': { background: 'transparent', color: 'var(--success)' },
}

export function Button({
  variant = 'primary',
  size = 'md',
  loading = false,
  icon,
  fullWidth,
  children,
  style,
  disabled,
  onMouseEnter,
  onMouseLeave,
  ...rest
}: ButtonProps) {
  const [hover, setHover] = React.useState(false)
  const [active, setActive] = React.useState(false)

  const hoverStyles: Record<Variant, React.CSSProperties> = {
    primary: { background: 'var(--accent-hover)' },
    secondary: { background: 'var(--bg-overlay)', borderColor: 'var(--border-strong)' },
    ghost: { background: 'var(--bg-elevated)', color: 'var(--text-1)' },
    danger: { background: 'rgba(239,68,68,0.18)', borderColor: 'var(--danger)' },
    'danger-ghost': { background: 'var(--danger-subtle)' },
    success: { background: 'rgba(34,197,94,0.18)', borderColor: 'var(--success)' },
    'success-ghost': { background: 'var(--success-subtle)' },
  }

  return (
    <button
      {...rest}
      disabled={disabled || loading}
      onMouseEnter={(e) => {
        setHover(true)
        onMouseEnter?.(e)
      }}
      onMouseLeave={(e) => {
        setHover(false)
        setActive(false)
        onMouseLeave?.(e)
      }}
      onMouseDown={() => setActive(true)}
      onMouseUp={() => setActive(false)}
      style={{
        ...base,
        ...sizes[size],
        ...variants[variant],
        ...(hover && !disabled && !loading ? hoverStyles[variant] : {}),
        ...(active && !disabled && !loading ? { transform: 'scale(0.98)' } : {}),
        ...(disabled || loading ? { opacity: 0.6, cursor: 'not-allowed' } : {}),
        ...(fullWidth ? { width: '100%' } : {}),
        ...style,
      }}
    >
      {loading ? (
        <span className={cls('spinner', variant !== 'primary' && 'spinner-accent')} />
      ) : (
        icon
      )}
      {children}
    </button>
  )
}
