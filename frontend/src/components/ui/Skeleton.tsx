import React from 'react';

interface SkeletonProps {
  className?: string;
  width?: string | number;
  height?: string | number;
  style?: React.CSSProperties;
}

const shimmerStyle: React.CSSProperties = {
  background: 'linear-gradient(90deg, rgba(60,42,24,0.06) 25%, rgba(60,42,24,0.11) 50%, rgba(60,42,24,0.06) 75%)',
  backgroundSize: '200% 100%',
  animation: 'shimmer 1.6s ease-in-out infinite',
};

export function Skeleton({ className = '', width, height, style }: SkeletonProps) {
  return (
    <div
      className={`rounded-md ${className}`}
      style={{
        ...shimmerStyle,
        width: width ?? '100%',
        height: height ?? 12,
        ...style,
      }}
    />
  );
}

/** Placeholder matching a dashboard .stat-card while KPIs load */
export function SkeletonStatCard() {
  return (
    <div className="stat-card" style={{ pointerEvents: 'none' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
        <Skeleton width={32} height={32} style={{ borderRadius: '50%' }} />
        <Skeleton width={72} height={18} style={{ borderRadius: 999 }} />
      </div>
      <Skeleton width="50%" height={28} style={{ marginTop: 14 }} />
      <Skeleton width="70%" height={10} style={{ marginTop: 10 }} />
    </div>
  );
}

/** Generic large card placeholder (charts etc.) */
export function SkeletonCard({ height = 200, width, style }: { height?: number; width?: number; style?: React.CSSProperties }) {
  return (
    <div
      className="card"
      style={{ height, width: width ?? '100%', pointerEvents: 'none', padding: 20, ...style }}
    >
      <Skeleton width="35%" height={14} />
      <Skeleton width="100%" height={Math.max(40, height - 86)} style={{ marginTop: 16 }} />
    </div>
  );
}

/** Rows of cells for use inside a <tbody> while a table loads */
export function SkeletonTableRows({ rows = 5, cols = 5 }: { rows?: number; cols?: number }) {
  return (
    <>
      {Array.from({ length: rows }).map((_, r) => (
        <tr key={r}>
          {Array.from({ length: cols }).map((_, c) => (
            <td key={c} style={{ padding: 12, paddingLeft: c === 0 ? 24 : 12 }}>
              <Skeleton
                width={`${55 + ((r * 7 + c * 13) % 40)}%`}
                height={12}
                style={{ animationDelay: `${(r * cols + c) * 60}ms` }}
              />
            </td>
          ))}
        </tr>
      ))}
    </>
  );
}

// Shimmer keyframes (kept here so the component is self-contained)
if (typeof document !== 'undefined' && !document.getElementById('aegis-shimmer-kf')) {
  const style = document.createElement('style');
  style.id = 'aegis-shimmer-kf';
  style.innerHTML = `
    @keyframes shimmer {
      0%   { background-position: -200% 0; }
      100% { background-position:  200% 0; }
    }
  `;
  document.head.appendChild(style);
}
