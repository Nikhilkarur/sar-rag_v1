import { useEffect, useRef } from 'react'

/**
 * DOT MESH — mathematical n-dimensional wave grid.
 * Each dot drifts via overlapping sine / cosine oscillations so the
 * grid breathes and flows. Shared by the landing page and auth shell.
 * Pauses offscreen; renders one static frame under reduced motion.
 */
export default function DotMesh({ dark = false }: { dark?: boolean }) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    const dpr = Math.min(window.devicePixelRatio || 1, 2)
    let w = 0, h = 0, raf = 0, running = false

    const resize = () => {
      const rect = canvas.getBoundingClientRect()
      w = rect.width; h = rect.height
      canvas.width = w * dpr; canvas.height = h * dpr
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
    }

    const S = 26          // grid spacing px
    const A = 5.2         // max drift amplitude px
    const BASE = dark ? 0.13 : 0.09
    const RGB = dark ? '255,255,255' : '10,10,10'

    const draw = (t: number) => {
      ctx.clearRect(0, 0, w, h)
      const cols = Math.ceil(w / S) + 2
      const rows = Math.ceil(h / S) + 2
      for (let ix = 0; ix < cols; ix++) {
        for (let iy = 0; iy < rows; iy++) {
          const p1 = ix * 0.38 + iy * 0.29
          const p2 = ix * 0.29 - iy * 0.38
          const p3 = (ix - iy) * 0.21
          const dx = A * Math.sin(t * 0.00042 + p1) + A * 0.3 * Math.sin(t * 0.00071 + p3)
          const dy = A * Math.cos(t * 0.00031 + p2) + A * 0.3 * Math.cos(t * 0.00058 + p3)
          const a = Math.max(0.03, BASE + 0.045 * Math.sin(t * 0.0009 + ix * 0.45 + iy * 0.45))
          ctx.beginPath()
          ctx.arc(ix * S + dx, iy * S + dy, 1.45, 0, Math.PI * 2)
          ctx.fillStyle = `rgba(${RGB},${a})`
          ctx.fill()
        }
      }
    }

    resize()
    if (reduced) {
      draw(0)
      const onResize = () => { resize(); draw(0) }
      window.addEventListener('resize', onResize)
      return () => window.removeEventListener('resize', onResize)
    }

    const tick = (t: number) => { draw(t); if (running) raf = requestAnimationFrame(tick) }
    const obs = new IntersectionObserver(([e]) => {
      if (e.isIntersecting) { if (!running) { running = true; raf = requestAnimationFrame(tick) } }
      else { running = false; cancelAnimationFrame(raf) }
    }, { threshold: 0 })
    obs.observe(canvas)
    window.addEventListener('resize', resize)
    return () => { obs.disconnect(); running = false; cancelAnimationFrame(raf); window.removeEventListener('resize', resize) }
  }, [dark])

  return <canvas ref={canvasRef} className="dot-mesh" aria-hidden="true" />
}
