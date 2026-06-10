interface ToggleProps {
  checked: boolean
  onChange: (checked: boolean) => void
  disabled?: boolean
}

export function Toggle({ checked, onChange, disabled }: ToggleProps) {
  return (
    <button
      role="switch"
      aria-checked={checked}
      disabled={disabled}
      onClick={() => onChange(!checked)}
      style={{
        width: 44,
        height: 24,
        borderRadius: 'var(--r-full)',
        background: checked ? 'var(--accent)' : 'var(--bg-elevated)',
        border: '1px solid ' + (checked ? 'var(--accent)' : 'var(--border)'),
        position: 'relative',
        cursor: disabled ? 'not-allowed' : 'pointer',
        transition: 'background 200ms cubic-bezier(0.4,0,0.2,1), border-color 200ms',
        opacity: disabled ? 0.5 : 1,
        flexShrink: 0,
        padding: 0,
      }}
    >
      <span
        style={{
          position: 'absolute',
          top: 2,
          left: checked ? 22 : 3,
          width: 18,
          height: 18,
          borderRadius: '50%',
          background: '#fff',
          boxShadow: 'var(--shadow-sm)',
          transition: 'left 200ms cubic-bezier(0.4,0,0.2,1)',
        }}
      />
    </button>
  )
}
