import { Check, Cpu, Lock } from 'lucide-react'
import { useLLMConfig } from '../../../hooks/useTenant'
import { Skeleton } from '../../../components/ui/Skeleton'
import { cls, formatNumber } from '../../../utils/format'

export function LLMConfig() {
  const { data: config, isLoading } = useLLMConfig()

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24, maxWidth: 760 }}>
      {/* Provider cards */}
      <div className="anim-fade-in-up">
        <h3 style={{ fontSize: 16, fontWeight: 600, letterSpacing: '-0.01em', marginBottom: 16 }}>
          LLM Provider
        </h3>
        <div className="chart-grid" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
          {/* Managed inference card */}
          <div className={cls('card', 'card-selected')} style={{ position: 'relative' }}>
            <span
              style={{
                position: 'absolute',
                top: 12,
                right: 12,
                width: 22,
                height: 22,
                borderRadius: '50%',
                background: 'var(--accent)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <Check size={13} color="#fff" />
            </span>
            <div
              style={{
                fontFamily: 'var(--font-mono)',
                fontSize: 22,
                fontWeight: 500,
                color: 'var(--text-1)',
                letterSpacing: '-0.02em',
              }}
            >
              aegis ai
            </div>
            <h3 style={{ fontSize: 15, fontWeight: 600, marginTop: 10 }}>SaaS Managed</h3>
            <div style={{ marginTop: 10 }}>
              <span
                style={{
                  background: 'var(--bg-elevated)',
                  border: '1px solid var(--border)',
                  borderRadius: 'var(--r-full)',
                  padding: '3px 10px',
                  fontSize: 11,
                  fontFamily: 'var(--font-mono)',
                  color: 'var(--text-2)',
                }}
              >
                Aegis-managed model
              </span>
            </div>
            <p style={{ fontSize: 13, color: 'var(--text-3)', marginTop: 12, lineHeight: 1.6 }}>
              Managed by Aegis. No configuration required — your drafting model is selected
              automatically based on your plan (Standard or Premium Drafting).
            </p>
          </div>

          {/* Private LLM — locked */}
          <div
            className="card tip"
            style={{ position: 'relative', overflow: 'hidden', cursor: 'not-allowed', display: 'block' }}
          >
            <span className="ribbon">Coming Soon</span>
            <span className="tip-content" style={{ left: '50%', bottom: 'auto', top: '40%' }}>
              Connect your private LLM endpoint — available in a future release.
            </span>
            <div style={{ color: 'var(--text-4)' }}>
              <div style={{ fontSize: 22, fontWeight: 500, letterSpacing: '-0.02em' }}>Private LLM</div>
              <h3 style={{ fontSize: 15, fontWeight: 600, marginTop: 10, color: 'var(--text-4)' }}>
                Bring Your Own Model
              </h3>
              <div style={{ marginTop: 10 }}>
                <span
                  style={{
                    background: 'var(--bg-elevated)',
                    borderRadius: 'var(--r-full)',
                    padding: '3px 10px',
                    fontSize: 11,
                    fontFamily: 'var(--font-mono)',
                    color: 'var(--text-4)',
                  }}
                >
                  self-hosted endpoint
                </span>
              </div>
              <p style={{ fontSize: 13, marginTop: 12, lineHeight: 1.6 }}>
                Route SAR generation through your own on-prem or VPC-hosted model for full data
                sovereignty.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* SAR template style — fixed to Both: goAML filing needs the narrative (reason + PDF) AND
          the structured fields (indicators), so "Both" is the only compliant mode for the MVP. */}
      <div className="anim-fade-in-up" style={{ animationDelay: '80ms' }}>
        <h3 style={{ fontSize: 16, fontWeight: 600, letterSpacing: '-0.01em', marginBottom: 16 }}>
          SAR Template Style
        </h3>
        <div
          className="card"
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: 12,
            borderLeft: '3px solid var(--accent)',
          }}
        >
          <div>
            <div style={{ fontSize: 14, fontWeight: 500, color: 'var(--text-1)' }}>
              Both — narrative + structured fields
            </div>
            <div style={{ fontSize: 13, color: 'var(--text-3)', marginTop: 2 }}>
              Full narrative plus structured fields — the goAML-friendly default.
            </div>
          </div>
          <span
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 5,
              flexShrink: 0,
              fontSize: 12,
              color: 'var(--text-4)',
              whiteSpace: 'nowrap',
            }}
          >
            <Lock size={12} /> Locked for MVP
          </span>
        </div>
      </div>

      {/* Locked settings + token usage */}
      <div className="card anim-fade-in-up" style={{ animationDelay: '160ms' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span className="label-upper">Jurisdiction</span>
            <span style={{ fontSize: 13, color: 'var(--text-2)' }}>
              India — FIU-India goAML <span style={{ color: 'var(--text-4)' }}>(locked for MVP)</span>
            </span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span className="label-upper">Report Language</span>
            <span style={{ fontSize: 13, color: 'var(--text-2)' }}>
              English <span style={{ color: 'var(--text-4)' }}>(locked for MVP)</span>
            </span>
          </div>
          <div style={{ height: 1, background: 'var(--border-subtle)' }} />
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, color: 'var(--text-3)' }}>
            <Cpu size={14} />
            {isLoading ? (
              <Skeleton width={220} height={14} />
            ) : (
              <span>
                <span style={{ color: 'var(--text-1)', fontWeight: 500 }}>
                  {formatNumber(config?.total_tokens_used ?? 0)}
                </span>{' '}
                tokens used ·{' '}
                <span style={{ color: 'var(--text-1)', fontWeight: 500 }}>
                  {formatNumber(config?.total_requests ?? 0)}
                </span>{' '}
                requests
              </span>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
