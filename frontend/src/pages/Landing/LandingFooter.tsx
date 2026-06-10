import { AegisShield } from '../../components/AegisLogo'

export default function LandingFooter() {
  return (
    <footer className="landing-footer">
      <div>
        <div style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}>
          <AegisShield size={20} />
          <span style={{ fontSize: 14, fontWeight: 700 }}>
            <span style={{ color: 'var(--text-1)' }}>AEGIS</span>{' '}
            <span style={{ color: 'var(--accent)' }}>AML</span>
          </span>
        </div>
        <div style={{ fontSize: 12, color: 'var(--text-4)', marginTop: 4 }}>
          © 2026 Aegis AML. All rights reserved.
        </div>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <a href="#privacy">Privacy Policy</a>
        <span style={{ color: 'var(--text-4)', fontSize: 12 }}>·</span>
        <a href="#terms">Terms of Service</a>
        <span style={{ color: 'var(--text-4)', fontSize: 12 }}>·</span>
        <a href="mailto:support@aegis-aml.com">Contact</a>
      </div>
    </footer>
  )
}
