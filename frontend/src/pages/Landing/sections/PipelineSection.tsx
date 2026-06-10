import { useEffect, useRef, useState } from 'react'
import { FileCheck, Inbox } from 'lucide-react'
import { AegisShield } from '../../../components/AegisLogo'
import { useReveal } from '../../../hooks/useReveal'
import { cls } from '../../../utils/format'

function Arrow() {
  return (
    <div className="pipeline-arrow" aria-hidden="true">
      <div className="pipeline-arrow-line" />
      <div className="pipeline-arrow-head" />
    </div>
  )
}

export default function PipelineSection() {
  const headerRef = useReveal<HTMLDivElement>()
  const rowRef = useRef<HTMLDivElement>(null)
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    const el = rowRef.current
    if (!el) return
    const obs = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setVisible(true)
          obs.disconnect()
        }
      },
      { threshold: 0.2 },
    )
    obs.observe(el)
    return () => obs.disconnect()
  }, [])

  return (
    <section style={{ background: 'var(--bg-base)', padding: '120px 48px' }}>
      <div ref={headerRef} className="section-header">
        <div className="reveal">
          <span className="section-tag">How It Works</span>
        </div>
        <h2 className="section-h2 reveal">Three stages. Fully automated.</h2>
        <p className="section-sub reveal">
          From raw transaction data to a PMLA-compliant SAR, with your officer in the loop.
        </p>
      </div>

      <div ref={rowRef} className={cls('pipeline-row', visible && 'is-visible')}>
        {/* Card 1 — Alert In */}
        <div className="pipeline-card">
          <div
            style={{
              width: 56,
              height: 56,
              borderRadius: '50%',
              background: 'rgba(99,102,241,0.12)',
              border: '1px solid rgba(99,102,241,0.3)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <Inbox size={26} color="var(--accent-text)" />
          </div>
          <h3 style={{ fontSize: 16, fontWeight: 600 }}>Transaction Alert</h3>
          <p style={{ fontSize: 13, color: 'var(--text-3)', lineHeight: 1.6 }}>
            Raw JSON from your TMS, via API or webhook.
          </p>
          <span className="pipeline-pill">API · Webhook</span>
        </div>

        <Arrow />

        {/* Card 2 — AI Engine */}
        <div className="pipeline-card engine" style={{ paddingTop: 36, paddingBottom: 36 }}>
          <div style={{ animation: 'subtleFloat 4s ease-in-out infinite' }}>
            <AegisShield size={36} />
          </div>
          <h3 style={{ fontSize: 16, fontWeight: 600 }}>Aegis Engine</h3>
          <p style={{ fontSize: 13, color: 'var(--text-3)', lineHeight: 1.6 }}>
            PII masking, 8 AML checks, Groq SAR draft generation.
          </p>
          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', justifyContent: 'center' }}>
            <span className="pipeline-pill">PII Vault</span>
            <span className="pipeline-pill">AML Rules</span>
            <span className="pipeline-pill">Groq LLM</span>
          </div>
        </div>

        <Arrow />

        {/* Card 3 — SAR Out */}
        <div className="pipeline-card">
          <div
            style={{
              width: 56,
              height: 56,
              borderRadius: '50%',
              background: 'rgba(34,197,94,0.12)',
              border: '1px solid rgba(34,197,94,0.3)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <FileCheck size={26} color="var(--success)" />
          </div>
          <h3 style={{ fontSize: 16, fontWeight: 600 }}>Approved SAR</h3>
          <p style={{ fontSize: 13, color: 'var(--text-3)', lineHeight: 1.6 }}>
            HMAC-signed PDF delivered to your endpoint, FIU-India ready.
          </p>
          <span
            className="pipeline-pill"
            style={{ background: 'var(--success-subtle)', color: 'var(--success)' }}
          >
            PMLA Compliant
          </span>
        </div>
      </div>
    </section>
  )
}
