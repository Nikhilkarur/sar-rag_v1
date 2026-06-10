import { Check, CreditCard, Landmark, TrendingUp } from 'lucide-react'
import { useQueryClient } from '@tanstack/react-query'
import { useSchemas } from '../../../hooks/useTenant'
import { selectSchema } from '../../../api/tenant'
import { Button } from '../../../components/ui/Button'
import { Skeleton } from '../../../components/ui/Skeleton'
import { useToast } from '../../../components/ui/Toast'
import { cls } from '../../../utils/format'

const ICONS: Record<string, React.ReactNode> = {
  STANDARD_FINTECH: <Landmark size={28} color="var(--accent-text)" />,
  SEBI_BROKER: <TrendingUp size={28} color="var(--info)" />,
  PAYMENT_GW: <CreditCard size={28} color="var(--success)" />,
}

const STANDARD_FIELDS: { field: string; example: string; pii: boolean }[] = [
  { field: 'customer_name', example: 'Rajesh Kumar Sharma', pii: true },
  { field: 'customer_id', example: 'CUST-98271', pii: true },
  { field: 'account_id', example: 'HDFC-00123456789', pii: true },
  { field: 'transaction_id', example: 'TXN-2026-061099182', pii: false },
  { field: 'transaction_amount', example: '990000.00', pii: false },
  { field: 'transaction_currency', example: 'INR', pii: false },
  { field: 'transaction_type', example: 'NEFT_TRANSFER', pii: false },
  { field: 'transaction_direction', example: 'DEBIT', pii: false },
  { field: 'transaction_timestamp', example: '2026-06-10T09:30:00+05:30', pii: false },
  { field: 'counterparty_account', example: 'ICICI-00987654321', pii: true },
  { field: 'counterparty_name', example: 'Priya Enterprises', pii: true },
  { field: 'counterparty_institution', example: 'ICICI Bank', pii: false },
  { field: 'ip_address', example: '103.27.9.44', pii: true },
  { field: 'device_id', example: 'MOB-a1b2c3d4e5f6', pii: true },
  { field: 'risk_score', example: '87', pii: false },
  { field: 'alert_reason', example: 'Near reporting threshold', pii: false },
]

export function Schema() {
  const { data, isLoading } = useSchemas()
  const { toast } = useToast()
  const qc = useQueryClient()

  const handleSelect = async (templateKey: string, name: string) => {
    // Optimistic: flip active card immediately, then confirm.
    qc.setQueryData(['schemas'], (old: typeof data) =>
      old ? (old as any[]).map((p: any) => ({ ...p, is_active: p.template_key === templateKey })) : old,
    )
    await selectSchema(templateKey)
    qc.invalidateQueries({ queryKey: ['schemas'] })
    toast('success', 'Schema updated', `Now mapping payloads with “${name}”.`)
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
                  {preset.description}
                </p>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                  {preset.key_fields.map((f: string) => (
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

      {/* Extracted fields */}
      <div className="card anim-fade-in-up" style={{ padding: 0, animationDelay: '240ms' }}>
        <div style={{ padding: '20px 24px 8px' }}>
          <h3 style={{ fontSize: 16, fontWeight: 600, letterSpacing: '-0.01em' }}>What Aegis extracts</h3>
          <p style={{ fontSize: 13, color: 'var(--text-3)', marginTop: 4 }}>
            Every payload is normalized into these 16 standard fields. PII fields are tokenized
            before analysis.
          </p>
        </div>
        <div className="tbl-scroll">
          <table className="tbl">
            <thead>
              <tr>
                <th style={{ paddingLeft: 24 }}>Standard Field</th>
                <th>Example Value</th>
                <th style={{ paddingRight: 24 }}>PII</th>
              </tr>
            </thead>
            <tbody>
              {STANDARD_FIELDS.map((f) => (
                <tr key={f.field}>
                  <td
                    style={{
                      paddingLeft: 24,
                      fontFamily: 'var(--font-mono)',
                      fontSize: 13,
                      color: 'var(--text-1)',
                      height: 40,
                    }}
                  >
                    {f.field}
                  </td>
                  <td style={{ fontSize: 13, color: 'var(--text-3)', height: 40 }}>{f.example}</td>
                  <td style={{ paddingRight: 24, height: 40 }}>
                    {f.pii ? (
                      <span
                        style={{
                          height: 20,
                          padding: '0 8px',
                          borderRadius: 'var(--r-full)',
                          background: 'var(--warning-subtle)',
                          color: 'var(--warning)',
                          fontSize: 10,
                          fontWeight: 600,
                          display: 'inline-flex',
                          alignItems: 'center',
                        }}
                      >
                        MASKED
                      </span>
                    ) : (
                      <span style={{ fontSize: 12, color: 'var(--text-4)' }}>—</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
