import type { CSSProperties } from 'react'
import { useQuery } from '@tanstack/react-query'
import { CheckCircle2, CreditCard, Eye, Gift } from 'lucide-react'
import { getBilling } from '../../../api/tenant'
import { Skeleton } from '../../../components/ui/Skeleton'
import { Button } from '../../../components/ui/Button'
import { formatINR, formatNumber } from '../../../utils/format'

const rowStyle: CSSProperties = { display: 'flex', alignItems: 'flex-start', gap: 10 }

export function Billing() {
  const { data: b, isLoading } = useQuery({ queryKey: ['billing'], queryFn: getBilling })

  const freeSars = b?.free_sars ?? 36
  const usedPct = b ? Math.min(100, Math.round((b.sars_this_cycle / Math.max(1, freeSars)) * 100)) : 0
  const remaining = b ? Math.max(0, freeSars - b.sars_this_cycle) : 0

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24, maxWidth: 760 }}>
      {/* Special free-access banner (comped tenants, e.g. Meridian) */}
      {!isLoading && b?.special_free_access && (
        <div
          className="anim-fade-in-up"
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 12,
            padding: '14px 18px',
            borderRadius: 'var(--r-lg)',
            background: 'var(--success-subtle)',
            border: '1px solid var(--success)',
          }}
        >
          <span style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', width: 34, height: 34, borderRadius: 'var(--r-md)', background: 'var(--success)', color: '#fff', flexShrink: 0 }}>
            <Gift size={17} />
          </span>
          <div>
            <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--success)' }}>
              {b.special_access_label ?? 'Your bank has special free access — all SARs are free.'}
            </div>
            <div style={{ fontSize: 12.5, color: 'var(--text-3)', marginTop: 2 }}>
              Nothing is billed to your account — generate SARs freely.
            </div>
          </div>
        </div>
      )}

      {/* Current cycle */}
      <div className="card anim-fade-in-up">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 16, flexWrap: 'wrap' }}>
          <div>
            <span className="label-upper">Current cycle · this month</span>
            <div style={{ fontSize: 32, fontWeight: 600, letterSpacing: '-0.02em', marginTop: 6, fontVariantNumeric: 'tabular-nums' }}>
              {isLoading ? <Skeleton width={120} height={32} /> : formatINR(b?.amount_due_inr ?? 0)}
            </div>
            <div style={{ fontSize: 13, color: b?.within_free_tier ? 'var(--success)' : 'var(--text-3)', marginTop: 4 }}>
              {isLoading
                ? ''
                : b?.within_free_tier
                  ? 'Within free tier — nothing to pay'
                  : `${b?.billable_sars} SAR${b?.billable_sars === 1 ? '' : 's'} beyond the free tier`}
            </div>
          </div>
          {!isLoading && (
            <span
              style={{
                height: 22,
                padding: '0 10px',
                borderRadius: 'var(--r-full)',
                fontSize: 11,
                fontWeight: 600,
                letterSpacing: '0.04em',
                display: 'inline-flex',
                alignItems: 'center',
                background: b?.within_free_tier ? 'var(--success-subtle)' : 'var(--warning-subtle)',
                color: b?.within_free_tier ? 'var(--success)' : 'var(--warning)',
              }}
            >
              {b?.within_free_tier ? 'FREE TIER' : 'PAY-AS-YOU-GO'}
            </span>
          )}
        </div>

        {/* Usage — comped tenants get a flat "free access" state; everyone else a free-tier meter */}
        {!isLoading && b?.special_free_access ? (
          <div style={{ marginTop: 20, fontSize: 13, color: 'var(--text-3)' }}>
            <b style={{ color: 'var(--text-1)' }}>{b.sars_this_cycle}</b> SAR{b.sars_this_cycle === 1 ? '' : 's'} generated
            this cycle · {formatNumber(b.tokens_this_cycle)} tokens — all included at no charge.
          </div>
        ) : (
          <div style={{ marginTop: 20 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, marginBottom: 8 }}>
              <span style={{ color: 'var(--text-2)' }}>SARs generated this cycle</span>
              <span style={{ color: 'var(--text-3)' }}>
                {isLoading ? '' : <><b style={{ color: 'var(--text-1)' }}>{b?.sars_this_cycle}</b> / {freeSars} free</>}
              </span>
            </div>
            <div style={{ height: 8, borderRadius: 999, background: 'var(--bg-elevated)', overflow: 'hidden' }}>
              <div
                style={{
                  height: '100%',
                  width: `${usedPct}%`,
                  background: usedPct >= 100 ? 'var(--warning)' : 'var(--accent)',
                  transition: 'width 500ms ease-out',
                }}
              />
            </div>
            <div style={{ fontSize: 12, color: 'var(--text-4)', marginTop: 8 }}>
              {isLoading
                ? ''
                : `${remaining} free SAR${remaining === 1 ? '' : 's'} left · ${formatNumber(b?.tokens_this_cycle ?? 0)} tokens used this cycle`}
            </div>
          </div>
        )}
      </div>

      {/* Upgrade to a plan */}
      {!isLoading && b?.plans && b.plans.length > 0 && (
        <div className="card anim-fade-in-up" style={{ animationDelay: '60ms' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: 12, flexWrap: 'wrap', marginBottom: 4 }}>
            <h3 style={{ fontSize: 15, fontWeight: 600 }}>Plans &amp; drafting tiers</h3>
            <span style={{ fontSize: 12, color: 'var(--text-4)' }}>
              Standard {formatINR(b.price_per_sar_inr)}/SAR · Premium {formatINR(b.premium_price_per_sar_inr)}/SAR
            </span>
          </div>
          <p style={{ fontSize: 13, color: 'var(--text-3)', marginBottom: 18, lineHeight: 1.5 }}>
            You're on <b style={{ color: 'var(--text-1)' }}>Standard Drafting</b> at{' '}
            {formatINR(b.price_per_sar_inr)} per SAR. Switch to <b style={{ color: 'var(--text-1)' }}>Premium Drafting</b>{' '}
            at {formatINR(b.premium_price_per_sar_inr)} per SAR for the highest-quality narratives, or
            prepay a monthly volume plan.
          </p>
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(170px, 1fr))',
              gap: 12,
            }}
          >
            {b.plans.map((p) => {
              const isCurrent = p.id === b.current_plan
              const isRecommended = !isCurrent && p.id === b.recommended_plan
              return (
                <div
                  key={p.id}
                  style={{
                    border: `1px solid ${isRecommended ? 'var(--accent)' : 'var(--border)'}`,
                    borderRadius: 'var(--r-lg)',
                    padding: '16px 14px',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: 10,
                    background: isCurrent ? 'var(--bg-elevated)' : 'var(--bg-surface)',
                    position: 'relative',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{ fontSize: 13.5, fontWeight: 600 }}>{p.name}</span>
                    {isCurrent && (
                      <span style={{ fontSize: 10, fontWeight: 600, letterSpacing: '0.04em', color: 'var(--text-3)', background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 'var(--r-full)', padding: '1px 7px' }}>
                        CURRENT
                      </span>
                    )}
                    {isRecommended && (
                      <span style={{ fontSize: 10, fontWeight: 600, letterSpacing: '0.04em', color: 'var(--accent)', background: 'var(--accent-subtle)', borderRadius: 'var(--r-full)', padding: '1px 7px' }}>
                        SUGGESTED
                      </span>
                    )}
                  </div>
                  <div style={{ fontSize: 22, fontWeight: 600, letterSpacing: '-0.02em', fontVariantNumeric: 'tabular-nums' }}>
                    {p.monthly_inr !== null
                      ? formatINR(p.monthly_inr)
                      : p.per_sar_inr !== null
                        ? formatINR(p.per_sar_inr)
                        : 'Custom'}
                    <span style={{ fontSize: 12, fontWeight: 400, color: 'var(--text-4)' }}>
                      {p.monthly_inr !== null ? ' / mo' : p.per_sar_inr !== null ? ' / SAR' : ''}
                    </span>
                  </div>
                  <div style={{ fontSize: 12, color: 'var(--text-3)', display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
                    <span>{p.included_sars === null ? 'Pay per report' : `${formatNumber(p.included_sars)} SARs / month`}</span>
                    <span style={{ fontSize: 10, fontWeight: 600, letterSpacing: '0.02em', color: 'var(--text-3)', background: 'var(--bg-elevated)', borderRadius: 'var(--r-sm)', padding: '1px 6px' }}>
                      {p.model}
                    </span>
                  </div>
                  <ul style={{ display: 'flex', flexDirection: 'column', gap: 6, fontSize: 12, color: 'var(--text-2)', marginTop: 2 }}>
                    {p.features.map((f) => (
                      <li key={f} style={{ display: 'flex', gap: 6, alignItems: 'flex-start' }}>
                        <CheckCircle2 size={12} color="var(--success)" style={{ flexShrink: 0, marginTop: 2 }} />
                        <span>{f}</span>
                      </li>
                    ))}
                  </ul>
                  <Button
                    variant={isCurrent ? 'secondary' : isRecommended ? 'primary' : 'secondary'}
                    size="sm"
                    fullWidth
                    disabled={isCurrent}
                    style={{ marginTop: 'auto' }}
                    title={isCurrent ? 'This is your current plan' : 'Contact sales to switch plans'}
                    onClick={() => {
                      if (!isCurrent) window.location.href = 'mailto:sales@aegis-aml.com?subject=Upgrade%20to%20' + encodeURIComponent(p.name)
                    }}
                  >
                    {isCurrent
                      ? 'Current plan'
                      : p.monthly_inr === null && p.per_sar_inr === null
                        ? 'Talk to sales'
                        : p.id === 'premium'
                          ? 'Switch to Premium'
                          : 'Upgrade'}
                  </Button>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* How billing works */}
      <div className="card anim-fade-in-up" style={{ animationDelay: '80ms' }}>
        <h3 style={{ fontSize: 15, fontWeight: 600, marginBottom: 14 }}>How billing works</h3>
        <ul style={{ display: 'flex', flexDirection: 'column', gap: 12, fontSize: 13.5, color: 'var(--text-2)', lineHeight: 1.55 }}>
          <li style={rowStyle}>
            <CheckCircle2 size={15} color="var(--success)" style={{ flexShrink: 0, marginTop: 2 }} />
            <span>
              The first <b>{freeSars} SARs</b> (~{formatNumber(b?.free_tokens ?? 100000)} tokens) each month are <b>free</b>.
            </span>
          </li>
          <li style={rowStyle}>
            <CreditCard size={15} color="var(--text-3)" style={{ flexShrink: 0, marginTop: 2 }} />
            <span>
              Beyond that, <b>{formatINR(b?.price_per_sar_inr ?? 5)} per SAR</b> on <b>Standard Drafting</b> —
              billed only for the reports you actually generate.
            </span>
          </li>
          <li style={rowStyle}>
            <CreditCard size={15} color="var(--accent-text)" style={{ flexShrink: 0, marginTop: 2 }} />
            <span>
              <b>Premium Drafting</b> is <b>{formatINR(b?.premium_price_per_sar_inr ?? 10)} per SAR</b> —
              our most capable drafting tier for the highest-quality narratives.
            </span>
          </li>
          <li style={rowStyle}>
            <Eye size={15} color="var(--text-3)" style={{ flexShrink: 0, marginTop: 2 }} />
            <span>
              Viewing reports, the dashboard, and downloading PDFs are always free — you're billed only when a new SAR is generated.
            </span>
          </li>
        </ul>
      </div>
    </div>
  )
}
