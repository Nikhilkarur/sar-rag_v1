import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { AegisShield } from '../../components/AegisLogo'
import { cls } from '../../utils/format'

export default function LandingNav() {
  const [scrolled, setScrolled] = useState(false)

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 40)
    onScroll()
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  return (
    <nav className={cls('landing-nav', scrolled && 'scrolled')}>
      <Link to="/" style={{ display: 'inline-flex', alignItems: 'center', gap: 8, textDecoration: 'none' }}>
        <AegisShield size={22} />
        <span style={{ fontSize: 15, fontWeight: 700, letterSpacing: '-0.01em' }}>
          <span style={{ color: 'var(--text-1)' }}>AEGIS</span>{' '}
          <span style={{ color: 'var(--accent)' }}>AML</span>
        </span>
      </Link>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <Link
          to="/login"
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            height: 28,
            padding: '0 10px',
            borderRadius: 'var(--r-md)',
            fontSize: 13,
            fontWeight: 500,
            color: 'var(--text-2)',
            textDecoration: 'none',
            transition: 'background var(--t-fast), color var(--t-fast)',
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.background = 'var(--bg-elevated)'
            e.currentTarget.style.color = 'var(--text-1)'
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.background = 'transparent'
            e.currentTarget.style.color = 'var(--text-2)'
          }}
        >
          Sign In
        </Link>
        <Link
          to="/signup"
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            height: 28,
            padding: '0 12px',
            borderRadius: 'var(--r-md)',
            fontSize: 13,
            fontWeight: 500,
            background: 'var(--accent)',
            color: '#fff',
            textDecoration: 'none',
            transition: 'background var(--t-fast)',
          }}
          onMouseEnter={(e) => (e.currentTarget.style.background = 'var(--accent-hover)')}
          onMouseLeave={(e) => (e.currentTarget.style.background = 'var(--accent)')}
        >
          Request Access →
        </Link>
      </div>
    </nav>
  )
}
