import React from 'react'

interface SkeletonProps {
  width?: string | number
  height?: string | number
  style?: React.CSSProperties
}

export function Skeleton({ width = '100%', height = 16, style }: SkeletonProps) {
  return <div className="skeleton" style={{ width, height, ...style }} />
}

export function SkeletonTextLine({ width = '70%' }: { width?: string | number }) {
  return <Skeleton width={width} height={14} style={{ marginBottom: 8 }} />
}

export function SkeletonStatCard() {
  return (
    <div className="stat-card" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
        <Skeleton width={32} height={32} style={{ borderRadius: '50%' }} />
        <Skeleton width={70} height={18} />
      </div>
      <Skeleton width={90} height={28} />
      <Skeleton width={110} height={11} />
    </div>
  )
}

export function SkeletonCard({ height = 240 }: { height?: number }) {
  return (
    <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <Skeleton width={160} height={18} />
      <Skeleton width="100%" height={height - 80} />
    </div>
  )
}

export function SkeletonTableRows({ rows = 5, cols = 6 }: { rows?: number; cols?: number }) {
  return (
    <>
      {Array.from({ length: rows }, (_, r) => (
        <tr key={r}>
          {Array.from({ length: cols }, (_, c) => (
            <td key={c}>
              <Skeleton width={c === 0 ? 110 : 60 + ((r + c) % 3) * 22} height={13} />
            </td>
          ))}
        </tr>
      ))}
    </>
  )
}
