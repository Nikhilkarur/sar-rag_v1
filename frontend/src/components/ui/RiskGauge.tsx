import { riskColor } from './Badge'

interface RiskGaugeProps {
  score: number
  size?: number
}

const CIRCUMFERENCE = 251 // 2π × r(40)

export function RiskGauge({ score, size = 96 }: RiskGaugeProps) {
  const color = riskColor(score)
  const target = CIRCUMFERENCE - (score / 100) * CIRCUMFERENCE

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 6 }}>
      <div style={{ position: 'relative', width: size, height: size }}>
        <svg width={size} height={size} viewBox="0 0 96 96">
          <circle cx="48" cy="48" r="40" stroke="var(--border)" strokeWidth="7" fill="none" />
          <circle
            cx="48"
            cy="48"
            r="40"
            stroke={color}
            strokeWidth="7"
            fill="none"
            strokeLinecap="round"
            strokeDasharray={CIRCUMFERENCE}
            strokeDashoffset={CIRCUMFERENCE}
            transform="rotate(-90 48 48)"
            style={
              {
                '--arc-target': `${target}`,
                animation: 'riskArc 800ms cubic-bezier(0.4,0,0.2,1) forwards',
              } as React.CSSProperties
            }
          />
        </svg>
        <div
          style={{
            position: 'absolute',
            inset: 0,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: 20,
            fontWeight: 700,
            color,
          }}
        >
          {score}
        </div>
      </div>
      <span
        style={{
          fontSize: 10,
          fontWeight: 500,
          textTransform: 'uppercase',
          letterSpacing: '0.06em',
          color: 'var(--text-3)',
        }}
      >
        Risk Score
      </span>
    </div>
  )
}
