import React from 'react'
import { cls } from '../../utils/format'

interface FieldProps {
  label?: string
  hint?: string
  error?: string
  children: React.ReactNode
}

export function Field({ label, hint, error, children }: FieldProps) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      {label && (
        <label className="label-upper" style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          {label}
          {hint && (
            <span className="tip" style={{ cursor: 'help' }}>
              <span
                style={{
                  width: 14,
                  height: 14,
                  borderRadius: '50%',
                  border: '1px solid var(--border-strong)',
                  color: 'var(--text-4)',
                  fontSize: 9,
                  display: 'inline-flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  textTransform: 'none',
                  letterSpacing: 0,
                }}
              >
                ?
              </span>
              <span className="tip-content">{hint}</span>
            </span>
          )}
        </label>
      )}
      {children}
      {error && (
        <span className="anim-fade-in-up" style={{ fontSize: 12, color: 'var(--danger)' }}>
          {error}
        </span>
      )}
    </div>
  )
}

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  error?: boolean
  leftIcon?: React.ReactNode
  rightSlot?: React.ReactNode
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(function Input(
  { error, leftIcon, rightSlot, style, ...rest },
  ref,
) {
  if (!leftIcon && !rightSlot) {
    return (
      <input ref={ref} className={cls('input', error && 'input-error')} style={style} {...rest} />
    )
  }
  return (
    <div style={{ position: 'relative', width: '100%' }}>
      {leftIcon && (
        <span
          style={{
            position: 'absolute',
            left: 10,
            top: '50%',
            transform: 'translateY(-50%)',
            color: 'var(--text-4)',
            display: 'flex',
            pointerEvents: 'none',
          }}
        >
          {leftIcon}
        </span>
      )}
      <input
        ref={ref}
        className={cls('input', error && 'input-error')}
        style={{
          ...(leftIcon ? { paddingLeft: 32 } : {}),
          ...(rightSlot ? { paddingRight: 36 } : {}),
          ...style,
        }}
        {...rest}
      />
      {rightSlot && (
        <span
          style={{
            position: 'absolute',
            right: 8,
            top: '50%',
            transform: 'translateY(-50%)',
            display: 'flex',
          }}
        >
          {rightSlot}
        </span>
      )}
    </div>
  )
})

interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  options: { value: string; label: string }[]
}

export function Select({ options, style, ...rest }: SelectProps) {
  return (
    <div style={{ position: 'relative', width: '100%' }}>
      <select className="input" style={{ ...style, paddingRight: 30 }} {...rest}>
        {options.map((o) => (
          <option key={o.value} value={o.value} style={{ background: 'var(--bg-elevated)' }}>
            {o.label}
          </option>
        ))}
      </select>
      <svg
        width="12"
        height="12"
        viewBox="0 0 24 24"
        fill="none"
        stroke="var(--text-3)"
        strokeWidth="2.5"
        style={{
          position: 'absolute',
          right: 12,
          top: '50%',
          transform: 'translateY(-50%)',
          pointerEvents: 'none',
        }}
      >
        <polyline points="6 9 12 15 18 9" />
      </svg>
    </div>
  )
}
