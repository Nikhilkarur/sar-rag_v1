import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { ChevronDown } from 'lucide-react'
import UniverseCanvas from '../../../components/UniverseCanvas/UniverseCanvas'
import { cls } from '../../../utils/format'

const AVATARS = [
  { initials: 'RK', bg: 'var(--accent)' },
  { initials: 'AP', bg: '#10b981' },
  { initials: 'SM', bg: 'var(--info)' },
]

export default function HeroSection() {
  const heroRef = useRef<HTMLElement>(null)
  const [scrolledPast, setScrolledPast] = useState(false)

  useEffect(() => {
    const onScroll = () => setScrolledPast(window.scrollY > 80)
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  return (
    <section ref={heroRef} className="hero-section">
      {/* The universe */}
      <div className="hero-universe">
        <UniverseCanvas interactive />
      </div>

      {/* Bottom vignette blends into next section */}
      <div className="hero-vignette" aria-hidden="true" />

      {/* Text overlay */}
      <div className="hero-content">
        {/* 1 — Product tag */}
        <div className="hero-stagger" style={{ animationDelay: '0ms' }}>
          <span className="section-tag" style={{ marginBottom: 0 }}>
            <span
              style={{
                width: 6,
                height: 6,
                borderRadius: '50%',
                background: 'var(--accent)',
                animation: 'processingPulse 2s infinite',
                flexShrink: 0,
              }}
            />
            Aegis AML · Compliance Intelligence
          </span>
        </div>

        {/* 2 — Headline */}
        <h1 className="hero-h1 hero-stagger" style={{ animationDelay: '120ms' }}>
          Stop Chasing False Positives.
          <br />
          Start Filing <span className="hero-gradient-text">Intelligent SARs.</span>
        </h1>

        {/* 3 — Sub-headline */}
        <p className="hero-sub hero-stagger" style={{ animationDelay: '240ms' }}>
          AI-powered SAR generation for Indian fintechs and brokers.
          <br />
          PMLA compliant <span className="dot">·</span> FIU-India ready{' '}
          <span className="dot">·</span> 8 AML typology checks.
        </p>

        {/* 4 — CTAs */}
        <div
          className="hero-stagger"
          style={{ animationDelay: '360ms', display: 'flex', gap: 12, marginTop: 32, flexWrap: 'wrap', justifyContent: 'center' }}
        >
          <Link to="/signup" className="btn-landing btn-landing-primary btn-hero-cta">
            Request Access →
          </Link>
          <Link to="/login" className="btn-landing btn-landing-secondary">
            Sign In
          </Link>
        </div>

        {/* 5 — Social proof */}
        <div
          className="hero-stagger"
          style={{
            animationDelay: '480ms',
            marginTop: 32,
            display: 'flex',
            alignItems: 'center',
            gap: 12,
          }}
        >
          <span style={{ display: 'inline-flex' }}>
            {AVATARS.map((a, i) => (
              <span
                key={a.initials}
                style={{
                  width: 32,
                  height: 32,
                  borderRadius: '50%',
                  background: a.bg,
                  border: '2px solid #030305',
                  color: '#fff',
                  fontSize: 11,
                  fontWeight: 600,
                  display: 'inline-flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  marginLeft: i === 0 ? 0 : -8,
                  position: 'relative',
                  zIndex: AVATARS.length - i,
                }}
              >
                {a.initials}
              </span>
            ))}
          </span>
          <span style={{ fontSize: 12, color: 'var(--text-4)' }}>
            Trusted by India's leading compliance teams
          </span>
        </div>
      </div>

      {/* Scroll indicator */}
      <div className={cls('scroll-hint', scrolledPast && 'hidden')}>
        <ChevronDown size={16} color="var(--text-4)" />
        <span
          style={{
            fontSize: 10,
            textTransform: 'uppercase',
            letterSpacing: '0.08em',
            color: 'var(--text-4)',
          }}
        >
          Scroll
        </span>
      </div>
    </section>
  )
}
