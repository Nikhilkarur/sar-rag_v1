import { Link } from 'react-router-dom'
import { useReveal } from '../../../hooks/useReveal'

export default function CtaSection() {
  const sectionRef = useReveal<HTMLElement>()

  return (
    <section ref={sectionRef} style={{ background: 'var(--bg-base)', padding: '80px 48px 120px' }}>
      <div className="cta-card reveal">
        <span className="section-tag">Get Started</span>
        <h2 style={{ fontSize: 36, fontWeight: 700, letterSpacing: '-0.025em', lineHeight: 1.15 }}>
          Automate your compliance workflow.
        </h2>
        <p
          className="section-sub"
          style={{ maxWidth: 480, marginLeft: 'auto', marginRight: 'auto' }}
        >
          Join India's compliance-first fintechs using Aegis to cut SAR preparation time by 94%.
        </p>
        <div style={{ marginTop: 32, position: 'relative' }}>
          <Link
            to="/signup"
            className="btn-landing btn-landing-primary btn-hero-cta"
            style={{ height: 48, fontSize: 16 }}
          >
            Request Access →
          </Link>
          <div style={{ fontSize: 12, color: 'var(--text-4)', marginTop: 12 }}>
            No commitment. Set up in under 10 minutes.
          </div>
        </div>
      </div>
    </section>
  )
}
