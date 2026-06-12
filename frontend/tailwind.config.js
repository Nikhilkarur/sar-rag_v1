/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        // Backgrounds — light mode (legacy names kept; values remapped)
        obsidian:  '#FFFFFF',
        surface:   '#FFFFFF',
        'surface-2': '#FAFAF9',
        'surface-3': '#F4F4F3',
        overlay:   '#EFEFED',

        // Borders
        'border-dim':    '#EEEEEC',
        'border-base':   '#E4E4E2',
        'border-strong': '#CFCFCD',

        // Accent — brand emerald
        'electric':      '#064E3B',
        'electric-dim':  '#ECF5F1',
        'electric-text': '#066049',

        // Risk
        'risk-high':     '#C0392B',
        'risk-high-dim': '#FCF0EE',
        'risk-med':      '#9A6700',
        'risk-med-dim':  '#FBF4E5',
        'risk-low':      '#067647',
        'risk-low-dim':  '#EBF6F0',

        // Text
        'ink-1': '#151515',
        'ink-2': '#4A4A48',
        'ink-3': '#7D7D7A',
        'ink-4': '#ABABA8',
      },
      fontFamily: {
        sans: ['Inter', '-apple-system', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', '"Fira Code"', 'monospace'],
        serif: ['Inter', '-apple-system', 'system-ui', 'sans-serif'],
        display: ['Inter', '-apple-system', 'system-ui', 'sans-serif'],
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
        'glow-blue':   '0 0 0 1px rgba(6,78,59,0.2)',
        'glow-red':    '0 0 0 1px rgba(192,57,43,0.25)',
        'glow-yellow': '0 0 0 1px rgba(154,103,0,0.25)',
        'glow-green':  '0 0 0 1px rgba(6,118,71,0.25)',
        'focus':       '0 0 0 3px rgba(6,78,59,0.12)',
        'modal':       '0 1px 2px rgba(0,0,0,0.06), 0 16px 40px -12px rgba(0,0,0,0.16)',
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
        'scale-in':    'scaleIn 160ms ease-out',
        'slide-in-r':  'slideInR 200ms ease-out',
        'pulse-slow':  'pulse 3s ease-in-out infinite',
        'glow-pulse':  'glowPulse 2s ease-in-out infinite',
      },
      keyframes: {
        fadeIn:    { from: { opacity: 0 },                    to: { opacity: 1 } },
        fadeUp:    { from: { opacity: 0, transform: 'translateY(6px)' }, to: { opacity: 1, transform: 'none' } },
        scaleIn:   { from: { opacity: 0, transform: 'scale(0.98)' },    to: { opacity: 1, transform: 'scale(1)' } },
        slideInR:  { from: { opacity: 0, transform: 'translateX(8px)' }, to: { opacity: 1, transform: 'none' } },
        glowPulse: {
          '0%,100%': { opacity: 1 },
          '50%':     { opacity: 0.65 },
        },
      },
    },
  },
  plugins: [],
}
