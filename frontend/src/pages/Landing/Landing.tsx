import HeroSection from './sections/HeroSection'
import PipelineSection from './sections/PipelineSection'
import FeaturesSection from './sections/FeaturesSection'
import StatsSection from './sections/StatsSection'
import CtaSection from './sections/CtaSection'
import LandingNav from './LandingNav'
import LandingFooter from './LandingFooter'
import './Landing.css'

export default function Landing() {
  return (
    <div className="landing-root">
      <LandingNav />
      <HeroSection />
      <PipelineSection />
      <FeaturesSection />
      <StatsSection />
      <CtaSection />
      <LandingFooter />
    </div>
  )
}
