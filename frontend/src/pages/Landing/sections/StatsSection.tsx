import { useEffect, useRef, useState } from 'react'

const DURATION_MS = 1400

const easeOutCubic = (t: number) => 1 - Math.pow(1 - t, 3)

/** Animate 0→1 progress once `start` flips true. */
function useCountProgress(start: boolean): number {
  const [progress, setProgress] = useState(0)
  useEffect(() => {
    if (!start) return
    let raf = 0
    const t0 = performance.now()
    const tick = (now: number) => {
      const t = Math.min(1, (now - t0) / DURATION_MS)
      setProgress(easeOutCubic(t))
      if (t < 1) raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [start])
  return progress
}

export default function StatsSection() {
  const sectionRef = useRef<HTMLElement>(null)
  const [started, setStarted] = useState(false)
  const p = useCountProgress(started)

  useEffect(() => {
    const el = sectionRef.current
    if (!el) return
    const obs = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setStarted(true)
          obs.disconnect()
        }
      },
      { threshold: 0.3 },
    )
    obs.observe(el)
    return () => obs.disconnect()
  }, [])

  // < 10 min counts DOWN from 60 to 10; others count up
  const minutes = Math.round(60 - (60 - 10) * p)
  const checks = Math.round(8 * p)
  const coverage = Math.round(100 * p)

  const stats: { value: string; label: string }[] = [
    { value: `< ${minutes} min`, label: 'Per SAR, end-to-end' },
    { value: `${checks}`, label: 'AML typology checks' },
    { value: 'PMLA 2002', label: 'Compliance standard' },
    { value: `${coverage}%`, label: 'Audit trail coverage' },
  ]

  return (
    <section ref={sectionRef} className="stats-section">
      <div className="stats-grid">
        {stats.map((s) => (
          <div key={s.label} className="stat-block">
            <div className="stat-number">{s.value}</div>
            <div className="stat-label">{s.label}</div>
          </div>
        ))}
      </div>
    </section>
  )
}
