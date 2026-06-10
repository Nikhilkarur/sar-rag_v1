import * as THREE from 'three'
import { UNIVERSE_CONFIG as C } from './universe.config'

/**
 * Compute a node's world position given its orbit ring, angle, the ring tilt,
 * and elapsed time. Packets pass speedMult = PACKET_SPEED to travel faster.
 */
export function nodePosition(
  orbitIndex: number,
  angleDeg: number,
  time: number,
  speedMult = 1,
  out?: THREE.Vector3,
): THREE.Vector3 {
  const ring = C.RINGS[orbitIndex]
  // ring.speed is tuned per-frame; scale to per-second for time-based motion
  const a = THREE.MathUtils.degToRad(angleDeg) + time * ring.speed * 60 * speedMult
  const tilt = THREE.MathUtils.degToRad(ring.tilt)

  // Parametric orbit on tilted plane
  const x = ring.radius * Math.cos(a)
  const y = ring.radius * Math.sin(a) * Math.sin(tilt)
  const z = ring.radius * Math.sin(a) * Math.cos(tilt)
  const v = out ?? new THREE.Vector3()
  return v.set(x, y, z)
}

/** Build a BufferGeometry for a flat orbit ring (torus cross-section = 0.004) */
export function buildRingGeometry(radius: number, tiltDeg: number): THREE.BufferGeometry {
  const geo = new THREE.TorusGeometry(radius, 0.004, 8, 128)
  // TorusGeometry lies in the XY plane: points (r·cos a, r·sin a, 0).
  // Node orbits are (r·cos a, r·sin a·sin t, r·sin a·cos t) — rotating the
  // torus by (π/2 − t) about X maps (·, sin a, 0) → (·, sin a·sin t, sin a·cos t),
  // so rings sit exactly on their nodes' orbital planes.
  geo.rotateX(Math.PI / 2 - THREE.MathUtils.degToRad(tiltDeg))
  return geo
}

/** Generate random star field positions */
export function buildStarField(count: number): THREE.BufferGeometry {
  const positions = new Float32Array(count * 3)
  for (let i = 0; i < count; i++) {
    positions[i * 3] = (Math.random() - 0.5) * 160
    positions[i * 3 + 1] = (Math.random() - 0.5) * 160
    positions[i * 3 + 2] = C.STAR_DEPTH[0] + Math.random() * (C.STAR_DEPTH[1] - C.STAR_DEPTH[0])
  }
  const geo = new THREE.BufferGeometry()
  geo.setAttribute('position', new THREE.BufferAttribute(positions, 3))
  return geo
}

/** Lerp a value with damping (smooth, frame-rate independent follow) */
export function damp(current: number, target: number, lambda: number, dt: number): number {
  return THREE.MathUtils.lerp(current, target, 1 - Math.exp(-lambda * dt))
}
