/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        // Backgrounds
        obsidian:  '#0A0A0A',
        surface:   '#111111',
        'surface-2': '#161616',
        'surface-3': '#1C1C1C',
        overlay:   '#222222',

        // Borders
        'border-dim':    '#1E1E1E',
        'border-base':   '#2A2A2A',
        'border-strong': '#3A3A3A',

        // Accent
        'electric':      '#3B82F6',
        'electric-dim':  'rgba(59,130,246,0.12)',
        'electric-text': '#93C5FD',

        // Risk
        'risk-high':     '#FF4444',
        'risk-high-dim': 'rgba(255,68,68,0.10)',
        'risk-med':      '#FFBB00',
        'risk-med-dim':  'rgba(255,187,0,0.10)',
        'risk-low':      '#00CC66',
        'risk-low-dim':  'rgba(0,204,102,0.10)',

        // Text
        'ink-1': '#FFFFFF',
        'ink-2': '#A1A1AA',
        'ink-3': '#52525B',
        'ink-4': '#3F3F46',
      },
      fontFamily: {
        sans: ['Inter', '-apple-system', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', '"Fira Code"', 'monospace'],
        serif: ['"Playfair Display"', 'Georgia', 'serif'],
        display: ['Outfit', 'Inter', 'system-ui', 'sans-serif'],
        logo: ['Cinzel', 'Georgia', 'serif'],
      },
      fontSize: {
        '2xs': ['10px', { lineHeight: '14px', letterSpacing: '0.05em' }],
        xs:    ['11px', { lineHeight: '16px' }],
        sm:    ['12px', { lineHeight: '18px' }],
        base:  ['13px', { lineHeight: '20px' }],
        md:    ['14px', { lineHeight: '22px' }],
        lg:    ['16px', { lineHeight: '24px' }],
        xl:    ['18px', { lineHeight: '26px' }],
        '2xl': ['22px', { lineHeight: '30px' }],
        '3xl': ['28px', { lineHeight: '36px' }],
      },
      boxShadow: {
        'glow-blue':   '0 0 0 1px rgba(59,130,246,0.25), 0 0 16px rgba(59,130,246,0.08)',
        'glow-red':    '0 0 0 1px rgba(255,68,68,0.3),  0 0 12px rgba(255,68,68,0.08)',
        'glow-yellow': '0 0 0 1px rgba(255,187,0,0.25), 0 0 12px rgba(255,187,0,0.06)',
        'glow-green':  '0 0 0 1px rgba(0,204,102,0.25), 0 0 12px rgba(0,204,102,0.06)',
        'focus':       '0 0 0 2px rgba(59,130,246,0.4)',
        'modal':       '0 24px 48px rgba(0,0,0,0.8), 0 0 0 1px #2A2A2A',
      },
      borderRadius: {
        DEFAULT: '6px',
        sm: '4px',
        md: '6px',
        lg: '8px',
        xl: '12px',
      },
      animation: {
        'fade-in':     'fadeIn 150ms ease-out',
        'fade-up':     'fadeUp 200ms ease-out',
        'scale-in':    'scaleIn 200ms cubic-bezier(0.34,1.56,0.64,1)',
        'slide-in-r':  'slideInR 200ms ease-out',
        'pulse-slow':  'pulse 3s ease-in-out infinite',
        'glow-pulse':  'glowPulse 2s ease-in-out infinite',
      },
      keyframes: {
        fadeIn:    { from: { opacity: 0 },                    to: { opacity: 1 } },
        fadeUp:    { from: { opacity: 0, transform: 'translateY(8px)' }, to: { opacity: 1, transform: 'none' } },
        scaleIn:   { from: { opacity: 0, transform: 'scale(0.95)' },    to: { opacity: 1, transform: 'scale(1)' } },
        slideInR:  { from: { opacity: 0, transform: 'translateX(12px)' }, to: { opacity: 1, transform: 'none' } },
        glowPulse: {
          '0%,100%': { boxShadow: '0 0 0 1px rgba(255,68,68,0.3)' },
          '50%':     { boxShadow: '0 0 0 1px rgba(255,68,68,0.6), 0 0 20px rgba(255,68,68,0.12)' },
        },
      },
    },
  },
  plugins: [],
}
