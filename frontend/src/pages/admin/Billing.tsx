import { useQuery } from '@tanstack/react-query'
import { Gift, Info, Receipt, Users } from 'lucide-react'
import { getPlatformBilling } from '../../api/admin'
import { useCountUp } from '../../hooks/useCountUp'
import { SkeletonStatCard, SkeletonTableRows } from '../../components/ui/Skeleton'
import { formatINR, formatNumber } from '../../utils/format'

function Stat({ icon, color, value, label, sub, index }: { icon: React.ReactNode; color: string; value: string; label: string; sub?: string; index: number }) {
  return (
    <div className="stat-card" style={{ padding: '20px 24px', animation: `fadeInUp 240ms ease-out ${index * 50}ms both` }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 7, fontSize: 13, color: 'var(--text-3)' }}>
        <span style={{ display: 'inline-flex', color }}>{icon}</span>
        {label}
      </div>
      <div style={{ fontSize: 26, fontWeight: 600, marginTop: 8, letterSpacing: '-0.02em', fontVariantNumeric: 'tabular-nums' }}>
        {value}
      </div>
      {sub && <div style={{ fontSize: 12, color: 'var(--text-4)', marginTop: 3 }}>{sub}</div>}
    </div>
  )
}

export function Billing() {
  const { data, isLoading } = useQuery({ queryKey: ['platform-billing'], queryFn: getPlatformBilling, refetchInterval: 30_000 })

  const total = useCountUp(data?.total_amount_due_inr ?? 0)
  const clients = data?.clients ?? []
  // Only meaningful once at least one client exists.
  const allComped = !isLoading && !!data && data.client_count > 0 && data.billable_client_count === 0

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      {/* All-free note — true today (only TEN-0005, on free-tier keys) */}
      {allComped && (
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10, padding: '12px 16px', borderRadius: 'var(--r-lg)', background: 'var(--success-subtle)', border: '1px solid var(--success)' }}>
          <Info size={16} color="var(--success)" style={{ flexShrink: 0, marginTop: 1 }} />
          <div style={{ fontSize: 13, color: 'var(--text-2)', lineHeight: 1.5 }}>
            <b style={{ color: 'var(--success)' }}>Nothing billable this cycle.</b>{' '}
            {data?.comped_client_count === data?.client_count
              ? 'Every current client is a free/test tenant on free-tier keys.'
              : 'No client has exceeded its free tier yet.'}{' '}
            Overall billing is the sum of each client below and updates automatically as paying clients onboard.
          </div>
        </div>
      )}

      {/* Headline totals */}
      <div className="stat-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 16 }}>
        {isLoading || !data ? (
          <>
            <SkeletonStatCard />
            <SkeletonStatCard />
            <SkeletonStatCard />
          </>
        ) : (
          <>
            <Stat index={0} icon={<Receipt size={15} />} color="#ec4899" value={`₹${total}`} label="Overall billing — this cycle" sub="sum of all clients" />
            <Stat index={1} icon={<Users size={15} />} color="#6366f1" value={String(data.client_count)} label="Active clients" sub={`${data.billable_client_count} billable · ${data.comped_client_count} free`} />
            <Stat index={2} icon={<Gift size={15} />} color="#10b981" value={formatNumber(data.total_sars_this_cycle)} label="SARs this cycle" sub={`first ${data.free_sars} free · then ${formatINR(data.price_per_sar_inr)}/SAR`} />
          </>
        )}
      </div>

      {/* Per-client breakdown */}
      <div className="card" style={{ padding: 0, animation: 'fadeInUp 300ms ease-out 240ms both' }}>
        <div style={{ padding: '20px 24px 8px' }}>
          <h3 style={{ fontSize: 16, fontWeight: 600, letterSpacing: '-0.01em' }}>Per-client billing</h3>
          <p style={{ fontSize: 12.5, color: 'var(--text-3)', marginTop: 2 }}>
            Each client's bill this cycle. The overall total above is the sum of this column.
          </p>
        </div>
        <div className="tbl-scroll">
          <table className="tbl">
            <thead>
              <tr>
                <th style={{ paddingLeft: 24 }}>Client</th>
                <th>Plan</th>
                <th style={{ textAlign: 'right' }}>SARs</th>
                <th style={{ textAlign: 'right' }}>Billable</th>
                <th style={{ textAlign: 'right', paddingRight: 24 }}>Amount due</th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <SkeletonTableRows rows={3} cols={5} />
              ) : clients.length === 0 ? (
                <tr>
                  <td colSpan={5} style={{ padding: '24px', textAlign: 'center', color: 'var(--text-4)', fontSize: 13 }}>
                    No active clients yet.
                  </td>
                </tr>
              ) : (
                clients.map((c) => (
                  <tr key={c.tenant_id}>
                    <td style={{ paddingLeft: 24 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <span style={{ fontWeight: 500, color: 'var(--text-1)' }}>{c.name}</span>
                        <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--text-4)' }}>{c.tenant_id_public}</span>
                        {c.special_free_access && (
                          <span
                            title={c.note ?? 'Free access'}
                            style={{ fontSize: 10, fontWeight: 600, letterSpacing: '0.03em', color: 'var(--success)', background: 'var(--success-subtle)', borderRadius: 'var(--r-full)', padding: '1px 8px', display: 'inline-flex', alignItems: 'center', gap: 4 }}
                          >
                            <Gift size={10} /> FREE
                          </span>
                        )}
                      </div>
                      {c.note && <div style={{ fontSize: 11.5, color: 'var(--text-4)', marginTop: 3 }}>{c.note}</div>}
                    </td>
                    <td style={{ textTransform: 'capitalize', color: 'var(--text-2)', fontSize: 13 }}>{c.plan}</td>
                    <td style={{ textAlign: 'right', fontFamily: 'var(--font-mono)', fontSize: 13, color: 'var(--text-2)' }}>{c.sars_this_cycle}</td>
                    <td style={{ textAlign: 'right', fontFamily: 'var(--font-mono)', fontSize: 13, color: 'var(--text-3)' }}>{c.billable_sars}</td>
                    <td style={{ textAlign: 'right', paddingRight: 24, fontWeight: 600, fontVariantNumeric: 'tabular-nums', color: c.amount_due_inr > 0 ? 'var(--text-1)' : 'var(--text-4)' }}>
                      {c.special_free_access ? '—' : formatINR(c.amount_due_inr)}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
        <div style={{ padding: '12px 24px', borderTop: '1px solid var(--border-subtle)', display: 'flex', justifyContent: 'space-between', fontSize: 13 }}>
          <span style={{ color: 'var(--text-3)' }}>Overall billing</span>
          <span style={{ fontWeight: 600, fontVariantNumeric: 'tabular-nums' }}>{isLoading ? '' : formatINR(data?.total_amount_due_inr ?? 0)}</span>
        </div>
      </div>
    </div>
  )
}
