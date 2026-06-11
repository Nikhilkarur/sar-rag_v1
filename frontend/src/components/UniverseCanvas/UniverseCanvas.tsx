import { useEffect, useRef, useState } from 'react'
import * as THREE from 'three'
import { UNIVERSE_CONFIG as C } from './universe.config'
import { nodePosition, buildRingGeometry, buildStarField, damp } from './universe.utils'

interface UniverseCanvasProps {
  /** true = landing page (full parallax, node labels, full brightness) */
  interactive?: boolean
  /** true = auth pages (canvas is blurred, low brightness, no pointer events) */
  blurred?: boolean
  className?: string
}

const LABEL_COLORS: Record<string, string> = {
  sar: 'var(--text-3)',
  rule: 'var(--gold-text)',
  alert: 'var(--danger)',
}

// Labeled nodes rendered as DOM spans; positions are driven imperatively from
// the animation loop. On mobile, spans whose orbits were dropped simply stay
// hidden (opacity 0) since no mesh drives them — NODES order guarantees the
// surviving labels map onto the first N spans.
const UNIVERSE_LABELED_NODES = C.NODES.filter((n) => n.label !== '')

export default function UniverseCanvas({
  interactive = true,
  blurred = false,
  className = '',
}: UniverseCanvasProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const wrapRef = useRef<HTMLDivElement>(null)
  const labelsRef = useRef<HTMLDivElement>(null)
  const [webglFailed, setWebglFailed] = useState(false)

  const showLabels = interactive && !blurred

  useEffect(() => {
    const canvas = canvasRef.current
    const wrap = wrapRef.current
    if (!canvas || !wrap || webglFailed) return

    // ── WebGL support check (fallback to CSS gradient) ────────────
    const testCanvas = document.createElement('canvas')
    const gl = testCanvas.getContext('webgl2') || testCanvas.getContext('webgl')
    if (!gl) {
      setWebglFailed(true)
      return
    }

    // ── Mobile degradation ─────────────────────────────────────────
    const isMobile = window.innerWidth < C.MOBILE_BREAKPOINT
    const parallaxEnabled = interactive && !isMobile
    const starCount = isMobile ? C.STAR_COUNT_MOBILE : C.STAR_COUNT
    const activeRings = isMobile ? C.RINGS.slice(0, 2) : C.RINGS
    const activeNodes = C.NODES.filter((n) => n.orbit < activeRings.length)
    // Remap constellation pairs onto the surviving node indices
    const indexMap = new Map<number, number>()
    C.NODES.forEach((n, i) => {
      if (n.orbit < activeRings.length) indexMap.set(i, indexMap.size)
    })
    const activePairs = C.CONSTELLATION_PAIRS.filter(
      ([a, b]) => indexMap.has(a) && indexMap.has(b),
    ).map(([a, b]) => [indexMap.get(a)!, indexMap.get(b)!] as [number, number])

    // ── Renderer ───────────────────────────────────────────────────
    let renderer: THREE.WebGLRenderer
    try {
      renderer = new THREE.WebGLRenderer({
        canvas,
        antialias: true,
        alpha: false,
        powerPreference: 'high-performance',
      })
    } catch {
      setWebglFailed(true)
      return
    }
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, C.PIXEL_RATIO_CAP))
    renderer.setSize(wrap.clientWidth, wrap.clientHeight, false)
    renderer.setClearColor(0xfdfbf7, 1) // alabaster marble — the astrolabe is engraved, not floating in space

    // ── Scene, Camera, Pivot ───────────────────────────────────────
    // All scene objects live in a pivot group so that mouse parallax (x/y
    // offsets) and base auto-rotation (accumulating y) compose cleanly.
    const scene = new THREE.Scene()
    const pivot = new THREE.Group()
    scene.add(pivot)

    const camera = new THREE.PerspectiveCamera(
      C.CAM_FOV,
      wrap.clientWidth / Math.max(wrap.clientHeight, 1),
      0.1,
      500,
    )
    camera.position.z = C.CAM_Z

    const disposables: { dispose: () => void }[] = []
    const track = <T extends { dispose: () => void }>(d: T): T => {
      disposables.push(d)
      return d
    }

    // ── Lighting ───────────────────────────────────────────────────
    const ambient = new THREE.AmbientLight(0xfdf8ec, 0.85)
    scene.add(ambient)

    // The beacon flame — emerald key light
    const pointLight = new THREE.PointLight(0x064e3b, 5, 12)
    pointLight.position.set(0, 0, 2)
    scene.add(pointLight)

    // Treasury rim — restrained gold kiss from the side
    const rimLight = new THREE.PointLight(0xd4af37, 1.8, 8)
    rimLight.position.set(-3, 2, -1)
    scene.add(rimLight)

    // Sea-breeze fill — faint azure from below
    const seaLight = new THREE.PointLight(0x0e7490, 1.4, 9)
    seaLight.position.set(2, -3, 1)
    scene.add(seaLight)

    // ── Central Orb ────────────────────────────────────────────────
    const orbGeo = track(new THREE.SphereGeometry(C.ORB_RADIUS, 96, 96))
    const orbMat = track(
      new THREE.MeshPhongMaterial({
        color: C.ORB_COLOR,
        emissive: C.ORB_EMISSIVE,
        emissiveIntensity: C.ORB_EMISSIVE_INTENSITY,
        shininess: 80,
        specular: 0xffffff,
      }),
    )
    const orb = new THREE.Mesh(orbGeo, orbMat)
    pivot.add(orb)

    // Fake bloom: tight, clean atmosphere — no giant blurry halo
    const glowLayers: [number, number, number][] = [
      [1.15, 0x064e3b, 0.09], // tight emerald atmosphere
      [1.42, 0x0e7490, 0.035], // faint azure haze
    ]
    glowLayers.slice(0, C.ORB_GLOW_LAYERS).forEach(([scale, color, opacity]) => {
      const geo = track(new THREE.SphereGeometry(C.ORB_RADIUS * scale, 32, 32))
      const mat = track(
        new THREE.MeshBasicMaterial({ color, transparent: true, opacity, side: THREE.BackSide }),
      )
      pivot.add(new THREE.Mesh(geo, mat))
    })

    // ── Orbit Rings ────────────────────────────────────────────────
    activeRings.forEach((ring) => {
      const ringGeo = track(buildRingGeometry(ring.radius, ring.tilt))
      const ringMat = track(
        new THREE.MeshBasicMaterial({
          color: ring.color,
          transparent: true,
          opacity: ring.opacity,
          side: THREE.DoubleSide,
        }),
      )
      pivot.add(new THREE.Mesh(ringGeo, ringMat))
    })

    // ── Orbiting Nodes ─────────────────────────────────────────────
    const nodeMeshes: THREE.Mesh[] = []
    activeNodes.forEach((node) => {
      const geo = track(new THREE.SphereGeometry(node.size, 16, 16))
      const mat = track(
        new THREE.MeshPhongMaterial({
          color: node.color,
          emissive: node.color,
          emissiveIntensity: node.type === 'packet' ? 0.9 : 0.5,
          shininess: 60,
        }),
      )
      const mesh = new THREE.Mesh(geo, mat)
      nodeMeshes.push(mesh)
      pivot.add(mesh)
    })

    // ── Constellation Lines ────────────────────────────────────────
    // Pre-allocated buffer; endpoints are rewritten every frame.
    const linePositions = new Float32Array(activePairs.length * 2 * 3)
    const lineGeo = track(new THREE.BufferGeometry())
    lineGeo.setAttribute('position', new THREE.BufferAttribute(linePositions, 3))
    const lineMat = track(
      new THREE.LineBasicMaterial({ color: 0x064e3b, transparent: true, opacity: 0.28 }),
    )
    const constellationLines = new THREE.LineSegments(lineGeo, lineMat)
    pivot.add(constellationLines)

    // ── Star Field ─────────────────────────────────────────────────
    const starGeo = track(buildStarField(starCount))
    const starMat = track(
      new THREE.PointsMaterial({
        color: 0xc9a227, // sparse gold dust — kept faint so the air stays clean
        size: 0.022,
        transparent: true,
        opacity: 0.35,
        sizeAttenuation: true,
      }),
    )
    scene.add(new THREE.Points(starGeo, starMat))

    // ── Mouse Parallax ─────────────────────────────────────────────
    let targetRotX = 0
    let targetRotY = 0
    let currentRotX = 0
    let currentRotY = 0

    const onMouseMove = (e: MouseEvent) => {
      const nx = (e.clientX / window.innerWidth - 0.5) * 2 // -1 to 1
      const ny = (e.clientY / window.innerHeight - 0.5) * 2
      targetRotY = nx * C.MOUSE_PARALLAX
      targetRotX = -ny * C.MOUSE_PARALLAX * 0.6
    }
    if (parallaxEnabled) window.addEventListener('mousemove', onMouseMove)

    // ── Resize Handling ────────────────────────────────────────────
    const applySize = () => {
      const w = wrap.clientWidth
      const h = Math.max(wrap.clientHeight, 1)
      camera.aspect = w / h
      camera.updateProjectionMatrix()
      renderer.setSize(w, h, false)
    }
    window.addEventListener('resize', applySize)
    const resizeObserver = new ResizeObserver(applySize)
    resizeObserver.observe(wrap)

    // ── Label projection setup ─────────────────────────────────────
    const labeledNodes = activeNodes
      .map((node, meshIndex) => ({ node, meshIndex }))
      .filter(({ node }) => node.label !== '')
    const labelEls = labelsRef.current
      ? (Array.from(labelsRef.current.children) as HTMLElement[])
      : []
    const projVec = new THREE.Vector3()
    const midVec = new THREE.Vector3()

    // ── Animation Loop ─────────────────────────────────────────────
    let animId: number
    let t = 0
    let autoRotY = 0
    let lastTime = performance.now()

    const animate = (now: number) => {
      animId = requestAnimationFrame(animate)
      const dt = Math.min((now - lastTime) / 1000, 0.05) // capped at 50ms
      lastTime = now
      t += dt

      // Base auto-rotation (per-frame constant, accumulated separately so the
      // mouse parallax can be applied as a clean offset on top)
      autoRotY += C.SCENE_ROTATE_Y

      if (parallaxEnabled) {
        currentRotX = damp(currentRotX, targetRotX, C.PARALLAX_DAMP, dt)
        currentRotY = damp(currentRotY, targetRotY, C.PARALLAX_DAMP, dt)
      }
      pivot.rotation.y = autoRotY + currentRotY
      pivot.rotation.x = currentRotX

      // Pulse orb emissive intensity — a quiet heartbeat, not a flare
      orbMat.emissiveIntensity = C.ORB_EMISSIVE_INTENSITY + Math.sin(t * 1.4) * 0.07

      // Update node positions along their tilted orbits
      activeNodes.forEach((nodeConf, i) => {
        const speedMult = nodeConf.type === 'packet' ? C.PACKET_SPEED : 1
        nodePosition(nodeConf.orbit, nodeConf.angle, t, speedMult, nodeMeshes[i].position)
      })

      // Update constellation line endpoints
      const posAttr = lineGeo.attributes.position as THREE.BufferAttribute
      activePairs.forEach(([a, b], i) => {
        const pa = nodeMeshes[a].position
        const pb = nodeMeshes[b].position
        posAttr.setXYZ(i * 2, pa.x, pa.y, pa.z)
        posAttr.setXYZ(i * 2 + 1, pb.x, pb.y, pb.z)
      })
      posAttr.needsUpdate = true

      // Project node labels to 2D screen space
      if (labelEls.length > 0) {
        const w = wrap.clientWidth
        const h = wrap.clientHeight
        // NDC depth of the orb's plane — labels nearer than this are "close".
        // (A fixed threshold like 0.5 never fires: with near=0.1/far=500 all
        // nodes project to z ≈ 0.95–0.98, so we compare against the centre.)
        const zMid = midVec.set(0, 0, 0).project(camera).z
        labeledNodes.forEach(({ meshIndex }, k) => {
          const el = labelEls[k]
          if (!el) return
          nodeMeshes[meshIndex].getWorldPosition(projVec)
          projVec.project(camera)
          if (projVec.z > 1) {
            // behind the camera
            el.style.opacity = '0'
            return
          }
          const x = ((projVec.x + 1) / 2) * w
          const y = ((-projVec.y + 1) / 2) * h
          el.style.transform = `translate(${x}px, ${y}px) translate(-50%, -120%)`
          el.style.opacity = projVec.z < zMid ? '0.85' : '0.3'
        })
      }

      renderer.render(scene, camera)
    }
    animate(performance.now())

    // ── Cleanup ────────────────────────────────────────────────────
    return () => {
      cancelAnimationFrame(animId)
      if (parallaxEnabled) window.removeEventListener('mousemove', onMouseMove)
      window.removeEventListener('resize', applySize)
      resizeObserver.disconnect()
      disposables.forEach((d) => d.dispose())
      renderer.dispose()
    }
  }, [interactive, webglFailed])

  // WebGL fallback: static deep indigo radial gradient — never a blank screen
  if (webglFailed) {
    return (
      <div
        className={`universe-canvas-fallback ${className}`}
        aria-hidden="true"
        style={{
          width: '100%',
          height: '100%',
          background:
            'radial-gradient(ellipse 60% 50% at 50% 45%, rgba(6,78,59,0.14) 0%, rgba(201,162,39,0.07) 40%, #FDFBF7 100%)',
          filter: blurred ? 'brightness(0.55)' : 'none',
        }}
      />
    )
  }

  return (
    <div
      ref={wrapRef}
      className={`universe-wrap ${className}`}
      style={{ position: 'relative', width: '100%', height: '100%', overflow: 'hidden' }}
    >
      <canvas
        ref={canvasRef}
        className="universe-canvas"
        style={{
          display: 'block',
          width: '100%',
          height: '100%',
          filter: blurred ? 'blur(14px) brightness(0.55) saturate(0.7)' : 'none',
          pointerEvents: blurred ? 'none' : 'auto',
          transition: 'filter 600ms ease',
        }}
      />
      {showLabels && (
        <div ref={labelsRef} className="universe-labels" aria-hidden="true">
          {UNIVERSE_LABELED_NODES.map((node, i) => (
            <span
              key={i}
              className="node-label"
              style={{ color: LABEL_COLORS[node.type] ?? 'var(--text-3)', opacity: 0 }}
            >
              {node.label}
            </span>
          ))}
        </div>
      )}
    </div>
  )
}
