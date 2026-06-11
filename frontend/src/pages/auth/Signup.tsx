import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Check } from 'lucide-react'
import { signup } from '../../api/auth'
import { useAuthStore } from '../../store/auth'
import { AegisShield } from '../../components/AegisLogo'
import { Button } from '../../components/ui/Button'
import { Input, Field, Select } from '../../components/ui/Input'

const COMPANY_TYPES = [
  { value: 'FINTECH', label: 'Fintech' },
  { value: 'BROKER', label: 'Broker' },
  { value: 'NBFC', label: 'NBFC' },
  { value: 'PAYMENT_CO', label: 'Payment Company' },
  { value: 'OTHER', label: 'Other' },
]

const STEPS = ['Company Details', 'Administrator', 'Review & Submit']

interface FormState {
  company_name: string
  company_type: string
  cin: string
  website: string
  admin_name: string
  admin_email: string
  admin_phone: string
  admin_designation: string
  admin_password: string
}

export function Signup() {
  const [step, setStep] = useState(0)
  const [direction, setDirection] = useState<'fwd' | 'back'>('fwd')
  const [agreed, setAgreed] = useState(false)
  const [loading, setLoading] = useState(false)
  const [submitted, setSubmitted] = useState(false)
  const [errors, setErrors] = useState<Partial<Record<keyof FormState, string>>>({})
  const [form, setForm] = useState<FormState>({
    company_name: '',
    company_type: 'FINTECH',
    cin: '',
    website: '',
    admin_name: '',
    admin_email: '',
    admin_phone: '',
    admin_designation: '',
    admin_password: '',
  })
  const navigate = useNavigate()
  const setAuth = useAuthStore((s) => s.setAuth)

  const set = (key: keyof FormState) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    setForm((f) => ({ ...f, [key]: e.target.value }))
    setErrors((er) => ({ ...er, [key]: undefined }))
  }

  const validateStep = (): boolean => {
    const e: Partial<Record<keyof FormState, string>> = {}
    if (step === 0) {
      if (!form.company_name.trim()) e.company_name = 'Company name is required.'
    } else if (step === 1) {
      if (!form.admin_name.trim()) e.admin_name = 'Full name is required.'
      if (!/^\S+@\S+\.\S+$/.test(form.admin_email)) e.admin_email = 'Enter a valid work email.'
      if (form.admin_password.length < 10) e.admin_password = 'Password must be at least 10 characters.'
    }
    setErrors(e)
    return Object.keys(e).length === 0
  }

  const next = () => {
    if (!validateStep()) return
    setDirection('fwd')
    setStep((s) => Math.min(s + 1, 2))
  }
  const back = () => {
    setDirection('back')
    setStep((s) => Math.max(s - 1, 0))
  }

  const handleSubmit = async () => {
    if (!agreed) return
    setLoading(true)
    try {
      const result = await signup(form)
      setAuth(result.user, result.access_token, result.refresh_token)
      setSubmitted(true)
      setTimeout(() => navigate('/status'), 2200)
    } finally {
      setLoading(false)
    }
  }

  const summaryRows: [string, string][] = [
    ['Company Name', form.company_name],
    ['Company Type', COMPANY_TYPES.find((t) => t.value === form.company_type)?.label ?? ''],
    ['CIN', form.cin || '—'],
    ['Website', form.website || '—'],
    ['Administrator', form.admin_name],
    ['Work Email', form.admin_email],
    ['Phone', form.admin_phone || '—'],
    ['Designation', form.admin_designation || '—'],
  ]

  return (
    <div
      style={{
        width: 480,
        maxWidth: '100%',
        background: 'var(--bg-surface)',
        border: '1px solid var(--border)',
        borderRadius: 'var(--r-xl)',
        boxShadow: 'var(--shadow-lg)',
        padding: 40,
        animation: 'scaleIn 250ms ease-out',
        overflow: 'hidden',
        margin: 'auto',
      }}
    >
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 28 }}>
          <AegisShield size={28} />
          <div>
            <div style={{ fontSize: 16, fontWeight: 700 }}>
              <span style={{ color: 'var(--text-1)' }}>AEGIS</span>{' '}
              <span style={{ color: 'var(--accent)' }}>AML</span>
            </div>
            <div style={{ fontSize: 12, color: 'var(--text-3)' }}>Request Access</div>
          </div>
        </div>

        {!submitted && (
          <>
            {/* Step progress */}
            <div style={{ display: 'flex', alignItems: 'center', marginBottom: 28 }}>
              {STEPS.map((label, i) => (
                <div key={label} style={{ display: 'flex', alignItems: 'center', flex: i < STEPS.length - 1 ? 1 : 'none' }}>
                  <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 }}>
                    <div
                      style={{
                        width: 28,
                        height: 28,
                        borderRadius: '50%',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        fontSize: 12,
                        fontWeight: 600,
                        flexShrink: 0,
                        background: i <= step ? 'var(--accent)' : 'transparent',
                        border: `1.5px solid ${i <= step ? 'var(--accent)' : 'var(--border)'}`,
                        color: i <= step ? '#fff' : 'var(--text-4)',
                        transition: 'background 400ms, border-color 400ms, color 400ms',
                      }}
                    >
                      {i < step ? <Check size={14} /> : i + 1}
                    </div>
                  </div>
                  {i < STEPS.length - 1 && (
                    <div style={{ flex: 1, height: 2, background: 'var(--border)', margin: '0 8px', position: 'relative', overflow: 'hidden', borderRadius: 1 }}>
                      <div
                        style={{
                          position: 'absolute',
                          inset: 0,
                          background: 'var(--accent)',
                          width: i < step ? '100%' : '0%',
                          transition: 'width 400ms cubic-bezier(0.4,0,0.2,1)',
                        }}
                      />
                    </div>
                  )}
                </div>
              ))}
            </div>

            <h2 style={{ fontSize: 20, fontWeight: 600, letterSpacing: '-0.015em', marginBottom: 20 }}>
              {STEPS[step]}
            </h2>

            <div key={step} className={direction === 'fwd' ? 'anim-slide-right' : 'anim-slide-top'}>
              {step === 0 && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                  <Field label="Company Name" error={errors.company_name}>
                    <Input placeholder="PayFast India Pvt Ltd" value={form.company_name} onChange={set('company_name')} error={!!errors.company_name} autoFocus />
                  </Field>
                  <Field label="Company Type">
                    <Select options={COMPANY_TYPES} value={form.company_type} onChange={set('company_type')} />
                  </Field>
                  <Field label="CIN" hint="Corporate Identity Number — issued by MCA">
                    <Input placeholder="U74999MH2021PTC123456 (optional)" value={form.cin} onChange={set('cin')} />
                  </Field>
                  <Field label="Website">
                    <Input placeholder="https://yourcompany.in" value={form.website} onChange={set('website')} />
                  </Field>
                  <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 8 }}>
                    <Button onClick={next}>Continue →</Button>
                  </div>
                </div>
              )}

              {step === 1 && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                  <Field label="Full Name" error={errors.admin_name}>
                    <Input placeholder="Nikhil Karur" value={form.admin_name} onChange={set('admin_name')} error={!!errors.admin_name} autoFocus />
                  </Field>
                  <Field label="Work Email" error={errors.admin_email}>
                    <Input type="email" placeholder="you@company.in" value={form.admin_email} onChange={set('admin_email')} error={!!errors.admin_email} />
                  </Field>
                  <Field label="Phone">
                    <Input placeholder="+91 98765 43210" value={form.admin_phone} onChange={set('admin_phone')} />
                  </Field>
                  <Field label="Designation">
                    <Input placeholder="Head of Compliance" value={form.admin_designation} onChange={set('admin_designation')} />
                  </Field>
                  <Field label="Password" error={errors.admin_password} hint="Minimum 10 characters — this signs you into the portal.">
                    <Input type="password" placeholder="••••••••••" value={form.admin_password} onChange={set('admin_password')} error={!!errors.admin_password} autoComplete="new-password" />
                  </Field>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 8 }}>
                    <Button variant="ghost" onClick={back}>
                      ← Back
                    </Button>
                    <Button onClick={next}>Continue →</Button>
                  </div>
                </div>
              )}

              {step === 2 && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
                  <div
                    style={{
                      background: 'var(--bg-base)',
                      border: '1px solid var(--border-subtle)',
                      borderRadius: 'var(--r-md)',
                      padding: '4px 16px',
                    }}
                  >
                    {summaryRows.map(([label, value], i) => (
                      <div
                        key={label}
                        style={{
                          display: 'grid',
                          gridTemplateColumns: '140px 1fr',
                          gap: 12,
                          padding: '10px 0',
                          borderBottom: i < summaryRows.length - 1 ? '1px solid var(--border-subtle)' : 'none',
                        }}
                      >
                        <span className="label-upper" style={{ alignSelf: 'center' }}>{label}</span>
                        <span style={{ fontSize: 14, color: 'var(--text-1)', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                          {value || '—'}
                        </span>
                      </div>
                    ))}
                  </div>

                  <label style={{ display: 'flex', gap: 10, alignItems: 'flex-start', cursor: 'pointer' }}>
                    <span
                      onClick={() => setAgreed((a) => !a)}
                      style={{
                        width: 18,
                        height: 18,
                        borderRadius: 'var(--r-sm)',
                        border: `1.5px solid ${agreed ? 'var(--accent)' : 'var(--border-strong)'}`,
                        background: agreed ? 'var(--accent)' : 'transparent',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        flexShrink: 0,
                        marginTop: 1,
                        transition: 'background var(--t-fast), border-color var(--t-fast)',
                      }}
                    >
                      {agreed && <Check size={12} color="#fff" />}
                    </span>
                    <span style={{ fontSize: 13, color: 'var(--text-2)', lineHeight: 1.5 }} onClick={() => setAgreed((a) => !a)}>
                      I confirm this entity is regulated under PMLA/SEBI AML guidelines and the
                      information provided is accurate.
                    </span>
                  </label>

                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <Button variant="ghost" onClick={back}>
                      ← Back
                    </Button>
                  </div>
                  <Button onClick={handleSubmit} loading={loading} disabled={!agreed} fullWidth style={{ height: 40 }}>
                    Submit Application
                  </Button>
                </div>
              )}
            </div>
          </>
        )}

        {submitted && (
          <div
            className="anim-fade-in"
            style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', textAlign: 'center', padding: '24px 0' }}
          >
            <div
              style={{
                width: 48,
                height: 48,
                borderRadius: '50%',
                background: 'var(--success-subtle)',
                border: '1.5px solid var(--success)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                animation: 'scaleIn 300ms cubic-bezier(0.34,1.56,0.64,1)',
              }}
            >
              <Check size={24} color="var(--success)" />
            </div>
            <h2 style={{ fontSize: 20, fontWeight: 600, marginTop: 16 }}>Application Submitted!</h2>
            <p style={{ fontSize: 14, color: 'var(--text-3)', marginTop: 8, maxWidth: 320 }}>
              We verify all entities manually. You'll hear back within 1–2 business days.
            </p>
            <div style={{ marginTop: 16, display: 'flex', alignItems: 'center', gap: 8, color: 'var(--text-4)', fontSize: 13 }}>
              <span className="spinner spinner-accent" />
              Redirecting to your status page…
            </div>
          </div>
        )}

        {!submitted && (
          <div style={{ textAlign: 'center', marginTop: 24 }}>
            <Link
              to="/login"
              style={{ fontSize: 13, color: 'var(--text-3)', textDecoration: 'none' }}
              onMouseEnter={(e) => (e.currentTarget.style.color = 'var(--accent-text)')}
              onMouseLeave={(e) => (e.currentTarget.style.color = 'var(--text-3)')}
            >
              Already registered? Sign in →
            </Link>
          </div>
        )}
    </div>
  )
}
