# ══════════════════════════════════════════════════════════════
# AEGIS AML — LANDING PAGE & AUTH BACKGROUND SPEC
# ══════════════════════════════════════════════════════════════
#
# PURPOSE:
# This file governs THREE things that share one visual identity:
#   1. The public landing page at `/`   — the HYPE
#   2. The auth page background         — the GATE
#   3. The shared UniverseCanvas engine — the ENGINE
#
# EMOTIONAL JOURNEY:
#   / (Landing)  →  "What IS this?"  →  they're hooked
#   /login       →  "I need in."     →  they feel the weight of the product
#   /dashboard   →  "This is real."  →  built by MasterPrompt.md
#
# FABLE 5 INSTRUCTIONS:
# 1. Read MasterPrompt.md first — design tokens, CSS vars, spacing, typography
#    are all inherited. Do NOT redefine what already exists there.
# 2. This file adds NEW components and NEW routes on top of that foundation.
# 3. Push the absolute limit. This is a demo for investors and enterprise buyers.
#    The landing page is the first impression. Make it unforgettable.
# 4. When this spec is fully implemented, output:
#    "✅ LANDING + AUTH BG COMPLETE. Universe canvas live, all sections built."
#    Then STOP. Do not touch MasterPrompt components, backend, or DB.
# ══════════════════════════════════════════════════════════════

---

## PACKAGE INSTALLATION

```bash
npm install three @types/three
```

Three.js is the only new dependency. Everything else uses what MasterPrompt.md already installed.

---

## THE UNIVERSE — PHILOSOPHY

The Aegis engine is not software. It is intelligence.

The central indigo orb is the LLM engine — alive, glowing, processing.
Around it orbits the compliance universe: transaction nodes, SAR reports, AML rules.
Lines connect them like a constellation map — a graph of money, suspicion, and law.

This is not decoration. It is the product made visible.

The effect the user should feel:
- On landing: **"This company is serious. This is not a spreadsheet tool."**
- On login/signup: **"I am approaching something powerful."** The universe continues behind frosted glass.
- The glass says: "You are locked out — but you can see what's waiting."

---

## FILE STRUCTURE TO CREATE

```
src/
├── components/
│   └── UniverseCanvas/
│       ├── UniverseCanvas.tsx          ← The Three.js engine
│       ├── universe.utils.ts           ← Orbit math, node data, helpers
│       └── universe.config.ts          ← All tunable constants
├── pages/
│   └── Landing/
│       ├── Landing.tsx                 ← Main landing page
│       ├── sections/
│       │   ├── HeroSection.tsx
│       │   ├── PipelineSection.tsx
│       │   ├── FeaturesSection.tsx
│       │   ├── StatsSection.tsx
│       │   └── CtaSection.tsx
│       └── Landing.css                 ← Landing-specific keyframes/styles
└── layouts/
    └── AuthLayout.tsx                  ← Wraps /login, /signup, /status
                                           Injects blurred UniverseCanvas as bg
```

---

## PART 1 — `universe.config.ts`

```typescript
export const UNIVERSE_CONFIG = {
  // Orb
  ORB_RADIUS:           0.78,
  ORB_COLOR:            0x6366f1,
  ORB_EMISSIVE:         0x4338ca,
  ORB_EMISSIVE_INTENSITY: 1.0,
  ORB_GLOW_LAYERS:      3,       // concentric transparent spheres for bloom fake

  // Orbit rings (purely visual, no physics)
  RINGS: [
    { radius: 1.6,  tilt: 0,    speed: 0.0006,  color: 0x6366f1, opacity: 0.12 },
    { radius: 2.4,  tilt: 55,   speed: -0.0004, color: 0x818cf8, opacity: 0.08 },
    { radius: 3.2,  tilt: 110,  speed: 0.0003,  color: 0x38bdf8, opacity: 0.06 },
  ],

  // Orbiting nodes (the "compliance graph")
  NODES: [
    // SAR documents
    { orbit: 0, angle: 0,    size: 0.10, color: 0xf4f4f5, label: 'SAR-2026-001',    type: 'sar' },
    { orbit: 0, angle: 120,  size: 0.09, color: 0xf4f4f5, label: 'SAR-2026-002',    type: 'sar' },
    { orbit: 0, angle: 240,  size: 0.08, color: 0xf4f4f5, label: 'SAR-2026-003',    type: 'sar' },
    // AML rules
    { orbit: 1, angle: 30,   size: 0.12, color: 0xf59e0b, label: 'STRUCTURING',     type: 'rule' },
    { orbit: 1, angle: 150,  size: 0.11, color: 0xf59e0b, label: 'RAPID_MOVEMENT',  type: 'rule' },
    { orbit: 1, angle: 270,  size: 0.10, color: 0xf59e0b, label: 'VELOCITY',        type: 'rule' },
    // Transaction alerts
    { orbit: 2, angle: 60,   size: 0.13, color: 0xef4444, label: '₹9,90,000',       type: 'alert' },
    { orbit: 2, angle: 180,  size: 0.11, color: 0xef4444, label: '₹24,50,000',      type: 'alert' },
    { orbit: 2, angle: 300,  size: 0.09, color: 0xef4444, label: 'HIGH RISK',       type: 'alert' },
    // Data packets (tiny, fast, no label)
    { orbit: 0, angle: 60,   size: 0.04, color: 0x818cf8, label: '',               type: 'packet' },
    { orbit: 1, angle: 200,  size: 0.04, color: 0x818cf8, label: '',               type: 'packet' },
    { orbit: 2, angle: 130,  size: 0.04, color: 0x6366f1, label: '',               type: 'packet' },
  ],

  // Constellation lines (pairs of node indices to connect)
  CONSTELLATION_PAIRS: [
    [0, 3], [1, 4], [2, 5],   // SARs connect to rules
    [3, 6], [4, 7], [5, 8],   // Rules connect to alerts
    [0, 1], [3, 4],           // Same-orbit connections
  ],

  // Star field
  STAR_COUNT:     1800,
  STAR_SIZE_MIN:  0.012,
  STAR_SIZE_MAX:  0.032,
  STAR_DEPTH:     [-80, -20],  // z range

  // Camera
  CAM_Z:          5.0,
  CAM_FOV:        58,
  MOUSE_PARALLAX: 0.18,        // max rotation in radians from mouse

  // Animation
  SCENE_ROTATE_Y: 0.00015,    // base auto-rotation per frame
  PACKET_SPEED:   1.8,         // multiplier for data packet nodes

  // Performance
  PIXEL_RATIO_CAP: 1.5,        // cap devicePixelRatio for perf
}
```

---

## PART 2 — `universe.utils.ts`

```typescript
import * as THREE from 'three'
import { UNIVERSE_CONFIG as C } from './universe.config'

/** Compute a node's world position given its orbit ring, angle, and the ring tilt. */
export function nodePosition(
  orbitIndex: number,
  angleDeg: number,
  time: number
): THREE.Vector3 {
  const ring = C.RINGS[orbitIndex]
  const speed = ring.speed * (orbitIndex === 0 ? C.PACKET_SPEED : 1)
  const a = THREE.MathUtils.degToRad(angleDeg) + time * ring.speed
  const tilt = THREE.MathUtils.degToRad(ring.tilt)

  // Parametric orbit on tilted plane
  const x = ring.radius * Math.cos(a)
  const y = ring.radius * Math.sin(a) * Math.sin(tilt)
  const z = ring.radius * Math.sin(a) * Math.cos(tilt)
  return new THREE.Vector3(x, y, z)
}

/** Build a BufferGeometry for a flat orbit ring (torus cross-section = 0.004) */
export function buildRingGeometry(radius: number, tiltDeg: number): THREE.BufferGeometry {
  const geo = new THREE.TorusGeometry(radius, 0.004, 8, 128)
  const euler = new THREE.Euler(THREE.MathUtils.degToRad(tiltDeg), 0, 0)
  geo.applyEuler(euler)
  return geo
}

/** Generate random star field positions */
export function buildStarField(): THREE.BufferGeometry {
  const positions = new Float32Array(C.STAR_COUNT * 3)
  for (let i = 0; i < C.STAR_COUNT; i++) {
    positions[i * 3]     = (Math.random() - 0.5) * 160
    positions[i * 3 + 1] = (Math.random() - 0.5) * 160
    positions[i * 3 + 2] = C.STAR_DEPTH[0] + Math.random() * (C.STAR_DEPTH[1] - C.STAR_DEPTH[0])
  }
  const geo = new THREE.BufferGeometry()
  geo.setAttribute('position', new THREE.BufferAttribute(positions, 3))
  return geo
}

/** Lerp a value with damping (smooth follow) */
export function damp(current: number, target: number, lambda: number, dt: number): number {
  return THREE.MathUtils.lerp(current, target, 1 - Math.exp(-lambda * dt))
}
```

---

## PART 3 — `UniverseCanvas.tsx`

```typescript
import { useEffect, useRef } from 'react'
import * as THREE from 'three'
import { UNIVERSE_CONFIG as C } from './universe.config'
import { nodePosition, buildRingGeometry, buildStarField, damp } from './universe.utils'

interface UniverseCanvasProps {
  /** true = landing page (full parallax, hover labels, full brightness)  */
  interactive?: boolean
  /** true = auth pages (canvas is blurred, low brightness, no pointer events) */
  blurred?: boolean
  className?: string
}

export default function UniverseCanvas({
  interactive = true,
  blurred = false,
  className = '',
}: UniverseCanvasProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    // ── Renderer ──────────────────────────────────────────────────
    const renderer = new THREE.WebGLRenderer({
      canvas,
      antialias: true,
      alpha: false,
      powerPreference: 'high-performance',
    })
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, C.PIXEL_RATIO_CAP))
    renderer.setSize(canvas.clientWidth, canvas.clientHeight)
    renderer.setClearColor(0x030305, 1)

    // ── Scene & Camera ─────────────────────────────────────────────
    const scene = new THREE.Scene()
    const camera = new THREE.PerspectiveCamera(C.CAM_FOV, canvas.clientWidth / canvas.clientHeight, 0.1, 500)
    camera.position.z = C.CAM_Z

    // ── Lighting ───────────────────────────────────────────────────
    const ambient = new THREE.AmbientLight(0xffffff, 0.15)
    scene.add(ambient)

    const pointLight = new THREE.PointLight(0x6366f1, 6, 12)
    pointLight.position.set(0, 0, 2)
    scene.add(pointLight)

    const rimLight = new THREE.PointLight(0x38bdf8, 2, 8)
    rimLight.position.set(-3, 2, -1)
    scene.add(rimLight)

    // ── Central Orb ────────────────────────────────────────────────
    const orbGeo = new THREE.SphereGeometry(C.ORB_RADIUS, 96, 96)
    const orbMat = new THREE.MeshPhongMaterial({
      color: C.ORB_COLOR,
      emissive: C.ORB_EMISSIVE,
      emissiveIntensity: C.ORB_EMISSIVE_INTENSITY,
      shininess: 80,
      specular: 0xffffff,
    })
    const orb = new THREE.Mesh(orbGeo, orbMat)
    scene.add(orb)

    // Fake glow: 3 increasingly large transparent spheres (backside rendering)
    // Layer 1: tightest glow
    const glow1Geo = new THREE.SphereGeometry(C.ORB_RADIUS * 1.18, 32, 32)
    const glow1Mat = new THREE.MeshBasicMaterial({ color: 0x6366f1, transparent: true, opacity: 0.12, side: THREE.BackSide })
    scene.add(new THREE.Mesh(glow1Geo, glow1Mat))

    // Layer 2: mid glow
    const glow2Geo = new THREE.SphereGeometry(C.ORB_RADIUS * 1.5, 32, 32)
    const glow2Mat = new THREE.MeshBasicMaterial({ color: 0x818cf8, transparent: true, opacity: 0.06, side: THREE.BackSide })
    scene.add(new THREE.Mesh(glow2Geo, glow2Mat))

    // Layer 3: wide atmospheric scatter
    const glow3Geo = new THREE.SphereGeometry(C.ORB_RADIUS * 2.2, 32, 32)
    const glow3Mat = new THREE.MeshBasicMaterial({ color: 0x4338ca, transparent: true, opacity: 0.03, side: THREE.BackSide })
    scene.add(new THREE.Mesh(glow3Geo, glow3Mat))

    // ── Orbit Rings ────────────────────────────────────────────────
    C.RINGS.forEach(ring => {
      const ringGeo = buildRingGeometry(ring.radius, ring.tilt)
      const ringMat = new THREE.MeshBasicMaterial({
        color: ring.color,
        transparent: true,
        opacity: ring.opacity,
        side: THREE.DoubleSide,
      })
      scene.add(new THREE.Mesh(ringGeo, ringMat))
    })

    // ── Orbiting Nodes ─────────────────────────────────────────────
    const nodeMeshes: THREE.Mesh[] = []
    C.NODES.forEach(node => {
      const geo = new THREE.SphereGeometry(node.size, 16, 16)
      const mat = new THREE.MeshPhongMaterial({
        color: node.color,
        emissive: node.color,
        emissiveIntensity: node.type === 'packet' ? 0.9 : 0.5,
        shininess: 60,
      })
      const mesh = new THREE.Mesh(geo, mat)
      nodeMeshes.push(mesh)
      scene.add(mesh)
    })

    // ── Constellation Lines ────────────────────────────────────────
    // Lines are rebuilt each frame since node positions change
    // Use LineSegments with a pre-allocated BufferGeometry
    const linePositions = new Float32Array(C.CONSTELLATION_PAIRS.length * 2 * 3)
    const lineGeo = new THREE.BufferGeometry()
    lineGeo.setAttribute('position', new THREE.BufferAttribute(linePositions, 3))
    const lineMat = new THREE.LineBasicMaterial({
      color: 0x6366f1,
      transparent: true,
      opacity: 0.18,
    })
    const constellationLines = new THREE.LineSegments(lineGeo, lineMat)
    scene.add(constellationLines)

    // ── Star Field ─────────────────────────────────────────────────
    const starGeo = buildStarField()
    const starMat = new THREE.PointsMaterial({
      color: 0xffffff,
      size: 0.025,
      transparent: true,
      opacity: 0.7,
      sizeAttenuation: true,
    })
    scene.add(new THREE.Points(starGeo, starMat))

    // ── Mouse Parallax ─────────────────────────────────────────────
    let targetRotX = 0
    let targetRotY = 0
    let currentRotX = 0
    let currentRotY = 0

    const onMouseMove = (e: MouseEvent) => {
      if (!interactive) return
      const nx = (e.clientX / window.innerWidth  - 0.5) * 2  // -1 to 1
      const ny = (e.clientY / window.innerHeight - 0.5) * 2
      targetRotY =  nx * C.MOUSE_PARALLAX
      targetRotX = -ny * C.MOUSE_PARALLAX * 0.6
    }
    if (interactive) window.addEventListener('mousemove', onMouseMove)

    // ── Resize Handler ─────────────────────────────────────────────
    const onResize = () => {
      const w = canvas.clientWidth
      const h = canvas.clientHeight
      camera.aspect = w / h
      camera.updateProjectionMatrix()
      renderer.setSize(w, h)
    }
    window.addEventListener('resize', onResize)

    // ── Animation Loop ─────────────────────────────────────────────
    let animId: number
    let t = 0
    let lastTime = performance.now()

    const animate = (now: number) => {
      animId = requestAnimationFrame(animate)
      const dt = Math.min((now - lastTime) / 1000, 0.05)  // capped at 50ms
      lastTime = now
      t += dt

      // Auto-rotate scene group
      scene.rotation.y += C.SCENE_ROTATE_Y

      // Smooth mouse parallax
      if (interactive) {
        currentRotX = damp(currentRotX, targetRotX, 4, dt)
        currentRotY = damp(currentRotY, targetRotY, 4, dt)
        scene.rotation.x = currentRotX
        // Y rotation accumulates from auto-rotate + mouse, so add offset
        // We handle this by rotating a pivot group instead of scene directly
      }

      // Pulse orb emissive intensity
      orbMat.emissiveIntensity = C.ORB_EMISSIVE_INTENSITY + Math.sin(t * 1.4) * 0.2

      // Update node positions
      C.NODES.forEach((nodeConf, i) => {
        const speedMult = nodeConf.type === 'packet' ? C.PACKET_SPEED : 1
        const ring = C.RINGS[nodeConf.orbit]
        const angle = THREE.MathUtils.degToRad(nodeConf.angle) + t * ring.speed * speedMult
        const tilt = THREE.MathUtils.degToRad(ring.tilt)
        nodeMeshes[i].position.set(
          ring.radius * Math.cos(angle),
          ring.radius * Math.sin(angle) * Math.sin(tilt),
          ring.radius * Math.sin(angle) * Math.cos(tilt)
        )
      })

      // Update constellation lines
      const posAttr = lineGeo.attributes.position as THREE.BufferAttribute
      C.CONSTELLATION_PAIRS.forEach(([a, b], i) => {
        const pa = nodeMeshes[a].position
        const pb = nodeMeshes[b].position
        posAttr.setXYZ(i * 2,     pa.x, pa.y, pa.z)
        posAttr.setXYZ(i * 2 + 1, pb.x, pb.y, pb.z)
      })
      posAttr.needsUpdate = true

      renderer.render(scene, camera)
    }
    animate(performance.now())

    // ── Cleanup ────────────────────────────────────────────────────
    return () => {
      cancelAnimationFrame(animId)
      window.removeEventListener('mousemove', onMouseMove)
      window.removeEventListener('resize', onResize)
      renderer.dispose()
    }
  }, [interactive])

  return (
    <canvas
      ref={canvasRef}
      className={`universe-canvas ${className}`}
      style={{
        display: 'block',
        width: '100%',
        height: '100%',
        filter: blurred ? 'blur(14px) brightness(0.55) saturate(0.7)' : 'none',
        pointerEvents: blurred ? 'none' : 'auto',
        transition: 'filter 600ms ease',
      }}
    />
  )
}
```

---

## PART 4 — `AuthLayout.tsx`

**This replaces the individual background on `/login`, `/signup`, and `/status`.**
The existing page cards do NOT change — only the background is swapped.

```typescript
// src/layouts/AuthLayout.tsx
import { Outlet } from 'react-router-dom'
import UniverseCanvas from '../components/UniverseCanvas/UniverseCanvas'

export default function AuthLayout() {
  return (
    <div className="auth-layout">
      {/* Background: the universe, blurred */}
      <div className="auth-universe-bg" aria-hidden="true">
        <UniverseCanvas interactive={false} blurred={true} />
      </div>

      {/* Frosted glass overlay — sits between canvas and card */}
      <div className="auth-glass-overlay" aria-hidden="true" />

      {/* Page content (login card, signup card, status card) */}
      <div className="auth-content">
        <Outlet />
      </div>
    </div>
  )
}
```

```css
/* In index.css — add these rules */

.auth-layout {
  position: relative;
  width: 100vw;
  height: 100dvh;
  overflow: hidden;
  background: var(--bg-base);
}

/* Canvas fills full viewport, fixed behind everything */
.auth-universe-bg {
  position: absolute;
  inset: 0;
  z-index: 0;
}

/* Frosted glass: semi-transparent dark layer with backdrop blur */
.auth-glass-overlay {
  position: absolute;
  inset: 0;
  z-index: 1;
  background: rgba(3, 3, 5, 0.62);
  backdrop-filter: blur(0px);  /* canvas is already blurred; this adds depth */
}

/* Content sits on top of everything */
.auth-content {
  position: absolute;
  inset: 0;
  z-index: 2;
  display: flex;
  align-items: center;
  justify-content: center;
}
```

**Router update** — wrap auth routes in AuthLayout:
```tsx
// src/App.tsx — update route tree:
<Route element={<AuthLayout />}>
  <Route path="/login"  element={<Login />} />
  <Route path="/signup" element={<Signup />} />
  <Route path="/status" element={<VerificationStatus />} />
</Route>
```

**Remove** from Login.tsx, Signup.tsx, StatusPage.tsx:
- The old `.login-bg` div and its `dotGrid` animation CSS.
- The `position: relative; overflow: hidden` wrapper if it was only for the bg.
- Keep the card itself (everything inside and including the white/surface card) — it is unchanged.

The existing cards will now float over the blurred 3D universe. The effect:
The indigo glow from the orb bleeds through the blur, casting an ambient purple warmth behind the login card. The user is *approaching* something.

---

## PART 5 — LANDING PAGE DESIGN

### Route

Register in `App.tsx`:
```tsx
<Route path="/" element={<Landing />} />
```
This route is **outside** `AuthLayout` and outside `AppLayout`. It is fully standalone.

---

### `Landing.tsx` — Shell

```tsx
import HeroSection     from './sections/HeroSection'
import PipelineSection from './sections/PipelineSection'
import FeaturesSection from './sections/FeaturesSection'
import StatsSection    from './sections/StatsSection'
import CtaSection      from './sections/CtaSection'
import LandingNav      from './LandingNav'

export default function Landing() {
  return (
    <div className="landing-root">
      <LandingNav />
      <HeroSection />
      <PipelineSection />
      <FeaturesSection />
      <StatsSection />
      <CtaSection />
      <LandingFooter />
    </div>
  )
}
```

```css
/* Landing.css */
.landing-root {
  background: #030305;
  color: var(--text-1);
  min-height: 100vh;
  overflow-x: hidden;
}
```

---

### `LandingNav` — Top Navigation Bar

Position: `fixed`, top 0, full width. `z-index: 100`.

```css
.landing-nav {
  position: fixed;
  top: 0; left: 0; right: 0;
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 48px;
  z-index: 100;
  /* Glassmorphic nav: transparent by default, frosts as user scrolls */
  background: transparent;
  border-bottom: 1px solid transparent;
  transition: background 400ms ease, border-color 400ms ease, backdrop-filter 400ms ease;
}
.landing-nav.scrolled {
  background: rgba(3, 3, 5, 0.72);
  border-bottom-color: var(--border-subtle);
  backdrop-filter: blur(16px);
}
```

JS: `useEffect` with `window.addEventListener('scroll')`. Add `scrolled` class when `scrollY > 40`.

Left: Aegis shield SVG (22px) + "AEGIS" (15px/700 var(--text-1)) + "AML" (15px/700 var(--accent)).
Same shield as MasterPrompt.md sidebar logo.

Right: "Sign In" link (ghost-sm button, routes to `/login`) + "Request Access →" button (primary-sm).
8px gap between them.

---

### `HeroSection` — Full Viewport Universe

```css
.hero-section {
  position: relative;
  width: 100%;
  height: 100dvh;
  min-height: 640px;
  overflow: hidden;
}

/* Universe canvas fills the entire hero */
.hero-universe {
  position: absolute;
  inset: 0;
  z-index: 0;
}

/* Very subtle dark vignette at bottom to blend into next section */
.hero-vignette {
  position: absolute;
  bottom: 0; left: 0; right: 0;
  height: 280px;
  background: linear-gradient(to top, #030305 0%, transparent 100%);
  z-index: 2;
  pointer-events: none;
}

/* Hero text overlay — centered */
.hero-content {
  position: absolute;
  inset: 0;
  z-index: 3;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 0 24px;
  pointer-events: none;  /* canvas stays interactive underneath */
}
.hero-content > * { pointer-events: auto; }
```

**Inside `.hero-content`:** (all children animate in on mount with staggered `fadeInUp`)

1. **Product tag** (animates at 0ms):
   ```
   [ ● AEGIS AML · COMPLIANCE INTELLIGENCE ]
   ```
   Style: pill shape, `border: 1px solid rgba(99,102,241,0.4)`, `background: rgba(99,102,241,0.08)`,
   height 28px, padding 0 14px, font 11px/500 uppercase letter-spacing 0.06em `var(--accent-text)`.
   Leading dot: 6px circle `var(--accent)`, `animation: processingPulse 2s infinite`.

2. **H1 — Main headline** (animates at 120ms):
   ```
   From Suspicious Alert
   to Filed SAR in
   Under 10 Minutes.
   ```
   Font: 64px/700, `line-height: 1.1`, `letter-spacing: -0.035em`, `var(--text-1)`.
   On screens < 768px: 40px.
   The phrase "Under 10 Minutes." uses the gradient text from MasterPrompt login:
   ```css
   background: linear-gradient(135deg, #6366f1 0%, #818cf8 55%, #38bdf8 100%);
   -webkit-background-clip: text;
   -webkit-text-fill-color: transparent;
   ```

3. **Sub-headline** (animates at 240ms):
   ```
   AI-powered SAR generation for Indian fintechs and brokers.
   PMLA compliant · FIU-India ready · 8 AML typology checks.
   ```
   Font: 18px/400, `var(--text-2)`, max-width 520px, line-height 1.6.
   The bullet points ("·") are `var(--accent)` color.
   `margin-top: 20px`.

4. **CTA buttons** (animates at 360ms):
   Row, gap 12px.
   - "Request Access →" — primary, height 46px, padding 0 28px, font 15px/500.
     Has a very subtle outer glow: `box-shadow: 0 0 24px rgba(99,102,241,0.35)`.
     On hover: glow intensifies to `0 0 40px rgba(99,102,241,0.55)`, scale 1.02 (`var(--t-spring)`).
     Routes to `/signup`.
   - "Sign In" — secondary, height 46px, padding 0 28px, font 15px/500.
     Routes to `/login`.

5. **Social proof** (animates at 480ms):
   `margin-top: 32px`.
   ```
   Trusted by India's leading compliance teams
   ```
   Font: 12px `var(--text-4)`. Three small avatar circles (32px, indigo/emerald/sky bg, white initials) inline before the text, overlapping by -8px each.

**Scroll indicator** (bottom-centre of hero, animates in at 800ms):
```css
.scroll-hint {
  position: absolute;
  bottom: 32px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 4;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  opacity: 0.4;
  animation: scrollBounce 2s ease-in-out infinite;
}
@keyframes scrollBounce {
  0%, 100% { transform: translateX(-50%) translateY(0); }
  50%       { transform: translateX(-50%) translateY(5px); }
}
```
Contains: `ChevronDownIcon` (16px `var(--text-4)`) + "Scroll" (10px uppercase `var(--text-4)`).
Fades out once user has scrolled > 80px (`IntersectionObserver` on hero section).

---

### `PipelineSection` — How It Works

**Background:** `var(--bg-base)`. Full width. `padding: 120px 48px`.

**Section header** (centered, max-width 560px, margin auto):
- Tag: `[ HOW IT WORKS ]` — same pill style as hero tag.
- H2: "Three stages. Fully automated." — 40px/700, letter-spacing -0.025em.
- Sub: "From raw transaction data to a PMLA-compliant SAR, with your officer in the loop." — 16px `var(--text-3)`.

**Pipeline diagram** (the centrepiece, margin-top 64px):

```
  [ ALERT IN ]  ────►  [ AI ENGINE ]  ────►  [ SAR OUT ]
```

CSS: `display: flex; align-items: center; justify-content: center; gap: 0`.

**Three "stage" cards** (each 220px wide) with **animated arrows** between them.

Each card:
```css
.pipeline-card {
  width: 220px;
  background: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  border-radius: var(--r-xl);
  padding: 28px 24px;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  gap: 12px;
  position: relative;
  transition: border-color var(--t-slow), box-shadow var(--t-slow);
}
.pipeline-card:hover {
  border-color: var(--accent);
  box-shadow: 0 0 32px rgba(99,102,241,0.12);
}
```

Card 1 — "Alert In":
- Icon: `InboxIcon` (32px) in a 56px circle with `rgba(99,102,241,0.12)` bg and `rgba(99,102,241,0.3)` border.
- Title: "Transaction Alert" (16px/600).
- Description: "Raw JSON from your TMS, via API or webhook." (13px `var(--text-3)`).
- Tag below: "API · Webhook" (11px mono pill `var(--bg-elevated)` `var(--r-sm)`).

Card 2 — "AI Engine" (the orb card, slightly taller, has accent border):
- `border-color: var(--accent)` permanently.
- `box-shadow: 0 0 40px rgba(99,102,241,0.15)`.
- Icon: mini Aegis shield SVG (32px), animated `subtleFloat 4s infinite`.
- Title: "Aegis Engine" (16px/600).
- Description: "PII masking, 8 AML checks, Groq SAR draft generation." (13px `var(--text-3)`).
- Three tags: "PII Vault" + "AML Rules" + "Groq LLM" — same pill style.

Card 3 — "SAR Out":
- Icon: `FileCheckIcon` (32px) in a 56px circle with `rgba(34,197,94,0.12)` bg.
- Title: "Approved SAR" (16px/600).
- Description: "HMAC-signed PDF delivered to your endpoint, FIU-India ready." (13px `var(--text-3)`).
- Tag: "PMLA Compliant" (11px pill, `var(--success-subtle)` bg, `var(--success)` text).

**Animated arrows** (between cards):

```css
.pipeline-arrow {
  width: 80px;
  display: flex;
  align-items: center;
  position: relative;
  flex-shrink: 0;
}
.pipeline-arrow-line {
  height: 1px;
  background: linear-gradient(90deg, var(--border) 0%, var(--accent) 100%);
  flex: 1;
  position: relative;
  overflow: hidden;
}
/* Data packet animation — a bright dot travels along the line */
.pipeline-arrow-line::after {
  content: '';
  position: absolute;
  top: -2px;
  width: 6px;
  height: 5px;
  border-radius: 50%;
  background: var(--accent);
  box-shadow: 0 0 8px var(--accent);
  animation: travelRight 1.8s ease-in-out infinite;
}
@keyframes travelRight {
  0%   { left: -8px; opacity: 0; }
  10%  { opacity: 1; }
  90%  { opacity: 1; }
  100% { left: 100%; opacity: 0; }
}
.pipeline-arrow-head {
  width: 0; height: 0;
  border-top:    5px solid transparent;
  border-bottom: 5px solid transparent;
  border-left:   8px solid var(--accent);
}
```

**Section entrance animation:**
Use `IntersectionObserver` (threshold 0.2).
When section enters viewport:
- Cards fade in with `fadeInUp`, staggered 120ms (left, then arrow, then center, then arrow, then right).
- Arrow data packets start animating only after their preceding card has fully appeared.
Set initial `opacity: 0` on all pipeline children; add `is-visible` class when observed.

```css
.pipeline-card, .pipeline-arrow {
  opacity: 0;
  transform: translateY(16px);
  transition: opacity 500ms ease, transform 500ms ease;
}
.is-visible .pipeline-card,
.is-visible .pipeline-arrow { opacity: 1; transform: none; }
.is-visible .pipeline-card:nth-child(1) { transition-delay: 0ms; }
.is-visible .pipeline-arrow:nth-child(2) { transition-delay: 120ms; }
.is-visible .pipeline-card:nth-child(3) { transition-delay: 240ms; }
.is-visible .pipeline-arrow:nth-child(4) { transition-delay: 360ms; }
.is-visible .pipeline-card:nth-child(5) { transition-delay: 480ms; }
```

---

### `FeaturesSection` — The 6-Cell Feature Grid

**Background:** `var(--bg-base)`. `padding: 0 48px 120px`.

**Section header** (same structure as PipelineSection):
- Tag: `[ CAPABILITIES ]`
- H2: "Every tool compliance teams need."
- Sub: "Built specifically for India's PMLA framework. Nothing generic."

**6-card grid** (CSS grid `repeat(3, 1fr)`, gap 16px, margin-top 56px):

Each card: `var(--bg-surface)`, border `var(--border-subtle)`, `var(--r-xl)`, padding 28px.
Hover: `border-color var(--border)`, card rises slightly (`transform: translateY(-3px)`).
Each card entrance: `IntersectionObserver`, stagger 80ms.

| # | Icon | Title | Description |
|---|------|-------|-------------|
| 1 | `ShieldCheckIcon` (indigo) | AML Typology Engine | 8 deterministic checks: structuring, velocity, high-risk type, rapid movement, round-number, dormant activation, counterparty risk, and composite score. |
| 2 | `LockIcon` (amber) | PII Tokenization Vault | All customer identifiers are replaced with opaque tokens before leaving your system. Real data re-hydrates only on officer approval. |
| 3 | `SparklesIcon` (sky) | Groq SAR Generation | llama-3.3-70b-versatile drafts a full narrative SAR in under 8 seconds — structured for FIU-India's goAML format. |
| 4 | `FileTextIcon` (green) | 3-Panel Workspace | Transaction data, AML analysis, and the editable SAR draft — all visible simultaneously. No tab-switching. |
| 5 | `WebhookIcon` (purple) | HMAC-Signed Delivery | Approved SARs are PDF-rendered, signed with SHA-256, and delivered to your endpoint with retry logic. |
| 6 | `Building2Icon` (slate) | Multi-Tenant Isolation | Every alert, SAR, and key is row-level isolated. No tenant can touch another's data — ever. |

Each card structure:
```
[icon in colored 48px circle]
[feature title — 16px/600 margin-top 16px]
[description — 14px var(--text-3) margin-top 8px line-height 1.6]
```

Icon circle colors:
```
1: background rgba(99,102,241,0.12), border rgba(99,102,241,0.25)
2: background rgba(245,158,11,0.12), border rgba(245,158,11,0.25)
3: background rgba(56,189,248,0.12), border rgba(56,189,248,0.25)
4: background rgba(34,197,94,0.12),  border rgba(34,197,94,0.25)
5: background rgba(168,85,247,0.12), border rgba(168,85,247,0.25)
6: background rgba(113,113,122,0.12),border rgba(113,113,122,0.25)
```

---

### `StatsSection` — Numbers That Matter

**Background:** `var(--bg-surface)`, full-width section. `padding: 80px 48px`.
Top and bottom: 1px borders `var(--border-subtle)`.

**4 stat blocks** in a grid (`repeat(4, 1fr)`, dividers between):

Each block: centered text, `padding: 0 32px`.
Divider between blocks: `1px solid var(--border-subtle)` (right border on first 3).

| Stat | Label |
|------|-------|
| < 10 min | Per SAR, end-to-end |
| 8 | AML typology checks |
| PMLA 2002 | Compliance standard |
| 100% | Audit trail coverage |

Number: 48px/700, gradient text (same as hero headline "Under 10 Minutes.").
Label: 14px `var(--text-3)`, margin-top 8px.

Entrance: when section enters viewport, numbers count up from 0 using a JS counter
(for "< 10 min": count from 60 down to 10; for "8": count 0→8; for "100%": count 0→100).
Duration: 1400ms cubic-ease-out. Trigger once.

---

### `CtaSection` — Final Conversion

**Background:** `var(--bg-base)`. `padding: 80px 48px 120px`. Centered.

**Large card** (max-width 720px, margin auto):
```css
.cta-card {
  background: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  border-radius: 24px;
  padding: 64px;
  text-align: center;
  position: relative;
  overflow: hidden;
}
/* Ambient glow behind card */
.cta-card::before {
  content: '';
  position: absolute;
  top: 50%; left: 50%;
  transform: translate(-50%, -50%);
  width: 400px; height: 300px;
  background: radial-gradient(ellipse, rgba(99,102,241,0.10) 0%, transparent 70%);
  pointer-events: none;
}
```

Inside:
- Tag: `[ GET STARTED ]`
- H2: "Automate your compliance workflow." — 36px/700.
- Sub: "Join India's compliance-first fintechs using Aegis to cut SAR preparation time by 94%." — 16px `var(--text-3)`, max-width 480px, margin auto.
- CTA button row (margin-top 32px):
  "Request Access →" — primary, height 48px, font 16px/500. Same glow as hero CTA.
  Below button: "No commitment. Set up in under 10 minutes." (12px `var(--text-4)`, margin-top 12px).

---

### `LandingFooter`

Height 80px. `border-top var(--border-subtle)`. `padding: 0 48px`. Flex, space-between, align-center.

Left: Aegis logo (same as nav). Below logo: "© 2026 Aegis AML. All rights reserved." — 12px `var(--text-4)`.
Right: 3 text links (12px `var(--text-3)`, hover `var(--text-1)`): "Privacy Policy" · "Terms of Service" · "Contact".

---

## PART 6 — `Landing.css` KEYFRAMES

Add these to `Landing.css` (imported by `Landing.tsx`):

```css
/* ── Section entrance utility ── */
.section-header { text-align: center; max-width: 560px; margin: 0 auto; }
.section-tag {
  display: inline-flex; align-items: center; gap: 8px;
  border: 1px solid rgba(99,102,241,0.35);
  background: rgba(99,102,241,0.08);
  height: 28px; padding: 0 14px;
  border-radius: var(--r-full);
  font-size: 11px; font-weight: 500;
  letter-spacing: 0.06em; text-transform: uppercase;
  color: var(--accent-text);
  margin-bottom: 20px;
}
.section-h2 {
  font-size: 40px; font-weight: 700;
  letter-spacing: -0.025em;
  color: var(--text-1);
  line-height: 1.1;
}
.section-sub {
  font-size: 16px; color: var(--text-3);
  margin-top: 12px; line-height: 1.65;
}

/* ── Scroll-reveal base state ── */
.reveal { opacity: 0; transform: translateY(18px); transition: opacity 550ms ease, transform 550ms ease; }
.reveal.visible { opacity: 1; transform: none; }

/* ── Hero headline ── */
.hero-h1 {
  font-size: clamp(40px, 6vw, 68px);
  font-weight: 700;
  line-height: 1.08;
  letter-spacing: -0.035em;
  color: var(--text-1);
  max-width: 700px;
  margin-top: 16px;
}
.hero-gradient-text {
  background: linear-gradient(135deg, #6366f1 0%, #818cf8 55%, #38bdf8 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}
.hero-sub {
  font-size: 18px; font-weight: 400;
  color: var(--text-2); max-width: 520px;
  margin-top: 20px; line-height: 1.65;
}
.hero-sub .dot { color: var(--accent); }

/* ── CTA Button glow ── */
.btn-hero-cta {
  box-shadow: 0 0 24px rgba(99,102,241,0.35);
  transition: box-shadow var(--t-slow), transform var(--t-spring) !important;
}
.btn-hero-cta:hover {
  box-shadow: 0 0 48px rgba(99,102,241,0.55) !important;
  transform: scale(1.03) !important;
}

/* ── Feature card hover ── */
.feature-card {
  transition: border-color var(--t-slow), transform var(--t-slow), box-shadow var(--t-slow);
}
.feature-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 12px 40px -8px rgba(0,0,0,0.5);
  border-color: var(--border);
}
```

---

## PART 7 — PERFORMANCE CHECKLIST

Fable must implement all of these:

- [ ] `devicePixelRatio` capped at `PIXEL_RATIO_CAP = 1.5` (prevents 4K canvas on retina displays)
- [ ] `cancelAnimationFrame` in the `useEffect` cleanup
- [ ] Three.js `renderer.dispose()` in cleanup
- [ ] `IntersectionObserver` for all section animations (no scroll event listeners in animation loop)
- [ ] Canvas `width/height` set from `canvas.clientWidth/clientHeight`, not hardcoded
- [ ] `ResizeObserver` on canvas container to handle panel resize
- [ ] `will-change: transform` on animated elements (hero content, section cards)
- [ ] `pointer-events: none` on `hero-vignette`, `auth-glass-overlay`, `.auth-universe-bg`
- [ ] On mobile (viewport < 640px): halve `STAR_COUNT` to 900, reduce `RINGS` to 2 rings, disable mouse parallax
- [ ] WebGL fallback: if `canvas.getContext('webgl2')` fails, render a static CSS radial gradient background (deep purple/indigo) instead of showing a blank screen

---

## PART 8 — NODE LABEL TOOLTIPS (Landing Page Only)

When `interactive={true}`, hovering a Three.js node (orbiting sphere) shows a CSS tooltip above it.

**How to implement:**
1. On each animation frame, project every node's 3D position to 2D screen space:
   ```typescript
   const projected = nodePos.clone().project(camera)
   const x = (projected.x  + 1) / 2 * canvasWidth
   const y = (-projected.y + 1) / 2 * canvasHeight
   ```
2. Maintain a separate `<div className="universe-labels">` overlay (position absolute, inset 0, pointer-events none, z-index 5) inside the hero section.
3. For each node with a non-empty label, render a `<span className="node-label">` absolutely positioned at `(x, y)` with `transform: translate(-50%, -120%)`.
4. Labels for all nodes with labels are always rendered (not just on hover). They should be:
   - 10px/500, `var(--font-mono)`, `var(--text-3)`.
   - Background: `rgba(3,3,5,0.7)`, border `var(--border-subtle)`, `var(--r-sm)`, padding `2px 6px`.
   - `pointer-events: none`.
   - Opacity varies with z-depth: nodes closer to camera (projected.z < 0.5) = opacity 0.85, further away = opacity 0.3.
5. Node type colors: `type === 'sar'` → `var(--text-3)`. `type === 'rule'` → `var(--warning)`. `type === 'alert'` → `var(--danger)`. Packets: no label rendered.

```css
.universe-labels {
  position: absolute; inset: 0;
  pointer-events: none;
  z-index: 5;
  overflow: hidden;
}
.node-label {
  position: absolute;
  white-space: nowrap;
  transition: opacity 300ms;
}
```

---

## PART 9 — INTERSECTION OBSERVER UTILITY

Create once, use everywhere in Landing sections:

```typescript
// src/hooks/useReveal.ts
import { useEffect, useRef } from 'react'

export function useReveal(options?: IntersectionObserverInit) {
  const ref = useRef<HTMLElement>(null)
  useEffect(() => {
    const el = ref.current
    if (!el) return
    const obs = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting) {
        el.querySelectorAll('.reveal').forEach((child, i) => {
          setTimeout(() => child.classList.add('visible'), i * 80)
        })
        obs.disconnect()
      }
    }, { threshold: 0.15, ...options })
    obs.observe(el)
    return () => obs.disconnect()
  }, [])
  return ref
}
```

Usage:
```tsx
const sectionRef = useReveal()
<section ref={sectionRef as any}>
  <div className="reveal">...</div>
  <div className="reveal">...</div>
</section>
```

---

## FINAL CHECKLIST — Fable must verify before declaring done

- [ ] `UniverseCanvas` renders in Three.js without console errors
- [ ] Central orb glows indigo with 3-layer fake bloom
- [ ] All 3 orbit rings visible and rotating at correct tilts
- [ ] 9 named nodes + 3 packets orbit on correct rings
- [ ] Constellation lines draw between correct node pairs and update each frame
- [ ] 1800-star field fills the background
- [ ] Mouse parallax: scene gently follows cursor on landing page (not on auth)
- [ ] `AuthLayout.tsx` created, router updated to wrap auth routes
- [ ] Login/signup/status show blurred universe background through frosted glass
- [ ] Old `.login-bg` dot-grid removed from Login.tsx, Signup.tsx, StatusPage.tsx
- [ ] Landing nav: transparent → glassmorphic on scroll
- [ ] Hero: orb + full-screen Three.js canvas + text overlay + scroll indicator
- [ ] Hero headline uses clamp() for responsive font size
- [ ] "Under 10 Minutes." has gradient text treatment
- [ ] All hero content items animate in with stagger on mount
- [ ] Pipeline section: 3 cards + 2 animated arrows + data-packet travel animation
- [ ] Pipeline cards animate in on scroll (IntersectionObserver)
- [ ] Features section: 6-card grid, all icons in colored circles, hover lift
- [ ] Stats section: all 4 numbers count up on scroll entry (one-time)
- [ ] CTA section: card with ambient glow, hero-glow button
- [ ] Footer: logo + copyright + 3 links
- [ ] Node labels render at correct 2D positions over canvas
- [ ] Label opacity varies by node z-depth
- [ ] WebGL fallback renders gradient if context fails
- [ ] Mobile: star count halved, mouse parallax disabled
- [ ] `renderer.dispose()` + `cancelAnimationFrame` in every cleanup
- [ ] No layout shift on page load (canvas is position:absolute, not in flow)

---

## ⛔ STOP INSTRUCTION ⛔

When every item above is checked:

> "✅ LANDING + AUTH BG COMPLETE.
> UniverseCanvas live with Three.js. Landing page all 5 sections built.
> Auth pages show blurred universe behind frosted glass.
> Route `/` active. AuthLayout wraps /login, /signup, /status.
> Ready for backend integration."

**Do NOT write any Python, FastAPI, database, or Docker files. STOP here.**
