import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Building2,
  FileText,
  Lock,
  ShieldCheck,
  Sparkles,
  Webhook,
} from 'lucide-react'
import LandingNav from './LandingNav'
import { AegisShield } from '../../components/AegisLogo'
import './Landing.css'

/* ═══════════════════════════════════════════════════════════════════
   LANDING — clean and quiet. Alabaster space, piercing emerald,
   one good product shot. Animation is limited to a hero entrance
   and a gentle fade-up as sections scroll into view.
   ═══════════════════════════════════════════════════════════════════ */

/** Adds .visible to every .reveal element the first time it scrolls into view. */
function useRevealOnScroll(rootRef: React.RefObject<HTMLElement>) {
  useEffect(() => {
    const root = rootRef.current
    if (!root) return
    const els = Array.from(root.querySelectorAll<HTMLElement>('.reveal'))
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      els.forEach((el) => el.classList.add('visible'))
      return
    }
    const obs = new IntersectionObserver(
      (entries) => {
        entries.forEach((e) => {
          if (e.isIntersecting) {
            e.target.classList.add('visible')
            obs.unobserve(e.target)
          }
        })
      },
      { threshold: 0.15 },
    )
    els.forEach((el) => obs.observe(el))
    return () => obs.disconnect()
  }, [rootRef])
}

/* ── The product shot: a quiet two-pane mock of the real app ──────── */
const MOCK_ROWS = [
  { id: 'TXN-88412', amount: '₹50,00,000', risk: 91, level: 'high', rule: 'Structuring' },
  { id: 'TXN-88409', amount: '₹9,90,000', risk: 78, level: 'med', rule: 'Velocity' },
  { id: 'TXN-88401', amount: '₹12,40,000', risk: 64, level: 'med', rule: 'Counterparty' },
  { id: 'TXN-88396', amount: '₹3,20,000', risk: 22, level: 'low', rule: 'Auto-cleared' },
]

function ProductMock() {
  return (
    <div className="mock reveal" aria-hidden="true">
      <div className="mock-bar">
        <span className="mock-dot" />
        <span className="mock-dot" />
        <span className="mock-dot" />
        <span className="mock-url">app.aegis-aml.com/queue</span>
      </div>
      <div className="mock-body">
        <div className="mock-queue">
          <div className="mock-pane-head">
            <span>Alert Queue</span>
            <span className="mock-live">
              <span className="pulse-dot" /> 3 pending
            </span>
          </div>
          {MOCK_ROWS.map((r) => (
            <div key={r.id} className="mock-row">
              <span className="mock-id">{r.id}</span>
              <span className="mock-amount">{r.amount}</span>
              <span className={`mock-risk mock-risk-${r.level}`}>{r.risk}</span>
              <span className="mock-rule">{r.rule}</span>
            </div>
          ))}
        </div>
        <div className="mock-sar">
          <div className="mock-pane-head">
            <span>SAR Draft — TXN-88412</span>
            <span className="mock-ai">Groq · 6.2s</span>
          </div>
          <div className="mock-line w-92" />
          <div className="mock-line w-100" />
          <div className="mock-line w-84" />
          <div className="mock-line w-95" />
          <div className="mock-line w-60" />
          <div className="mock-approve">Approve &amp; File →</div>
        </div>
      </div>
    </div>
  )
}

/* ── Sections ─────────────────────────────────────────────────────── */
const STEPS = [
  {
    n: '01',
    title: 'Alert arrives',
    body: 'Raw transaction JSON lands from your TMS via API or webhook. PII is tokenized before anything leaves your system.',
  },
  {
    n: '02',
    title: 'Engine analyzes',
    body: 'Eight deterministic AML typology checks score the alert; Groq drafts a full narrative SAR in seconds.',
  },
  {
    n: '03',
    title: 'Officer approves',
    body: 'Your compliance officer reviews, edits, and approves. The HMAC-signed PDF ships to your endpoint, FIU-India ready.',
  },
]

const FEATURES = [
  { icon: <ShieldCheck size={18} />, title: 'AML Typology Engine', body: '8 deterministic checks — structuring, velocity, layering, counterparty risk, and more.' },
  { icon: <Lock size={18} />, title: 'PII Tokenization Vault', body: 'Customer identifiers never leave your perimeter. Real data re-hydrates only on approval.' },
  { icon: <Sparkles size={18} />, title: 'Groq SAR Generation', body: 'A full narrative SAR in under 8 seconds, structured for FIU-India’s goAML format.' },
  { icon: <FileText size={18} />, title: '3-Panel Workspace', body: 'Transaction data, AML analysis, and the editable draft — visible simultaneously.' },
  { icon: <Webhook size={18} />, title: 'HMAC-Signed Delivery', body: 'SHA-256 signed PDFs delivered to your endpoint with retry logic.' },
  { icon: <Building2 size={18} />, title: 'Multi-Tenant Isolation', body: 'Every alert, SAR, and key is row-level isolated between tenants.' },
]

const easeOut = (t: number) => 1 - Math.pow(1 - t, 3)

function StatsBand() {
  const ref = useRef<HTMLDivElement>(null)
  const [p, setP] = useState(0)

  useEffect(() => {
    const el = ref.current
    if (!el) return
    let raf = 0
    const obs = new IntersectionObserver(
      ([entry]) => {
        if (!entry.isIntersecting) return
        obs.disconnect()
        const t0 = performance.now()
        const tick = (now: number) => {
          const t = Math.min(1, (now - t0) / 1400)
          setP(easeOut(t))
          if (t < 1) raf = requestAnimationFrame(tick)
        }
        raf = requestAnimationFrame(tick)
      },
      { threshold: 0.4 },
    )
    obs.observe(el)
    return () => {
      obs.disconnect()
      cancelAnimationFrame(raf)
    }
  }, [])

  const stats = [
    { value: `< ${Math.round(60 - 50 * p)} min`, label: 'Per SAR, end-to-end' },
    { value: `${Math.round(8 * p)}`, label: 'AML typology checks' },
    { value: 'PMLA 2002', label: 'Compliance standard' },
    { value: `${Math.round(100 * p)}%`, label: 'Audit trail coverage' },
  ]

  return (
    <section className="lc-stats">
      <div ref={ref} className="lc-stats-grid reveal">
        {stats.map((s) => (
          <div key={s.label} className="lc-stat">
            <div className="lc-stat-value">{s.value}</div>
            <div className="lc-stat-label">{s.label}</div>
          </div>
        ))}
      </div>
    </section>
  )
}

export default function Landing() {
  const rootRef = useRef<HTMLDivElement>(null)
  useRevealOnScroll(rootRef)

  return (
    <div ref={rootRef} className="landing-clean">
      <LandingNav />

      {/* ── Hero ── */}
      <header className="lc-hero">
        <span className="section-tag rise" style={{ animationDelay: '0ms' }}>
          <span className="tag-dot" />
          Aegis AML · Compliance Intelligence
        </span>
        <h1 className="lc-h1 rise" style={{ animationDelay: '90ms' }}>
          Stop chasing false positives.
          <br />
          Start filing <span className="lc-grad">intelligent SARs.</span>
        </h1>
        <p className="lc-sub rise" style={{ animationDelay: '180ms' }}>
          AI-powered SAR generation for Indian fintechs and brokers. From raw
          transaction alert to a PMLA-compliant filing in minutes, with your
          officer in the loop.
        </p>
        <div className="lc-ctas rise" style={{ animationDelay: '270ms' }}>
          <Link to="/signup" className="btn-landing btn-landing-primary">
            Request Access →
          </Link>
          <Link to="/login" className="btn-landing btn-landing-secondary">
            Sign In
          </Link>
        </div>
        <div className="lc-trust rise" style={{ animationDelay: '360ms' }}>
          PMLA 2002 <span>·</span> FIU-IND goAML <span>·</span> 8 AML typology checks
        </div>
        <ProductMock />
      </header>

      {/* ── How it works ── */}
      <section className="lc-section">
        <div className="lc-section-head reveal">
          <span className="section-tag">How It Works</span>
          <h2 className="lc-h2">Three stages. Fully automated.</h2>
        </div>
        <div className="lc-steps">
          {STEPS.map((s, i) => (
            <div key={s.n} className="lc-step reveal" style={{ transitionDelay: `${i * 70}ms` }}>
              <span className="lc-step-n">{s.n}</span>
              <h3>{s.title}</h3>
              <p>{s.body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ── Features ── */}
      <section className="lc-section lc-section-tight">
        <div className="lc-section-head reveal">
          <span className="section-tag">Capabilities</span>
          <h2 className="lc-h2">Every tool compliance teams need.</h2>
          <p className="lc-section-sub">
            Built specifically for India's PMLA framework. Nothing generic.
          </p>
        </div>
        <div className="lc-features">
          {FEATURES.map((f, i) => (
            <div key={f.title} className="lc-feature reveal" style={{ transitionDelay: `${(i % 3) * 70}ms` }}>
              <div className="lc-feature-icon">{f.icon}</div>
              <h3>{f.title}</h3>
              <p>{f.body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ── Stats ── */}
      <StatsBand />

      {/* ── CTA ── */}
      <section className="lc-section lc-cta">
        <div className="reveal">
          <h2 className="lc-h2">Automate your compliance workflow.</h2>
          <p className="lc-section-sub" style={{ maxWidth: 460, margin: '14px auto 0' }}>
            Join India's compliance-first fintechs using Aegis to cut SAR
            preparation time by 94%.
          </p>
          <div style={{ marginTop: 30 }}>
            <Link to="/signup" className="btn-landing btn-landing-primary">
              Request Access →
            </Link>
          </div>
          <div className="lc-cta-note">No commitment. Set up in under 10 minutes.</div>
        </div>
      </section>

      {/* ── Footer ── */}
      <footer className="lc-footer">
        <div className="lc-footer-brand">
          <AegisShield size={18} />
          <span className="font-logo">
            AEGIS <span style={{ color: 'var(--accent)' }}>AML</span>
          </span>
          <span className="lc-footer-copy">© 2026 Aegis AML. All rights reserved.</span>
        </div>
        <div className="lc-footer-links">
          <a href="#privacy">Privacy</a>
          <a href="#terms">Terms</a>
          <a href="mailto:support@aegis-aml.com">Contact</a>
        </div>
      </footer>
    </div>
  )
}
