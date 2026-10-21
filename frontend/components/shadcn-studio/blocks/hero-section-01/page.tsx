import HeroSection from '@/components/shadcn-studio/blocks/hero-section-01/hero-section-01'
import Header from '@/components/shadcn-studio/blocks/hero-section-01/header'
import Footer from '@/components/shadcn-studio/blocks/hero-section-01/footer'
import FeaturesSection from '@/components/shadcn-studio/blocks/hero-section-01/sections/features-section'
import HowItWorksSection from '@/components/shadcn-studio/blocks/hero-section-01/sections/how-it-works-section'
import StatsSection from '@/components/shadcn-studio/blocks/hero-section-01/sections/stats-section'
import ComparisonSection from '@/components/shadcn-studio/blocks/hero-section-01/sections/comparison-section'
// import TestimonialsSection from '@/components/shadcn-studio/blocks/hero-section-01/sections/testimonials-section'
import FAQSection from '@/components/shadcn-studio/blocks/hero-section-01/sections/faq-section'
import CTASection from '@/components/shadcn-studio/blocks/hero-section-01/sections/cta-section'

const LandingPage = () => {
  return (
    <div className='relative min-h-screen flex flex-col'>
      {/* Header Section */}
      <Header />

      {/* Main Content */}
      <main className='flex flex-col flex-1'>
        {/* Hero — first impression with animated particles & grid */}
        <HeroSection />

        {/* Features — 6 core capabilities */}
        <FeaturesSection />

        {/* Stats — social proof with animated counters */}
        <StatsSection />

        {/* How It Works — 4-step onboarding timeline */}
        <HowItWorksSection />

        {/* Comparison — Corretto vs traditional tools */}
        <ComparisonSection />

        {/* Testimonials — real user stories */}
        {/* <TestimonialsSection /> */}

        {/* FAQ — address objections */}
        <FAQSection />

        {/* Final CTA — convert */}
        <CTASection />
      </main>

      {/* Footer Section */}
      <Footer />
    </div>
  )
}

export default LandingPage
