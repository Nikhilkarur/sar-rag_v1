import { useMemo, useRef } from 'react'
import { Check, CreditCard, Download, Landmark, Printer, TrendingUp } from 'lucide-react'
import { useQueryClient } from '@tanstack/react-query'
import { useSchemas } from '../../../hooks/useTenant'
import { selectSchema } from '../../../api/tenant'
import { useAuthStore } from '../../../store/auth'
import { Button } from '../../../components/ui/Button'
import { Skeleton } from '../../../components/ui/Skeleton'
import { useToast } from '../../../components/ui/Toast'
import { cls } from '../../../utils/format'
import { buildTechDocHtml } from './techDoc'

const ICONS: Record<string, React.ReactNode> = {
  STANDARD_FINTECH: <Landmark size={28} color="var(--accent-text)" />,
  SEBI_BROKER: <TrendingUp size={28} color="var(--info)" />,
  PAYMENT_GW: <CreditCard size={28} color="var(--success)" />,
}

/* The API returns { name, template_key, is_active, field_map, pii_fields } —
   description and key-field chips are presentation-only, so they live here. */
const FALLBACK_DESC: Record<string, string> = {
  STANDARD_FINTECH:
    'For NEFT / UPI / IMPS transaction alerts from standard core-banking or fintech TMS payloads.',
  SEBI_BROKER:
    'For broking and securities alerts — pay-in / pay-out, contract notes and trade-surveillance feeds.',
  PAYMENT_GW:
    'For payment-gateway alerts — merchant settlements, refunds and chargeback streams.',
}

export function Schema() {
  const { data, isLoading } = useSchemas()
  const { user } = useAuthStore()
  const { toast } = useToast()
  const qc = useQueryClient()

  const tenantId = user?.tenant?.tenantIdPublic ?? 'TEN-XXXX'
  const docHtml = useMemo(() => buildTechDocHtml(tenantId), [tenantId])
  const frameRef = useRef<HTMLIFrameElement>(null)

  const fitFrame = () => {
    const f = frameRef.current
    if (f?.contentWindow) f.style.height = `${f.contentWindow.document.body.scrollHeight + 8}px`
  }

  const handlePrint = () => {
    const w = frameRef.current?.contentWindow
    if (w) { w.focus(); w.print() }
  }

  const handleDownload = () => {
    const blob = new Blob([docHtml], { type: 'text/html;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `aegis-integration-${tenantId}.html`
    document.body.appendChild(a)
    a.click()
    a.remove()
    URL.revokeObjectURL(url)
    toast('success', 'Downloaded', 'Share this file with your engineering team.')
  }

  const handleSelect = async (templateKey: string, name: string) => {
    // Optimistic: flip active card immediately, then confirm.
    qc.setQueryData(['schemas'], (old: typeof data) =>
      old ? (old as any[]).map((p: any) => ({ ...p, is_active: p.template_key === templateKey })) : old,
    )
    await selectSchema(templateKey)
    qc.invalidateQueries({ queryKey: ['schemas'] })
    toast('success', 'Schema updated', `Now mapping payloads with "${name}".`)
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 32 }}>
      <div className="anim-fade-in-up">
        <h3 style={{ fontSize: 16, fontWeight: 600, letterSpacing: '-0.01em', marginBottom: 4 }}>
          Alert Schema Mapping
        </h3>
        <p style={{ fontSize: 13, color: 'var(--text-3)', maxWidth: 560 }}>
          Tell Aegis which fields in your alert payload contain sensitive data, transaction
          identifiers, and risk signals. Pick the preset that matches your TMS.
        </p>
      </div>

      {/* Preset cards */}
      <div
        className="chart-grid"
        style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16 }}
      >
        {isLoading ? (
          <>
            <Skeleton height={240} style={{ borderRadius: 'var(--r-lg)' }} />
            <Skeleton height={240} style={{ borderRadius: 'var(--r-lg)' }} />
            <Skeleton height={240} style={{ borderRadius: 'var(--r-lg)' }} />
          </>
        ) : (
          ((data as any[]) ?? []).map((preset: any, i: number) => {
            const active = preset.is_active
            const keyFields: string[] =
              preset.key_fields ?? Object.keys(preset.field_map ?? {}).slice(0, 6)
            const description: string =
              preset.description ??
              FALLBACK_DESC[preset.template_key] ??
              'Maps your TMS payload into the 16 Aegis standard fields.'
            return (
              <div
                key={preset.template_key}
                className={cls('card', 'card-interactive', active && 'card-selected')}
                style={{
                  position: 'relative',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: 12,
                  animation: `fadeInUp 300ms ease-out ${i * 80}ms both`,
                }}
              >
                {active && (
                  <span
                    className="anim-scale-in"
                    style={{
                      position: 'absolute',
                      top: 12,
                      right: 12,
                      height: 20,
                      padding: '0 8px',
                      borderRadius: 'var(--r-full)',
                      background: 'var(--accent-subtle)',
                      color: 'var(--accent-text)',
                      fontSize: 10,
                      fontWeight: 600,
                      letterSpacing: '0.05em',
                      textTransform: 'uppercase',
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: 4,
                    }}
                  >
                    <Check size={10} />
                    Active
                  </span>
                )}
                <div
                  style={{
                    width: 48,
                    height: 48,
                    borderRadius: 'var(--r-md)',
                    background: 'var(--bg-elevated)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}
                >
                  {ICONS[preset.template_key]}
                </div>
                <h3 style={{ fontSize: 16, fontWeight: 600, letterSpacing: '-0.01em', lineHeight: 1.4 }}>
                  {preset.name}
                </h3>
                <p style={{ fontSize: 13, color: 'var(--text-3)', lineHeight: 1.6, flex: 1 }}>
                  {description}
                </p>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                  {keyFields.map((f: string) => (
                    <span
                      key={f}
                      style={{
                        background: 'var(--bg-elevated)',
                        borderRadius: 'var(--r-sm)',
                        padding: '2px 6px',
                        fontSize: 11,
                        fontFamily: 'var(--font-mono)',
                        color: 'var(--text-3)',
                      }}
                    >
                      {f}
                    </span>
                  ))}
                </div>
                <div style={{ marginTop: 4 }}>
                  <Button
                    variant="ghost"
                    size="sm"
                    disabled={active}
                    onClick={() => handleSelect(preset.template_key, preset.name)}
                  >
                    {active ? 'Selected' : 'Select'}
                  </Button>
                </div>
              </div>
            )
          })
        )}
      </div>

      {/* Technical integration reference — the single handoff doc (printable + downloadable) */}
      <div className="card anim-fade-in-up" style={{ padding: 0, animationDelay: '240ms' }}>
        <div
          style={{
            display: 'flex',
            alignItems: 'flex-start',
            justifyContent: 'space-between',
            gap: 16,
            flexWrap: 'wrap',
            padding: '20px 24px',
            borderBottom: '1px solid var(--border-subtle)',
          }}
        >
          <div>
            <h3 style={{ fontSize: 16, fontWeight: 600, letterSpacing: '-0.01em' }}>
              Technical integration reference
            </h3>
            <p style={{ fontSize: 13, color: 'var(--text-3)', marginTop: 4, maxWidth: 620 }}>
              Everything your engineering team needs — the ingest endpoint, authentication, the full
              payload schema, and the report webhook — in one document. Print it or download it to hand off.
            </p>
          </div>
          <div style={{ display: 'flex', gap: 8, flexShrink: 0 }}>
            <Button variant="secondary" size="sm" icon={<Printer size={14} />} onClick={handlePrint}>
              Print / PDF
            </Button>
            <Button variant="secondary" size="sm" icon={<Download size={14} />} onClick={handleDownload}>
              Download
            </Button>
          </div>
        </div>
        <div style={{ padding: 16 }}>
          <iframe
            ref={frameRef}
            title="Aegis technical integration reference"
            srcDoc={docHtml}
            onLoad={fitFrame}
            style={{
              width: '100%',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--r-md)',
              background: '#fff',
              minHeight: 400,
            }}
          />
        </div>
      </div>
    </div>
  )
}
