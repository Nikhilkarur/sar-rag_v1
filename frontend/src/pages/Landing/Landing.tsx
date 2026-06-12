import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Activity,
  ArrowRight,
  BarChart3,
  Bot,
  Building2,
  Check,
  Command,
  EyeOff,
  FileText,
  GitBranch,
  KeyRound,
  LayoutDashboard,
  Lock,
  Plus,
  RefreshCcw,
  ScrollText,
  ShieldCheck,
  Sparkles,
  Webhook,
  Zap,
} from 'lucide-react'
import LandingNav from './LandingNav'
import DotMesh from '../../components/DotMesh'
import { AegisShield } from '../../components/AegisLogo'
import { cls } from '../../utils/format'
import './Landing.css'

/* ═══════════════════════════════════════════════════════════════════
   LANDING — Attio-school minimalism, full-length.
   Pure white, near-black ink, gray hairlines; color lives inside the
   product mocks (Attio-style) and a drifting mathematical dot mesh
   behind the hero, risk-engine canvas, developer band and closing CTA.
   Every product claim on this page maps to a real backend behavior:
   8 typology checks, risk ≥ 75 → AI SAR / else auto-clear,
   PII token map, X-Aegis-Signature HMAC webhooks, POST /api/v1/ingest.
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

/* ═══════════════════════════════════════════════════════════════════
   TABBED PRODUCT SHOWCASE — SAR drafts / Review queue / Risk engine /
   Usage & reports. Mirrors the real portal routes.
   ═══════════════════════════════════════════════════════════════════ */

const MOCK_ROWS = [
  { id: 'TXN-88412', amount: '₹50,00,000', risk: 91, level: 'high', rule: 'Structuring' },
  { id: 'TXN-88409', amount: '₹9,90,000', risk: 78, level: 'med', rule: 'Velocity' },
  { id: 'TXN-88401', amount: '₹12,40,000', risk: 64, level: 'med', rule: 'Counterparty Risk' },
  { id: 'TXN-88396', amount: '₹3,20,000', risk: 22, level: 'low', rule: 'Auto-cleared' },
  { id: 'TXN-88390', amount: '₹7,75,000', risk: 58, level: 'med', rule: 'Rapid Movement' },
]

/* Mirrors the real portal sidebar: Workspace + Settings sections */
const SIDE_ITEMS = [
  { icon: <LayoutDashboard size={13} />, label: 'Dashboard', active: false },
  { icon: <Activity size={13} />, label: 'Review Queue', active: true, badge: 3 },
  { icon: <BarChart3 size={13} />, label: 'Usage', active: false },
]
const SIDE_SETTINGS = [
  { icon: <Lock size={13} />, label: 'Credentials' },
  { icon: <Webhook size={13} />, label: 'Webhook' },
  { icon: <FileText size={13} />, label: 'Ingestion Schema' },
  { icon: <Sparkles size={13} />, label: 'LLM Config' },
]

function MockSidebar() {
  return (
    <div className="ask-side">
      <div className="ask-side-ws">
        <span className="ask-side-logo">
          <AegisShield size={14} />
        </span>
        TestFintech
      </div>
      <div className="ask-side-search">
        <Command size={11} />
        Quick Actions
        <span className="ask-side-kbd">⌘K</span>
      </div>
      {SIDE_ITEMS.map((it) => (
        <div key={it.label} className={cls('ask-side-item', it.active && 'active')}>
          {it.icon}
          {it.label}
          {it.badge && <span className="ask-side-badge">{it.badge}</span>}
        </div>
      ))}
      <div className="ask-side-fav">Settings</div>
      {SIDE_SETTINGS.map((it) => (
        <div key={it.label} className="ask-side-item">
          {it.icon}
          {it.label}
        </div>
      ))}
    </div>
  )
}

function SarDraftMock() {
  return (
    <div className="ask-mock">
      <MockSidebar />
      <div className="ask-doc">
        <div className="ask-doc-title">
          SAR Draft — TXN-88412 <span className="mock-ai">AI draft · 6.2s</span>
        </div>
        <div className="ask-doc-h">Key risk signals:</div>
        <div className="ask-doc-p">
          <b>1. Structured deposits</b> — 14 cash deposits just under ₹10,00,000 across six days
        </div>
        <div className="ask-doc-p">
          <b>2. Velocity spike</b> — account turnover at 11× its 90-day baseline
        </div>
        <div className="ask-doc-p">
          <b>3. Round-number transfers</b> — six transfers of exactly ₹5,00,000 within 48 hours
        </div>
        <div className="ask-doc-p">
          <b>4. Counterparty risk</b> — two beneficiaries match internal watchlists
        </div>
        <div className="ask-doc-h">Critical next steps:</div>
        <div className="ask-doc-p">
          <b>1. Review the drafted narrative</b> — grounds of suspicion cite PMLA 2002 §12
          record-keeping duties
        </div>
        <div className="ask-doc-p ask-doc-sub">
          a. Confirm the customer profile matches the declared business activity
        </div>
        <div className="ask-doc-p ask-doc-sub">
          b. Verify tokenized identifiers re-hydrate correctly before filing
        </div>
        <div className="ask-doc-p">
          <b>2. Approve &amp; file</b> — delivery ships to your endpoint signed with
          X-Aegis-Signature
          <span className="ask-caret" />
        </div>
      </div>
    </div>
  )
}

function QueueMock() {
  return (
    <div className="queue-mock">
      <div className="mock-pane-head">
        <span>Review Queue</span>
        <span className="mock-live">
          <span className="pulse-dot" /> 3 pending review
        </span>
      </div>
      <div className="mock-row mock-row-head">
        <span>Alert</span>
        <span>Amount</span>
        <span style={{ textAlign: 'center' }}>Risk</span>
        <span style={{ textAlign: 'right' }}>Typology</span>
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
  )
}

function RiskEngineMock() {
  return (
    <div className="flow-mock">
      <div className="flow-mock-node">
        <span className="agent-badge">
          <Check size={11} /> Triggered
        </span>
        <div className="agent-node-head">
          <span className="agent-node-icon icon-blue">
            <Zap size={11} />
          </span>
          When Alert scored
          <span className="agent-tag tag-blue">Alerts</span>
        </div>
        <div className="agent-node-sub">Eight typology checks compute the risk score</div>
      </div>
      <svg className="flow-mock-wire" viewBox="0 0 40 56" aria-hidden="true">
        <path d="M20 0 V56" pathLength={1} />
      </svg>
      <div className="flow-mock-node">
        <span className="agent-badge">
          <Check size={11} /> Completed
        </span>
        <div className="agent-node-head">
          <span className="agent-node-icon icon-purple">
            <GitBranch size={11} />
          </span>
          Switch
          <span className="agent-tag tag-purple">Condition</span>
        </div>
        <div className="agent-node-sub">risk ≥ 75 → AI SAR draft · below → auto-clear</div>
      </div>
    </div>
  )
}

/* ── Colorful usage chart (Attio "Business metrics" flavor) ───────── */
const CHART_STACKS = [
  [26, 14, 9],
  [32, 18, 10],
  [24, 16, 12],
  [38, 20, 12],
  [30, 22, 14],
  [44, 24, 14],
  [52, 30, 18],
]
const CHART_MONTHS = ['Dec', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun']

const DONUT_SEGS = [
  { c: 'var(--c-pink)', v: 38, label: 'Structuring' },
  { c: 'var(--c-blue)', v: 27, label: 'Velocity' },
  { c: 'var(--c-purple)', v: 20, label: 'Counterparty' },
  { c: 'var(--c-amber)', v: 15, label: 'Other' },
]

function Donut() {
  const R = 38
  const C = 2 * Math.PI * R
  let acc = 0
  return (
    <svg viewBox="0 0 100 100" className="donut" aria-hidden="true">
      {DONUT_SEGS.map((s) => {
        const off = acc
        acc += s.v
        return (
          <circle
            key={s.label}
            cx="50"
            cy="50"
            r={R}
            fill="none"
            stroke={s.c}
            strokeWidth="13"
            strokeDasharray={`${(s.v / 100) * C - 1.5} ${C}`}
            strokeDashoffset={-(off / 100) * C}
            transform="rotate(-90 50 50)"
          />
        )
      })}
      <text x="50" y="47" textAnchor="middle" className="donut-num">
        412
      </text>
      <text x="50" y="60" textAnchor="middle" className="donut-lbl">
        SARs filed
      </text>
    </svg>
  )
}

function UsageChart({ withTip = false }: { withTip?: boolean }) {
  return (
    <div className="chart-card">
      <div className="chart-head">
        <span>Usage &amp; reports</span>
        <span className="chart-legend">
          <i style={{ background: 'var(--c-pink)' }} /> Filed
          <i style={{ background: 'var(--c-blue)' }} /> Drafted
          <i style={{ background: 'var(--c-purple)' }} /> Auto-cleared
        </span>
      </div>
      <div className="chart-body">
        <div className="chart-bars">
          {CHART_STACKS.map((g, i) => (
            <div key={i} className="chart-col" style={{ '--d': `${i * 70}ms` } as React.CSSProperties}>
              <div className="chart-stack">
                <span style={{ height: `${g[2]}%`, background: 'var(--c-purple-soft)' }} />
                <span style={{ height: `${g[1]}%`, background: 'var(--c-blue-soft)' }} />
                <span style={{ height: `${g[0]}%`, background: 'var(--c-pink)' }} />
              </div>
              <span className="chart-month">{CHART_MONTHS[i]}</span>
            </div>
          ))}
        </div>
        <div className="chart-side">
          <Donut />
          <div className="chart-side-legend">
            {DONUT_SEGS.map((s) => (
              <div key={s.label} className="chart-side-row">
                <i style={{ background: s.c }} />
                {s.label}
                <b>{s.v}%</b>
              </div>
            ))}
          </div>
        </div>
      </div>
      {withTip && (
        <div className="chart-tip">
          <div className="chart-tip-head">
            SARs filed <span className="chart-tip-up">↗ +63%</span>
          </div>
          <div className="chart-tip-row">
            <span>May 2026</span>
            <b>38 filings</b>
          </div>
          <div className="chart-tip-row">
            <span>Jun 2026</span>
            <b>62 filings</b>
          </div>
        </div>
      )}
    </div>
  )
}

function UsageMock() {
  return (
    <div className="report-mock">
      <div className="report-chart">
        <UsageChart />
      </div>
      <div className="report-tiles">
        <div className="report-tile">
          <div className="report-tile-v">38 min</div>
          <div className="report-tile-l">Median time to file</div>
        </div>
        <div className="report-tile">
          <div className="report-tile-v">64%</div>
          <div className="report-tile-l">Alerts auto-cleared</div>
        </div>
        <div className="report-tile">
          <div className="report-tile-v">100%</div>
          <div className="report-tile-l">Deliveries signed</div>
        </div>
      </div>
    </div>
  )
}

const TABS = [
  { label: 'SAR drafts', url: 'queue/TXN-88412', view: <SarDraftMock /> },
  { label: 'Review queue', url: 'queue', view: <QueueMock /> },
  { label: 'Risk engine', url: 'dashboard', view: <RiskEngineMock /> },
  { label: 'Usage & reports', url: 'usage', view: <UsageMock /> },
]

function ShowcaseTabs() {
  const [tab, setTab] = useState(0)
  const [pinned, setPinned] = useState(false)

  useEffect(() => {
    if (pinned) return
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return
    const id = setInterval(() => {
      if (!document.hidden) setTab((t) => (t + 1) % TABS.length)
    }, 5200)
    return () => clearInterval(id)
  }, [pinned])

  return (
    <div className="showcase reveal">
      <div className={cls('showcase-tabs', !pinned && 'auto')} role="tablist">
        {TABS.map((t, i) => (
          <button
            key={t.label}
            role="tab"
            aria-selected={i === tab}
            className={cls('showcase-tab', i === tab && 'active')}
            onClick={() => {
              setPinned(true)
              setTab(i)
            }}
          >
            {t.label}
          </button>
        ))}
      </div>
      <div className="mock" aria-hidden="true">
        <div className="mock-bar">
          <span className="mock-dot" />
          <span className="mock-dot" />
          <span className="mock-dot" />
          <span className="mock-url">app.aegis-aml.com/{TABS[tab].url}</span>
        </div>
        <div className="mock-stage" key={tab}>
          {TABS[tab].view}
        </div>
      </div>
    </div>
  )
}

/* ═══════════════════════════════════════════════════════════════════
   CUSTOMERS — hairline logo grid (fictional design partners).
   ═══════════════════════════════════════════════════════════════════ */

const LOGOS = [
  { name: 'Novapay', cls: 'logo-sans' },
  { name: 'RupeeFlow', cls: 'logo-serif' },
  { name: 'FinEdge', cls: 'logo-mono' },
  { name: 'Zentra Capital', cls: 'logo-light' },
  { name: 'PayOrbit', cls: 'logo-serif' },
  { name: 'LedgerLine', cls: 'logo-sans' },
  { name: 'Brokr', cls: 'logo-mono' },
  { name: 'Quantis', cls: 'logo-light' },
]

function LogoBand() {
  return (
    <section className="lc-section" id="customers">
      <div className="lc-section-head centered reveal">
        <h2 className="lc-h2" style={{ maxWidth: 640, margin: '0 auto' }}>
          Aegis is trusted by India's compliance-first fintechs, brokers and payment platforms.
        </h2>
      </div>
      <div className="logo-grid reveal reveal-list">
        {LOGOS.map((l, i) => (
          <div key={l.name} className="logo-cell reveal-item" style={{ '--d': `${i * 60}ms` } as React.CSSProperties}>
            <span className={l.cls}>{l.name}</span>
          </div>
        ))}
      </div>
    </section>
  )
}

/* ═══════════════════════════════════════════════════════════════════
   SCROLL QUOTE — sticky section; words ink in as you scroll through.
   ═══════════════════════════════════════════════════════════════════ */

const QUOTE =
  'When I first opened Aegis, I instantly got the feeling this was the next generation of compliance.'

function ScrollQuote() {
  const wrapRef = useRef<HTMLDivElement>(null)
  const [lit, setLit] = useState(0)
  const words = QUOTE.split(' ')

  useEffect(() => {
    const el = wrapRef.current
    if (!el) return
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      setLit(words.length)
      return
    }
    let raf = 0
    const onScroll = () => {
      cancelAnimationFrame(raf)
      raf = requestAnimationFrame(() => {
        const rect = el.getBoundingClientRect()
        const span = rect.height - window.innerHeight
        if (span <= 0) return
        const p = Math.min(1, Math.max(0, -rect.top / span))
        setLit(Math.round(p * words.length))
      })
    }
    onScroll()
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => {
      window.removeEventListener('scroll', onScroll)
      cancelAnimationFrame(raf)
    }
  }, [words.length])

  return (
    <section className="lc-quote-wrap" ref={wrapRef}>
      <div className="lc-quote-sticky">
        <blockquote className="lc-quote">
          {words.map((w, i) => (
            <span key={i} className={cls('lc-quote-w', i < lit && 'lit')}>
              {i === 0 ? `“${w}` : i === words.length - 1 ? `${w}”` : w}{' '}
            </span>
          ))}
        </blockquote>
        <div className={cls('lc-quote-attr', lit >= words.length - 2 && 'lit')}>
          <div className="lc-quote-name">Priya Raghavan</div>
          <div className="lc-quote-role">Chief Compliance Officer · Novapay</div>
        </div>
      </div>
    </section>
  )
}

/* ═══════════════════════════════════════════════════════════════════
   AGENTS — animated workflow canvas + agent chip stack.
   Mirrors the real pipeline: ingest → 8 checks → risk ≥ 75 routes to
   an AI SAR, below auto-clears as COMPLETED_CLEAN.
   ═══════════════════════════════════════════════════════════════════ */

const AGENT_CHIPS = [
  { label: 'Re-screen dormant accounts', dim: 0.3, ic: 'icon-blue' },
  { label: 'Velocity rule routing', dim: 0.45, ic: 'icon-amber' },
  { label: 'Counterparty hand-off', dim: 0.7, ic: 'icon-purple' },
  { label: 'New SAR draft pipeline', dim: 1, hot: true, ic: 'icon-green' },
  { label: 'Round-number screening', dim: 0.7, ic: 'icon-pink' },
  { label: 'Monitor review backlog', dim: 0.45, ic: 'icon-blue' },
  { label: 'Flag rapid movement', dim: 0.3, ic: 'icon-purple' },
]

function AgentsSection() {
  return (
    <section className="lc-agents" id="agents">
      <div className="lc-agents-inner">
        <div className="lc-agents-copy reveal">
          <h2 className="lc-h2">
            A risk engine at
            <br />
            your command.
          </h2>
          <p className="lc-section-sub">
            It's your rulebook. Eight deterministic typology checks score every alert; anything at
            risk 75 or above routes to an AI-drafted SAR, the rest auto-clears with a clean audit
            entry.
          </p>
          <a href="#how-it-works" className="lc-agents-link">
            See how it works <ArrowRight size={14} />
          </a>
        </div>

        <div className="agents-stage reveal">
          <DotMesh />
          <div className="agents-canvas" aria-hidden="true">
            <svg className="agents-wires" viewBox="0 0 560 640" preserveAspectRatio="none">
              <path className="wire wire-1" pathLength={1} d="M280 150 V250" />
              <path
                className="wire wire-2"
                pathLength={1}
                d="M280 364 V404 C280 428 170 420 170 470 V480"
              />
              <path
                className="wire wire-3 wire-idle"
                pathLength={1}
                d="M280 364 V404 C280 428 396 420 396 470 V480"
              />
            </svg>

            <span className="agent-float agent-float-trigger">
              <span className="agent-float-icon">
                <Zap size={10} />
              </span>
              Trigger
            </span>
            <span className="agent-badge agents-b1">
              <Check size={11} /> Triggered
            </span>
            <div className="agent-node agents-n1">
              <div className="agent-node-head">
                <span className="agent-node-icon icon-blue">
                  <Zap size={11} />
                </span>
                When Alert created
                <span className="agent-tag tag-blue">Alerts</span>
              </div>
              <div className="agent-node-sub">Eight typology checks compute the risk score</div>
            </div>

            <span className="agent-badge agents-b2">
              <Check size={11} /> Completed
            </span>
            <div className="agent-node agents-n2">
              <div className="agent-node-head">
                <span className="agent-node-icon icon-purple">
                  <GitBranch size={11} />
                </span>
                Switch
                <span className="agent-tag tag-purple">Condition</span>
              </div>
              <div className="agent-node-sub">risk ≥ 75 → escalate · below → auto-clear</div>
            </div>

            <span className="agent-branch agents-br1">Escalate</span>
            <span className="agent-branch agents-br2 idle">Auto-clear</span>

            <span className="agent-badge agents-b3">
              <Check size={11} /> Completed
            </span>
            <div className="agent-node agents-n3">
              <div className="agent-node-head">
                <span className="agent-node-icon icon-green">
                  <Sparkles size={11} />
                </span>
                Draft SAR
                <span className="agent-tag tag-green">AI</span>
              </div>
              <div className="agent-node-sub">Narrative grounded in typology evidence</div>
            </div>

            <div className="agent-node agents-n4 idle">
              <div className="agent-node-head">
                <span className="agent-node-icon">
                  <Check size={11} />
                </span>
                Log &amp; close
                <span className="agent-tag">Audit</span>
              </div>
              <div className="agent-node-sub">Closed as COMPLETED_CLEAN</div>
            </div>
          </div>

          <div className="agents-chips" aria-hidden="true">
            {AGENT_CHIPS.map((c, i) => (
              <div
                key={c.label}
                className={cls('agent-chip', c.hot && 'hot')}
                style={
                  {
                    '--dim': c.dim,
                    transitionDelay: `${260 + i * 70}ms`,
                  } as React.CSSProperties
                }
              >
                <span className={cls('agent-chip-icon', c.ic)}>
                  <Bot size={12} />
                </span>
                {c.label}
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}

/* ═══════════════════════════════════════════════════════════════════
   SPLIT FEATURE BLOCKS — workspace + reporting.
   ═══════════════════════════════════════════════════════════════════ */

function WorkspaceMock() {
  return (
    <div className="ws-mock reveal" aria-hidden="true">
      <div className="ws-record">
        <div className="ws-record-head">TXN-88412</div>
        <div className="ws-attr">
          <span>Amount</span>
          <b>₹50,00,000</b>
        </div>
        <div className="ws-attr">
          <span>Risk score</span>
          <b className="mock-risk mock-risk-high" style={{ padding: '2px 8px' }}>
            91
          </b>
        </div>
        <div className="ws-attr">
          <span>Status</span>
          <b className="ws-status">PENDING_REVIEW</b>
        </div>
        <div className="ws-record-sub">Rule matches</div>
        <div className="ws-rules">
          <span className="ws-rule rule-pink">Structuring · 0.92</span>
          <span className="ws-rule rule-blue">Velocity · 0.81</span>
          <span className="ws-rule rule-purple">Counterparty · 0.64</span>
        </div>
      </div>
      <div className="ws-doc">
        <div className="ws-doc-head">
          SAR Narrative <span className="mock-ai">editable</span>
        </div>
        {['w-92', 'w-100', 'w-84', 'w-95', 'w-60'].map((w, i) => (
          <div key={w} className={cls('mock-line reveal-item', w)} style={{ '--d': `${250 + i * 120}ms` } as React.CSSProperties} />
        ))}
        <div className="ws-approve reveal-item" style={{ '--d': '900ms' } as React.CSSProperties}>
          Approve &amp; file →
        </div>
      </div>
    </div>
  )
}

function SplitBlocks() {
  return (
    <>
      <section className="lc-section" id="workspace">
        <div className="lc-split">
          <div className="lc-split-copy reveal">
            <span className="lc-eyebrow">SAR Workspace</span>
            <h2 className="lc-h2">Review everything on one screen.</h2>
            <p className="lc-section-sub">
              Transaction record, typology evidence, and the editable AI draft — side by side.
              Approve, and the filing leaves your hands signed.
            </p>
            <ul className="lc-checks">
              <li>
                <Check size={14} /> Evidence rows cite each triggered rule with confidence
              </li>
              <li>
                <Check size={14} /> Tokenized PII re-hydrates only at approval time
              </li>
              <li>
                <Check size={14} /> One click files and delivers to your endpoint
              </li>
            </ul>
          </div>
          <WorkspaceMock />
        </div>
      </section>

      <section className="lc-section">
        <div className="lc-split lc-split-rev">
          <div className="lc-split-copy reveal">
            <span className="lc-eyebrow">Usage &amp; reports</span>
            <h2 className="lc-h2">Reporting your auditor will love.</h2>
            <p className="lc-section-sub">
              Filings, drafts, auto-clears and LLM usage — tracked per tenant, exportable, and
              always reconciled against the webhook event log.
            </p>
            <ul className="lc-checks">
              <li>
                <Check size={14} /> Per-month filing and auto-clear breakdowns
              </li>
              <li>
                <Check size={14} /> Typology mix across every scored alert
              </li>
              <li>
                <Check size={14} /> Delivery log with HMAC verification status
              </li>
            </ul>
          </div>
          <div className="lc-split-chart reveal">
            <UsageChart withTip />
          </div>
        </div>
      </section>
    </>
  )
}

/* ═══════════════════════════════════════════════════════════════════
   DEVELOPERS — dark band with the real API surface.
   ═══════════════════════════════════════════════════════════════════ */

function DeveloperSection() {
  return (
    <section className="lc-dev" id="developers">
      <DotMesh dark />
      <div className="lc-dev-inner">
        <div className="lc-dev-copy reveal">
          <span className="lc-eyebrow lc-eyebrow-dark">Developers</span>
          <h2 className="lc-h2 lc-h2-dark">API-first. Integrated in an afternoon.</h2>
          <p className="lc-dev-sub">
            One idempotent ingestion endpoint, schema presets for common TMS formats, rotating API
            keys, and an HMAC-signed webhook back when a SAR is approved.
          </p>
          <div className="lc-dev-chips">
            {['Idempotent ingestion', 'Schema presets', 'Key rotation', 'Webhook event log'].map(
              (chip, i) => (
                <span key={chip} className="reveal-item" style={{ '--d': `${200 + i * 90}ms` } as React.CSSProperties}>
                  {chip}
                </span>
              ),
            )}
          </div>
        </div>
        <div className="lc-dev-codes reveal">
          <div className="code-card">
            <div className="code-bar">
              <span className="code-dot" />
              <span className="code-dot" />
              <span className="code-dot" />
              POST /api/v1/ingest
            </div>
            <pre className="code-pre">
              <span className="tk-c"># Send a raw transaction alert</span>
              {'\n'}
              <span className="tk-y">curl</span> -X POST https://api.aegis-aml.com
              <span className="tk-b">/api/v1/ingest/</span> \{'\n'}
              {'  '}-H <span className="tk-g">"X-API-Key: ak_live_••••••••"</span> \{'\n'}
              {'  '}-H <span className="tk-g">"X-Tenant-ID: TEN-0001"</span> \{'\n'}
              {'  '}-d <span className="tk-g">{`'{`}</span>
              {'\n'}
              {'      '}
              <span className="tk-p">"transaction_id"</span>:{' '}
              <span className="tk-g">"TXN-88412"</span>,{'\n'}
              {'      '}
              <span className="tk-p">"amount"</span>: <span className="tk-b">5000000</span>,{'\n'}
              {'      '}
              <span className="tk-p">"transaction_type"</span>:{' '}
              <span className="tk-g">"CASH_DEPOSIT"</span>
              {'\n'}
              {'    '}
              <span className="tk-g">{`}'`}</span>
              {'\n\n'}
              <span className="tk-c">→ 200</span> {'{'} <span className="tk-p">"risk_score"</span>:{' '}
              <span className="tk-b">91</span>,{'\n'}
              {'        '}
              <span className="tk-p">"message"</span>:{' '}
              <span className="tk-g">"SAR generation triggered."</span> {'}'}
            </pre>
          </div>
          <div className="code-card">
            <div className="code-bar">
              <span className="code-dot" />
              <span className="code-dot" />
              <span className="code-dot" />
              your-endpoint — webhook receiver
            </div>
            <pre className="code-pre">
              <span className="tk-c"># Every delivery is signed</span>
              {'\n'}
              <span className="tk-p">X-Aegis-Event</span>:{' '}
              <span className="tk-g">sar.approved</span>
              {'\n'}
              <span className="tk-p">X-Aegis-Signature</span>:{' '}
              <span className="tk-g">sha256=9f2a1c…</span>
              {'\n\n'}
              <span className="tk-y">expected</span> = hmac.new(secret, body,{' '}
              <span className="tk-b">sha256</span>).hexdigest(){'\n'}
              <span className="tk-y">assert</span> hmac.compare_digest({'\n'}
              {'  '}signature, <span className="tk-g">f"sha256={'{'}expected{'}'}"</span>){' '}
              <span className="tk-c"># ✓ verified</span>
            </pre>
          </div>
        </div>
      </div>
    </section>
  )
}

/* ═══════════════════════════════════════════════════════════════════
   STATIC SECTIONS
   ═══════════════════════════════════════════════════════════════════ */

const STEPS = [
  {
    n: '01',
    title: 'Alert arrives',
    body: 'Raw transaction JSON lands from your TMS via the ingestion API. PII is tokenized into a vault map before anything else happens — duplicates are rejected by idempotency key.',
  },
  {
    n: '02',
    title: 'Engine analyzes',
    body: 'Eight deterministic AML typology checks score the alert. Risk 75 and above routes to the AI engine for a full narrative draft; everything below auto-clears with a clean audit entry.',
  },
  {
    n: '03',
    title: 'Officer approves',
    body: 'Your compliance officer reviews and edits in the split-screen workspace. On approval, the SAR is delivered to your endpoint as an HMAC-signed webhook, FIU-India ready.',
  },
]

const FEATURES = [
  { icon: <ShieldCheck size={16} />, ico: 'ico-green', title: 'AML Typology Engine', body: '8 deterministic checks — structuring, velocity, rapid movement, dormant activation, counterparty risk, and more.' },
  { icon: <Lock size={16} />, ico: 'ico-blue', title: 'PII Tokenization Vault', body: 'Identifiers are tokenized at ingestion and encrypted at rest. Real data re-hydrates only on approval.' },
  { icon: <Sparkles size={16} />, ico: 'ico-purple', title: 'AI SAR Generation', body: "A full narrative SAR in seconds, grounded in rule evidence and structured for FIU-India's goAML format." },
  { icon: <FileText size={16} />, ico: 'ico-amber', title: 'Split-Screen Workspace', body: 'Transaction data, AML analysis, and the editable draft — visible simultaneously.' },
  { icon: <Webhook size={16} />, ico: 'ico-pink', title: 'HMAC-Signed Delivery', body: 'Approved SARs reach your endpoint with an X-Aegis-Signature header and a full delivery event log.' },
  { icon: <Building2 size={16} />, ico: 'ico-blue', title: 'Multi-Tenant Isolation', body: 'Every alert, SAR, key, and webhook secret is row-level isolated between tenants.' },
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
    { value: `${Math.round(100 * p)}%`, label: 'Deliveries HMAC-signed' },
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

/* ── Testimonials (fictional design partners) ─────────────────────── */
const TESTIMONIALS = [
  {
    quote:
      'We tested every compliance tool we could find. None balanced automation with officer control the way Aegis does.',
    name: 'Arjun Mehta',
    role: 'Head of Risk · RupeeFlow',
    initials: 'AM',
    av: 'av-blue',
  },
  {
    quote: 'Aegis feels like magic.',
    name: 'Nikhil Rao',
    role: 'Partner · Zentra Capital',
    initials: 'NR',
    av: 'av-purple',
  },
  {
    quote:
      'Our FIU-IND filings went from a quarterly fire drill to a checkbox. The audit trail alone is worth it.',
    name: "Sara D'Souza",
    role: 'Compliance Lead · FinEdge',
    initials: 'SD',
    av: 'av-pink',
  },
]

function Testimonials() {
  return (
    <section className="lc-section">
      <div className="lc-testis reveal reveal-list">
        {TESTIMONIALS.map((t, i) => (
          <div key={t.name} className="lc-testi reveal-item" style={{ '--d': `${i * 110}ms` } as React.CSSProperties}>
            <p className="lc-testi-quote">“{t.quote}”</p>
            <div className="lc-testi-meta">
              <span className={cls('lc-testi-av', t.av)}>{t.initials}</span>
              <div>
                <div className="lc-testi-name">{t.name}</div>
                <div className="lc-testi-role">{t.role}</div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </section>
  )
}

/* ── Security — vault flow + guarantees (all real backend behavior) ── */
const SEC_TOKENS = [
  { field: 'pan', raw: '"ABCDE1234F"', tok: 'tok_pan_8f2a', cls: 'rule-blue' },
  { field: 'name', raw: '"R. Sharma"', tok: 'tok_name_4c19', cls: 'rule-purple' },
  { field: 'account', raw: '"50100228841"', tok: 'tok_acct_2e77', cls: 'rule-pink' },
]

const SEC_TILES = [
  { icon: <KeyRound size={15} />, ico: 'ico-blue', title: 'Rotating API keys', body: 'Rotate keys from the Credentials page without downtime. Old keys die instantly.' },
  { icon: <RefreshCcw size={15} />, ico: 'ico-green', title: 'Refresh-token rotation', body: 'Sessions rotate their refresh token on every use; a replayed token revokes the session.' },
  { icon: <ScrollText size={15} />, ico: 'ico-amber', title: 'Tenant-scoped event log', body: 'Every transition — scored, drafted, approved, delivered — lands in the webhook event log.' },
  { icon: <EyeOff size={15} />, ico: 'ico-pink', title: 'The LLM never sees PII', body: 'The model receives tokens, never raw identifiers. Re-hydration happens inside your tenant.' },
]

function SecuritySection() {
  return (
    <section className="lc-section" id="security">
      <div className="lc-split">
        <div className="lc-split-copy reveal">
          <span className="lc-eyebrow">Security</span>
          <h2 className="lc-h2">PII goes in. Tokens come out.</h2>
          <p className="lc-section-sub">
            Identifiers are tokenized the moment an alert lands and encrypted at rest. Everything
            downstream — rules, scores, drafts, reviews — runs on tokens until an officer approves.
          </p>
          <ul className="lc-checks">
            <li>
              <Check size={14} /> Vault map encrypted at rest, isolated per tenant
            </li>
            <li>
              <Check size={14} /> Re-hydration happens only at approval time
            </li>
            <li>
              <Check size={14} /> Duplicate submissions rejected by idempotency key
            </li>
          </ul>
        </div>
        <div className="sec-vault reveal" aria-hidden="true">
          <div className="sec-vault-head">
            <Lock size={13} /> PII Tokenization Vault
            <span className="mock-ai">encrypted at rest</span>
          </div>
          {SEC_TOKENS.map((t, i) => (
            <div key={t.tok} className="sec-row reveal-item" style={{ '--d': `${220 + i * 160}ms` } as React.CSSProperties}>
              <span className="sec-raw">
                <b>"{t.field}"</b>: {t.raw}
              </span>
              <span className="sec-arrow">→</span>
              <span className={cls('sec-tok', t.cls)}>{t.tok}</span>
            </div>
          ))}
          <div className="sec-vault-foot reveal-item" style={{ '--d': '760ms' } as React.CSSProperties}>
            <span className="pulse-dot" /> vault map sealed · re-hydrates only at approval
          </div>
        </div>
      </div>
      <div className="sec-tiles reveal reveal-list">
        {SEC_TILES.map((t, i) => (
          <div key={t.title} className="sec-tile reveal-item" style={{ '--d': `${i * 90}ms` } as React.CSSProperties}>
            <div className={cls('lc-feature-icon', t.ico)}>{t.icon}</div>
            <h3>{t.title}</h3>
            <p>{t.body}</p>
          </div>
        ))}
      </div>
    </section>
  )
}

/* ── Pricing ──────────────────────────────────────────────────────── */
const PLANS = [
  {
    name: 'Pilot',
    price: '₹0',
    per: 'sandbox',
    desc: 'Simulated alerts to evaluate the engine.',
    items: ['100 alerts / month', '1 officer seat', 'All 8 typology checks', 'Community support'],
    cta: 'Request access',
    primary: false,
  },
  {
    name: 'Growth',
    price: '₹24k',
    per: 'per month',
    desc: 'For teams filing their first SARs.',
    items: ['2,000 alerts / month', '5 officer seats', 'Webhook delivery', 'Email support'],
    cta: 'Request access',
    primary: false,
  },
  {
    name: 'Scale',
    price: '₹58k',
    per: 'per month',
    desc: 'The full engine, around the clock.',
    items: ['20,000 alerts / month', 'Unlimited seats', 'AI SAR narratives', 'HMAC-signed delivery', 'Priority support'],
    cta: 'Request access',
    primary: true,
    badge: 'Most popular',
  },
  {
    name: 'Enterprise',
    price: 'Custom',
    per: 'annual',
    desc: 'Dedicated VPC and custom typologies.',
    items: ['Unlimited alerts', 'Custom rule packs', 'Dedicated infrastructure', 'SLA & onboarding'],
    cta: 'Talk to sales',
    primary: false,
    mail: true,
  },
]

function Pricing() {
  return (
    <section className="lc-section" id="pricing">
      <div className="lc-section-head centered reveal">
        <span className="lc-eyebrow">Pricing</span>
        <h2 className="lc-h2">Start free. Scale when you do.</h2>
        <p className="lc-section-sub">
          Every plan includes PII tokenization, the full audit trail, and FIU-IND goAML formatting.
        </p>
      </div>
      <div className="lc-plans reveal reveal-list">
        {PLANS.map((p, i) => (
          <div
            key={p.name}
            className={cls('lc-plan reveal-item', p.primary && 'featured')}
            style={{ '--d': `${i * 90}ms` } as React.CSSProperties}
          >
            {p.badge && <span className="lc-plan-badge">{p.badge}</span>}
            <div className="lc-plan-name">{p.name}</div>
            <div className="lc-plan-price">
              {p.price}
              <span> / {p.per}</span>
            </div>
            <div className="lc-plan-desc">{p.desc}</div>
            <ul className="lc-plan-list">
              {p.items.map((it) => (
                <li key={it}>
                  <Check size={13} />
                  {it}
                </li>
              ))}
            </ul>
            {p.mail ? (
              <a
                href="mailto:sales@aegis-aml.com"
                className="btn-landing btn-landing-secondary lc-plan-cta"
              >
                {p.cta}
              </a>
            ) : (
              <Link
                to="/signup"
                className={cls(
                  'btn-landing lc-plan-cta',
                  p.primary ? 'btn-landing-primary' : 'btn-landing-secondary',
                )}
              >
                {p.cta}
              </Link>
            )}
          </div>
        ))}
      </div>
    </section>
  )
}

/* ── FAQ ──────────────────────────────────────────────────────────── */
const FAQS = [
  {
    q: 'Does customer PII ever leave our infrastructure?',
    a: 'No. Identifiers are tokenized into a vault map at ingestion and encrypted at rest. The LLM only ever sees tokens — real values re-hydrate inside your tenant at approval time.',
  },
  {
    q: 'Which AML typologies are covered?',
    a: 'Eight deterministic checks: structuring, rapid movement, round-number transfers, dormant-account activation, high-risk transaction types, velocity, counterparty risk, and a composite risk-score threshold.',
  },
  {
    q: 'How are SAR narratives generated?',
    a: 'Alerts scoring 75 or above are routed to the LLM with the rule evidence as grounded context. The model is configurable from LLM Config, and your officer reviews and edits every draft in the split-screen workspace before anything is filed.',
  },
  {
    q: 'How do approved SARs reach our systems?',
    a: 'As webhooks signed with HMAC SHA-256 — verify the X-Aegis-Signature header against your secret. Test deliveries and the full event log live in the Webhook settings page.',
  },
  {
    q: 'Is the platform multi-tenant safe?',
    a: 'Every alert, SAR, PII map, API key, and webhook secret is row-level isolated by tenant. Keys rotate from the Credentials page without downtime, and duplicate submissions are rejected by idempotency key.',
  },
  {
    q: 'What does onboarding look like?',
    a: 'Request access, get verified by an admin, pick an ingestion schema preset, paste your keys, and send a test webhook. Most teams ingest their first alerts in under ten minutes.',
  },
]

function FAQ() {
  const [open, setOpen] = useState(0)
  return (
    <section className="lc-section" id="faq">
      <div className="lc-section-head centered reveal">
        <span className="lc-eyebrow">FAQ</span>
        <h2 className="lc-h2">Questions, answered.</h2>
      </div>
      <div className="lc-faq reveal">
        {FAQS.map((f, i) => (
          <div key={f.q} className={cls('lc-faq-item', open === i && 'open')}>
            <button className="lc-faq-q" onClick={() => setOpen(open === i ? -1 : i)}>
              {f.q}
              <span className="lc-faq-plus">
                <Plus size={16} />
              </span>
            </button>
            <div className="lc-faq-a">
              <div className="lc-faq-a-inner">{f.a}</div>
            </div>
          </div>
        ))}
      </div>
    </section>
  )
}

/* ── Footer ───────────────────────────────────────────────────────── */
const FOOTER_COLS = [
  {
    head: 'Platform',
    links: [
      ['Review Queue', '#capabilities'],
      ['SAR Workspace', '#workspace'],
      ['Risk Engine', '#agents'],
      ['Webhooks', '#developers'],
      ['Usage & Reports', '#capabilities'],
    ],
  },
  {
    head: 'Resources',
    links: [
      ['How it works', '#how-it-works'],
      ['Customers', '#customers'],
      ['Pricing', '#pricing'],
      ['API Reference', '#developers'],
      ['FAQ', '#faq'],
    ],
  },
  {
    head: 'Company',
    links: [
      ['About', '#'],
      ['Security', '#security'],
      ['Careers', '#'],
      ['Contact', 'mailto:support@aegis-aml.com'],
    ],
  },
  {
    head: 'Legal',
    links: [
      ['Privacy', '#'],
      ['Terms', '#'],
      ['DPA', '#'],
      ['PMLA 2002', '#'],
    ],
  },
]

function MegaFooter() {
  return (
    <footer className="lc-footer">
      <div className="lc-footer-cols">
        <div className="lc-footer-brandcol">
          <div className="lc-footer-brand">
            <AegisShield size={20} />
            <span className="font-logo" style={{ fontSize: 14 }}>
              AEGIS <span style={{ color: 'var(--accent)' }}>AML</span>
            </span>
          </div>
          <p className="lc-footer-tag">
            The AI compliance platform for Indian fintechs. From alert to FIU-ready SAR in minutes.
          </p>
        </div>
        {FOOTER_COLS.map((c) => (
          <div key={c.head} className="lc-footer-col">
            <div className="lc-footer-head">{c.head}</div>
            {c.links.map(([label, href]) => (
              <a key={label} href={href}>
                {label}
              </a>
            ))}
          </div>
        ))}
      </div>
      <div className="lc-footer-bottom">
        <span className="lc-footer-copy">© 2026 Aegis AML. All rights reserved.</span>
        <span className="lc-footer-made">Built for PMLA 2002 · FIU-IND goAML</span>
      </div>
      <div className="lc-footer-giant" aria-hidden="true">
        AEGIS
      </div>
    </footer>
  )
}

/* ═══════════════════════════════════════════════════════════════════
   PAGE
   ═══════════════════════════════════════════════════════════════════ */

export default function Landing() {
  const rootRef = useRef<HTMLDivElement>(null)
  useRevealOnScroll(rootRef)

  return (
    <div ref={rootRef} className="landing-clean">
      <LandingNav />

      {/* ── Hero ── */}
      <header className="lc-hero">
        <div className="hero-mesh">
          <DotMesh />
        </div>
        <a href="#customers" className="lc-pill rise" style={{ animationDelay: '0ms' }}>
          Explore SAR playbooks from compliance leaders at Novapay
          <ArrowRight size={13} />
        </a>
        <h1 className="lc-h1 rise" style={{ animationDelay: '80ms' }}>
          Every alert triaged.
          <br />
          <span className="lc-h1-grad">Every SAR defensible.</span>
        </h1>
        <p className="lc-sub rise" style={{ animationDelay: '160ms' }}>
          Aegis is the AI compliance platform that triages every alert, drafts every SAR, and
          protects your licence around the clock.
        </p>
        <div className="lc-ctas rise" style={{ animationDelay: '240ms' }}>
          <Link to="/signup" className="btn-landing btn-landing-primary btn-landing-lg">
            Request access
          </Link>
          <a
            href="mailto:sales@aegis-aml.com"
            className="btn-landing btn-landing-secondary btn-landing-lg"
          >
            Talk to sales
          </a>
        </div>
        <div className="lc-trust rise" style={{ animationDelay: '320ms' }}>
          PMLA 2002 <span>·</span> FIU-IND goAML <span>·</span> 8 AML typology checks
        </div>
        <ShowcaseTabs />
      </header>

      {/* ── Customers ── */}
      <LogoBand />

      {/* ── Scroll quote ── */}
      <ScrollQuote />

      {/* ── Agents / risk engine ── */}
      <AgentsSection />

      {/* ── How it works ── */}
      <section className="lc-section" id="how-it-works">
        <div className="lc-section-head reveal">
          <span className="lc-eyebrow">How it works</span>
          <h2 className="lc-h2">Three stages. Fully automated.</h2>
        </div>
        <div className="lc-steps reveal reveal-list">
          {STEPS.map((s, i) => (
            <div key={s.n} className="lc-step reveal-item" style={{ '--d': `${i * 130}ms` } as React.CSSProperties}>
              <span className="lc-step-n">{s.n}</span>
              <h3>{s.title}</h3>
              <p>{s.body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ── Split feature blocks ── */}
      <SplitBlocks />

      {/* ── Features ── */}
      <section className="lc-section" id="capabilities">
        <div className="lc-section-head reveal">
          <span className="lc-eyebrow">Capabilities</span>
          <h2 className="lc-h2">Every tool compliance teams need.</h2>
          <p className="lc-section-sub">
            Built specifically for India's PMLA framework. Nothing generic.
          </p>
        </div>
        <div className="lc-features reveal reveal-list">
          {FEATURES.map((f, i) => (
            <div key={f.title} className="lc-feature reveal-item" style={{ '--d': `${i * 80}ms` } as React.CSSProperties}>
              <div className={cls('lc-feature-icon', f.ico)}>{f.icon}</div>
              <h3>{f.title}</h3>
              <p>{f.body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ── Developers ── */}
      <DeveloperSection />

      {/* ── Stats ── */}
      <StatsBand />

      {/* ── Testimonials ── */}
      <Testimonials />

      {/* ── Security ── */}
      <SecuritySection />

      {/* ── Pricing ── */}
      <Pricing />

      {/* ── FAQ ── */}
      <FAQ />

      {/* ── CTA ── */}
      <section className="lc-cta">
        <div className="cta-mesh">
          <DotMesh />
        </div>
        <div className="reveal lc-cta-content">
          <h2 className="lc-h2" style={{ fontSize: 'clamp(34px, 4vw, 52px)' }}>
            Ready to file your first
            <br />
            intelligent SAR?
          </h2>
          <p className="lc-section-sub" style={{ maxWidth: 440, margin: '16px auto 0' }}>
            Join India's compliance-first fintechs using Aegis to cut SAR preparation time by 94%.
          </p>
          <div className="lc-ctas" style={{ marginTop: 30 }}>
            <Link to="/signup" className="btn-landing btn-landing-primary btn-landing-lg">
              Request access
            </Link>
            <a
              href="mailto:sales@aegis-aml.com"
              className="btn-landing btn-landing-secondary btn-landing-lg"
            >
              Talk to sales
            </a>
          </div>
          <div className="lc-cta-note">No commitment. Set up in under 10 minutes.</div>
        </div>
      </section>

      {/* ── Footer ── */}
      <MegaFooter />
    </div>
  )
}
