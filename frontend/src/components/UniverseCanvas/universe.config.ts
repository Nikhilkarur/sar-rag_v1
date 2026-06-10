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

export const UNIVERSE_CONFIG = {
  // Orb
  ORB_RADIUS: 0.78,
  ORB_COLOR: 0x6366f1,
  ORB_EMISSIVE: 0x4338ca,
  ORB_EMISSIVE_INTENSITY: 0.4,
  ORB_GLOW_LAYERS: 3, // concentric transparent spheres for bloom fake

  // Orbit rings (purely visual, no physics)
  RINGS: [
    { radius: 1.6, tilt: 0, speed: 0.0006, color: 0x6366f1, opacity: 0.06 },
    { radius: 2.4, tilt: 55, speed: -0.0004, color: 0x818cf8, opacity: 0.04 },
    { radius: 3.2, tilt: 110, speed: 0.0003, color: 0x38bdf8, opacity: 0.03 },
  ] as UniverseRing[],

  // Orbiting nodes (the "compliance graph")
  NODES: [
    // SAR documents
    { orbit: 0, angle: 0, size: 0.07, color: 0xf4f4f5, label: 'SAR-2026-001', type: 'sar' },
    { orbit: 0, angle: 120, size: 0.06, color: 0xf4f4f5, label: 'SAR-2026-002', type: 'sar' },
    { orbit: 0, angle: 240, size: 0.05, color: 0xf4f4f5, label: 'SAR-2026-003', type: 'sar' },
    // AML rules
    { orbit: 1, angle: 30, size: 0.08, color: 0xf59e0b, label: 'STRUCTURING', type: 'rule' },
    { orbit: 1, angle: 150, size: 0.07, color: 0xf59e0b, label: 'RAPID_MOVEMENT', type: 'rule' },
    { orbit: 1, angle: 270, size: 0.06, color: 0xf59e0b, label: 'VELOCITY', type: 'rule' },
    // Transaction alerts
    { orbit: 2, angle: 60, size: 0.09, color: 0xef4444, label: '₹9,90,000', type: 'alert' },
    { orbit: 2, angle: 180, size: 0.07, color: 0xef4444, label: '₹24,50,000', type: 'alert' },
    { orbit: 2, angle: 300, size: 0.06, color: 0xef4444, label: 'HIGH RISK', type: 'alert' },
    // Data packets (tiny, fast, no label)
    { orbit: 0, angle: 60, size: 0.02, color: 0x818cf8, label: '', type: 'packet' },
    { orbit: 1, angle: 200, size: 0.02, color: 0x818cf8, label: '', type: 'packet' },
    { orbit: 2, angle: 130, size: 0.02, color: 0x6366f1, label: '', type: 'packet' },
  ] as UniverseNode[],

  // Constellation lines (pairs of node indices to connect)
  CONSTELLATION_PAIRS: [
    [0, 3], [1, 4], [2, 5], // SARs connect to rules
    [3, 6], [4, 7], [5, 8], // Rules connect to alerts
    [0, 1], [3, 4], // Same-orbit connections
  ] as [number, number][],

  // Star field
  STAR_COUNT: 1800,
  STAR_COUNT_MOBILE: 900,
  STAR_SIZE_MIN: 0.012,
  STAR_SIZE_MAX: 0.032,
  STAR_DEPTH: [-80, -20] as [number, number], // z range

  // Camera
  CAM_Z: 5.0,
  CAM_FOV: 58,
  MOUSE_PARALLAX: 0.18, // max rotation in radians from mouse

  // Animation
  SCENE_ROTATE_Y: 0.00015, // base auto-rotation per frame
  PACKET_SPEED: 1.8, // multiplier for data packet nodes

  // Performance
  PIXEL_RATIO_CAP: 1.5, // cap devicePixelRatio for perf
  MOBILE_BREAKPOINT: 640,
}
