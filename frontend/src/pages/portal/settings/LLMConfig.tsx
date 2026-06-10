import { Check, Cpu } from 'lucide-react'
import { useQueryClient } from '@tanstack/react-query'
import { useLLMConfig } from '../../../hooks/useTenant'
import { updateLLMConfig } from '../../../api/tenant'
import { Skeleton } from '../../../components/ui/Skeleton'
import { useToast } from '../../../components/ui/Toast'
import { cls, formatNumber } from '../../../utils/format'
import type { LLMConfig as LLMConfigType } from '../../../types'

const STYLES: { key: LLMConfigType['sar_template_style']; label: string; description: string }[] = [
  {
    key: 'NARRATIVE',
    label: 'Narrative',
    description: 'Long-form prose SAR narrative — reads like an officer-written report.',
  },
  {
    key: 'STRUCTURED',
    label: 'Structured Fields',
    description: 'Key fields and a summary table — optimized for machine parsing.',
  },
  {
    key: 'BOTH',
    label: 'Both (Recommended)',
    description: 'Full narrative plus structured fields — the goAML-friendly default.',
  },
]

export function LLMConfig() {
  const { data: config, isLoading } = useLLMConfig()
  const { toast } = useToast()
  const qc = useQueryClient()

  const handleStyle = async (style: LLMConfigType['sar_template_style']) => {
    qc.setQueryData(['llm-config'], (old: LLMConfigType | undefined) =>
      old ? { ...old, sar_template_style: style } : old,
    )
    await updateLLMConfig(style)
    qc.invalidateQueries({ queryKey: ['llm-config'] })
    toast('success', 'SAR template style updated')
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24, maxWidth: 760 }}>
      {/* Provider cards */}
      <div className="anim-fade-in-up">
        <h3 style={{ fontSize: 16, fontWeight: 600, letterSpacing: '-0.01em', marginBottom: 16 }}>
          LLM Provider
        </h3>
        <div className="chart-grid" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
          {/* Groq card */}
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
              groq
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
                llama-3.3-70b-versatile
              </span>
            </div>
            <p style={{ fontSize: 13, color: 'var(--text-3)', marginTop: 12, lineHeight: 1.6 }}>
              Managed by Aegis. No configuration required. Sub-3-second SAR drafts on Groq LPU
              inference.
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

      {/* SAR template style */}
      <div className="anim-fade-in-up" style={{ animationDelay: '80ms' }}>
        <h3 style={{ fontSize: 16, fontWeight: 600, letterSpacing: '-0.01em', marginBottom: 16 }}>
          SAR Template Style
        </h3>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {isLoading ? (
            <>
              <Skeleton height={68} />
              <Skeleton height={68} />
              <Skeleton height={68} />
            </>
          ) : (
            STYLES.map((s) => {
              const active = config?.sar_template_style === s.key
              return (
                <button
                  key={s.key}
                  onClick={() => handleStyle(s.key)}
                  style={{
                    textAlign: 'left',
                    width: '100%',
                    padding: 16,
                    background: active ? 'var(--accent-subtle)' : 'var(--bg-surface)',
                    border: '1px solid var(--border-subtle)',
                    borderLeft: `3px solid ${active ? 'var(--accent)' : 'var(--border-subtle)'}`,
                    borderRadius: 'var(--r-md)',
                    cursor: 'pointer',
                    transition: 'background 150ms ease-out, border-color 150ms ease-out',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 14,
                  }}
                >
                  <span
                    style={{
                      width: 18,
                      height: 18,
                      borderRadius: '50%',
                      border: `1.5px solid ${active ? 'var(--accent)' : 'var(--border-strong)'}`,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      flexShrink: 0,
                      transition: 'border-color 150ms',
                    }}
                  >
                    {active && (
                      <span
                        className="anim-scale-in"
                        style={{ width: 10, height: 10, borderRadius: '50%', background: 'var(--accent)' }}
                      />
                    )}
                  </span>
                  <span>
                    <span style={{ fontSize: 14, fontWeight: 500, color: 'var(--text-1)', display: 'block' }}>
                      {s.label}
                    </span>
                    <span style={{ fontSize: 13, color: 'var(--text-3)', marginTop: 2, display: 'block' }}>
                      {s.description}
                    </span>
                  </span>
                </button>
              )
            })
          )}
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
