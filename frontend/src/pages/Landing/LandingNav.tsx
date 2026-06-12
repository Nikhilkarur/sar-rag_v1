import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ArrowRight, X } from 'lucide-react'
import { AegisShield } from '../../components/AegisLogo'
import { cls } from '../../utils/format'

export default function LandingNav() {
  const [scrolled, setScrolled] = useState(false)
  const [banner, setBanner] = useState(true)

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 24)
    onScroll()
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  return (
    <div className="landing-header">
      {banner && (
        <div className="lnav-banner">
          <a href="#agents" className="lnav-banner-link">
            Meet the Risk Engine — eight typologies, one pipeline
            <ArrowRight size={14} strokeWidth={2} />
          </a>
          <button
            className="lnav-banner-close"
            aria-label="Dismiss announcement"
            onClick={() => setBanner(false)}
          >
            <X size={15} strokeWidth={2} />
          </button>
        </div>
      )}

      <nav className={cls('landing-nav', scrolled && 'scrolled')}>
        <div className="lnav-inner">
          <Link to="/" className="lnav-brand">
            <AegisShield size={20} />
            <span className="lnav-brand-word">
              AEGIS <em>AML</em>
            </span>
          </Link>

          <div className="lnav-links">
            <a href="#capabilities" className="lnav-link">
              Platform
            </a>
            <a href="#how-it-works" className="lnav-link">
              How it works
            </a>
            <a href="#customers" className="lnav-link">
              Customers
            </a>
            <a href="#pricing" className="lnav-link">
              Pricing
            </a>
          </div>

          <div className="lnav-actions">
            <Link to="/login" className="btn-landing btn-landing-secondary btn-landing-sm">
              Sign in
            </Link>
          </div>
        </div>
      </nav>
    </div>
  )
}
