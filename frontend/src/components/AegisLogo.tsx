interface AegisLogoProps {
  size?: number
  float?: boolean
}

export function AegisShield({ size = 24, float }: AegisLogoProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 48 48"
      fill="none"
      style={float ? { animation: 'subtleFloat 6s ease-in-out infinite' } : undefined}
    >
      <path
        d="M24 3 L42 11 V23 C42 33.5 34.4 41.6 24 45 C13.6 41.6 6 33.5 6 23 V11 Z"
        stroke="var(--accent)"
        strokeWidth="2.5"
        strokeLinejoin="round"
        fill="rgba(99,102,241,0.10)"
      />
      <path
        d="M19 30 L24 17 L29 30 M20.8 26 H27.2"
        stroke="var(--accent)"
        strokeWidth="2.4"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}

export function AegisWordmark({ shieldSize = 24 }: { shieldSize?: number }) {
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}>
      <AegisShield size={shieldSize} />
      <span style={{ fontSize: 16, fontWeight: 700, letterSpacing: '-0.01em', whiteSpace: 'nowrap' }}>
        <span style={{ color: 'var(--text-1)' }}>AEGIS</span>{' '}
        <span style={{ color: 'var(--accent)' }}>AML</span>
      </span>
    </span>
  )
}
