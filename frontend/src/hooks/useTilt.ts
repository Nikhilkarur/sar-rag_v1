import { useCallback, useRef } from 'react'

/**
 * Physics-based hover tilt + mouse-tracked gold glare.
 * Returns spreadable handlers; pair with the `.tilt-card` class, whose CSS
 * reads the custom properties this hook writes:
 *   --rx/--ry  → perspective tilt   --mx/--my → glare position
 */
export function useTilt<T extends HTMLElement = HTMLDivElement>(maxDeg = 5) {
  const ref = useRef<T>(null)

  const onMouseMove = useCallback(
    (e: React.MouseEvent<T>) => {
      const el = ref.current ?? (e.currentTarget as T)
      const rect = el.getBoundingClientRect()
      const px = (e.clientX - rect.left) / rect.width // 0..1
      const py = (e.clientY - rect.top) / rect.height
      el.style.setProperty('--ry', `${(px - 0.5) * 2 * maxDeg}deg`)
      el.style.setProperty('--rx', `${-(py - 0.5) * 2 * maxDeg}deg`)
      el.style.setProperty('--mx', `${px * 100}%`)
      el.style.setProperty('--my', `${py * 100}%`)
      el.style.setProperty('--lift', '-4px')
    },
    [maxDeg],
  )

  const onMouseLeave = useCallback((e: React.MouseEvent<T>) => {
    const el = ref.current ?? (e.currentTarget as T)
    el.style.setProperty('--rx', '0deg')
    el.style.setProperty('--ry', '0deg')
    el.style.setProperty('--lift', '0px')
  }, [])

  return { ref, onMouseMove, onMouseLeave }
}
