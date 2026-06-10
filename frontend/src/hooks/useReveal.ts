import { useEffect, useRef } from 'react'

/**
 * Scroll-reveal helper: when the observed element enters the viewport, every
 * descendant with the `.reveal` class gains `.visible`, staggered 80ms apart.
 * Fires once, then disconnects.
 */
export function useReveal<T extends HTMLElement = HTMLElement>(options?: IntersectionObserverInit) {
  const ref = useRef<T>(null)
  useEffect(() => {
    const el = ref.current
    if (!el) return
    const obs = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          el.querySelectorAll('.reveal').forEach((child, i) => {
            setTimeout(() => child.classList.add('visible'), i * 80)
          })
          obs.disconnect()
        }
      },
      { threshold: 0.15, ...options },
    )
    obs.observe(el)
    return () => obs.disconnect()
  }, [])
  return ref
}
