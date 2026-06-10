import { Building2, FileText, Lock, ShieldCheck, Sparkles, Webhook } from 'lucide-react'
import { useReveal } from '../../../hooks/useReveal'

const FEATURES = [
  {
    icon: <ShieldCheck size={22} color="#a5b4fc" />,
    circle: { background: 'rgba(99,102,241,0.12)', border: '1px solid rgba(99,102,241,0.25)' },
    title: 'AML Typology Engine',
    description:
      '8 deterministic checks: structuring, velocity, high-risk type, rapid movement, round-number, dormant activation, counterparty risk, and composite score.',
  },
  {
    icon: <Lock size={22} color="#f59e0b" />,
    circle: { background: 'rgba(245,158,11,0.12)', border: '1px solid rgba(245,158,11,0.25)' },
    title: 'PII Tokenization Vault',
    description:
      'All customer identifiers are replaced with opaque tokens before leaving your system. Real data re-hydrates only on officer approval.',
  },
  {
    icon: <Sparkles size={22} color="#38bdf8" />,
    circle: { background: 'rgba(56,189,248,0.12)', border: '1px solid rgba(56,189,248,0.25)' },
    title: 'Groq SAR Generation',
    description:
      "llama-3.3-70b-versatile drafts a full narrative SAR in under 8 seconds — structured for FIU-India's goAML format.",
  },
  {
    icon: <FileText size={22} color="#22c55e" />,
    circle: { background: 'rgba(34,197,94,0.12)', border: '1px solid rgba(34,197,94,0.25)' },
    title: '3-Panel Workspace',
    description:
      'Transaction data, AML analysis, and the editable SAR draft — all visible simultaneously. No tab-switching.',
  },
  {
    icon: <Webhook size={22} color="#a855f7" />,
    circle: { background: 'rgba(168,85,247,0.12)', border: '1px solid rgba(168,85,247,0.25)' },
    title: 'HMAC-Signed Delivery',
    description:
      'Approved SARs are PDF-rendered, signed with SHA-256, and delivered to your endpoint with retry logic.',
  },
  {
    icon: <Building2 size={22} color="#71717a" />,
    circle: { background: 'rgba(113,113,122,0.12)', border: '1px solid rgba(113,113,122,0.25)' },
    title: 'Multi-Tenant Isolation',
    description:
      "Every alert, SAR, and key is row-level isolated. No tenant can touch another's data — ever.",
  },
]

export default function FeaturesSection() {
  const sectionRef = useReveal<HTMLElement>()

  return (
    <section ref={sectionRef} style={{ background: 'var(--bg-base)', padding: '0 48px 120px' }}>
      <div className="section-header">
        <div className="reveal">
          <span className="section-tag">Capabilities</span>
        </div>
        <h2 className="section-h2 reveal">Every tool compliance teams need.</h2>
        <p className="section-sub reveal">
          Built specifically for India's PMLA framework. Nothing generic.
        </p>
      </div>

      <div className="features-grid">
        {FEATURES.map((f) => (
          <div key={f.title} className="feature-card reveal">
            <div
              style={{
                width: 48,
                height: 48,
                borderRadius: '50%',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                ...f.circle,
              }}
            >
              {f.icon}
            </div>
            <h3 style={{ fontSize: 16, fontWeight: 600, marginTop: 16 }}>{f.title}</h3>
            <p style={{ fontSize: 14, color: 'var(--text-3)', marginTop: 8, lineHeight: 1.6 }}>
              {f.description}
            </p>
          </div>
        ))}
      </div>
    </section>
  )
}
