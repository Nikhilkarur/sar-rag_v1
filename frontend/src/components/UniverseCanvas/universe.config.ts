export type UniverseNodeType = 'sar' | 'rule' | 'alert' | 'packet'

export interface UniverseRing {
  radius: number
  tilt: number
  speed: number
  color: number
  opacity: number
}

export interface UniverseNode {
  orbit: number
  angle: number
  size: number
  color: number
  label: string
  type: UniverseNodeType
}

/**
 * The Ancient Astrolabe — an emerald world ringed by the financial
 * intelligence web. Inner ring: filed SARs (ink). Middle ring: AML
 * typology rules (gold). Outer ring: live transaction alerts (crimson).
 * Gold-dust packets ferry data between them.
 */
export const UNIVERSE_CONFIG = {
  // Orb — polished emerald under light: bright enough to read as a gem,
  // never a dark void behind the headline
  ORB_RADIUS: 0.78,
  ORB_COLOR: 0x0e7a5a,
  ORB_EMISSIVE: 0x064e3b,
  ORB_EMISSIVE_INTENSITY: 0.55,
  ORB_GLOW_LAYERS: 2, // tight atmosphere only — no giant blurry halo

  // Orbit rings (purely visual, no physics)
  RINGS: [
    { radius: 1.6, tilt: 0, speed: 0.0007, color: 0x064e3b, opacity: 0.13 },
    { radius: 2.4, tilt: 55, speed: -0.0005, color: 0xc9a227, opacity: 0.1 },
    { radius: 3.2, tilt: 110, speed: 0.00035, color: 0x0e7490, opacity: 0.08 },
  ] as UniverseRing[],

  // Orbiting nodes (the AML transaction graph)
  NODES: [
    // Filed SARs — ink on marble
    { orbit: 0, angle: 0, size: 0.07, color: 0x171717, label: 'SAR-2026-892', type: 'sar' },
    { orbit: 0, angle: 120, size: 0.06, color: 0x171717, label: 'SAR-2026-893', type: 'sar' },
    { orbit: 0, angle: 240, size: 0.05, color: 0x171717, label: 'STR → FIU-IND', type: 'sar' },
    // AML typology rules — crisp gold
    { orbit: 1, angle: 30, size: 0.08, color: 0xc9a227, label: 'STRUCTURING ALERT', type: 'rule' },
    { orbit: 1, angle: 150, size: 0.07, color: 0xc9a227, label: 'HIGH-VELOCITY TRANSFERS', type: 'rule' },
    { orbit: 1, angle: 270, size: 0.06, color: 0xc9a227, label: 'LAYERING PATTERN', type: 'rule' },
    // Live transaction alerts — crimson
    { orbit: 2, angle: 60, size: 0.09, color: 0xb3382c, label: '₹50,00,000', type: 'alert' },
    { orbit: 2, angle: 180, size: 0.07, color: 0xb3382c, label: '₹9,90,000', type: 'alert' },
    { orbit: 2, angle: 300, size: 0.06, color: 0xb3382c, label: 'SHELL COMPANY SUSPECTED', type: 'alert' },
    // Data packets — gold couriers ferrying the graph (buttery flow)
    { orbit: 0, angle: 60, size: 0.022, color: 0xd4af37, label: '', type: 'packet' },
    { orbit: 0, angle: 300, size: 0.02, color: 0xd4af37, label: '', type: 'packet' },
    { orbit: 1, angle: 200, size: 0.022, color: 0xd4af37, label: '', type: 'packet' },
    { orbit: 1, angle: 80, size: 0.02, color: 0xd4af37, label: '', type: 'packet' },
    { orbit: 2, angle: 130, size: 0.022, color: 0xd4af37, label: '', type: 'packet' },
    { orbit: 2, angle: 250, size: 0.02, color: 0xd4af37, label: '', type: 'packet' },
  ] as UniverseNode[],

  // Constellation lines — the transaction graph
  CONSTELLATION_PAIRS: [
    [0, 3], [1, 4], [2, 5], // SARs connect to the rules that triggered them
    [3, 6], [4, 7], [5, 8], // Rules connect to the live alerts they fired on
    [0, 1], [3, 4], // Same-orbit connections
  ] as [number, number][],

  // Gold-dust field
  STAR_COUNT: 1800,
  STAR_COUNT_MOBILE: 900,
  STAR_SIZE_MIN: 0.012,
  STAR_SIZE_MAX: 0.032,
  STAR_DEPTH: [-80, -20] as [number, number], // z range

  // Camera
  CAM_Z: 5.0,
  CAM_FOV: 58,
  MOUSE_PARALLAX: 0.18, // max rotation in radians from mouse

  // Animation — buttery
  SCENE_ROTATE_Y: 0.00022, // base auto-rotation per frame
  PACKET_SPEED: 1.8, // multiplier for data packet nodes
  PARALLAX_DAMP: 5.5, // higher = snappier-yet-smooth mouse follow

  // Performance
  PIXEL_RATIO_CAP: 2, // allow retina sharpness — fluidity is the point
  MOBILE_BREAKPOINT: 640,
}
