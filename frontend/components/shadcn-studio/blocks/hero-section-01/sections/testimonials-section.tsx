'use client'

import { useRef, useEffect } from 'react'
import { Star, Quote } from 'lucide-react'
import gsap from 'gsap'

import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { cn } from '@/lib/utils'
import { useLanguage } from '@/lib/context/language-context'

const testimonials = [
  {
    name: 'Ferdinando Del Vecchio',
    role: 'Dev',
    company: 'Corretto',
    avatar: null,
    initials: 'FDV',
    quote:
      'The AI-powered email triage has fundamentally transformed how our team operates. What used to take hours of manual sorting now happens instantly with remarkable accuracy.',
    rating: 5,
    color: 'bg-blue-500',
  },
  {
    name: 'Marco Donatucci',
    role: 'Dev',
    company: 'Corretto',
    avatar: null,
    initials: 'MD',
    quote:
      'Our productivity metrics improved by 40% within the first month. The intelligent scheduling and automated follow-ups ensure nothing falls through the cracks.',
    rating: 5,
    color: 'bg-violet-500',
  },
  {
    name: 'Emanuele Romano',
    role: 'Dev',
    company: 'Corretto',
    avatar: null,
    initials: 'ER',
    quote:
      'The intuitive interface made onboarding seamless. Within days, Corretto learned our communication patterns and started drafting responses that genuinely sound like us.',
    rating: 5,
    color: 'bg-emerald-500',
  },
  {
    name: 'Loris Catalano',
    role: 'Dev',
    company: 'Corretto',
    avatar: null,
    initials: 'LC',
    quote:
      'Enterprise-grade security with consumer-grade simplicity. We trust Corretto with sensitive communications knowing our data is protected by industry-leading standards.',
    rating: 5,
    color: 'bg-amber-500',
  },
]

const TestimonialsSection = () => {
  const containerRef = useRef<HTMLDivElement>(null)
  const trackRef = useRef<HTMLDivElement>(null)
  const animationRef = useRef<gsap.core.Tween | null>(null)
  const { t } = useLanguage()

  useEffect(() => {
    const track = trackRef.current
    if (!track) return

    // Calculate single set width
    const cards = track.querySelectorAll('.testimonial-card')
    const gap = 24 // gap-6 = 1.5rem = 24px
    let singleSetWidth = 0
    cards.forEach((card, index) => {
      if (index < testimonials.length) {
        singleSetWidth += (card as HTMLElement).offsetWidth + gap
      }
    })

    // Create infinite scroll animation
    animationRef.current = gsap.to(track, {
      x: -singleSetWidth,
      duration: 30,
      ease: 'none',
      repeat: -1,
      modifiers: {
        x: gsap.utils.unitize((x) => parseFloat(x) % singleSetWidth),
      },
    })

    // Pause on hover
    const handleMouseEnter = () => animationRef.current?.pause()
    const handleMouseLeave = () => animationRef.current?.resume()

    track.addEventListener('mouseenter', handleMouseEnter)
    track.addEventListener('mouseleave', handleMouseLeave)

    return () => {
      animationRef.current?.kill()
      track.removeEventListener('mouseenter', handleMouseEnter)
      track.removeEventListener('mouseleave', handleMouseLeave)
    }
  }, [])

  // Duplicate testimonials for seamless loop
  const duplicatedTestimonials = [...testimonials, ...testimonials, ...testimonials]

  return (
    <section className="relative py-24 sm:py-32 overflow-hidden">
      <div className="absolute inset-0 bg-gradient-to-b from-background via-muted/20 to-background" />

      <div className="relative z-10 mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        {/* Section Header */}
        <div className="mx-auto max-w-2xl text-center mb-16">
          <Badge variant="secondary" className="mb-4 px-4 py-1.5">
            {t('landing.testimonials.badge')}
          </Badge>
          <h2 className="text-3xl font-bold tracking-tight sm:text-4xl lg:text-5xl">
            {t('landing.testimonials.title')}{' '}
            <span className="text-slate-500 dark:text-slate-400">
              {t('landing.testimonials.titleHighlight')}
            </span>
          </h2>
          <p className="mt-4 text-lg text-muted-foreground">
            {t('landing.testimonials.subtitle')}
          </p>
        </div>

        {/* Testimonials Carousel */}
        <div
          ref={containerRef}
          className="relative overflow-hidden"
        >
          {/* Gradient masks for smooth fade effect */}
          <div className="absolute left-0 top-0 bottom-0 w-24 bg-gradient-to-r from-background to-transparent z-10 pointer-events-none" />
          <div className="absolute right-0 top-0 bottom-0 w-24 bg-gradient-to-l from-background to-transparent z-10 pointer-events-none" />

          <div
            ref={trackRef}
            className="flex gap-6"
            style={{ width: 'max-content' }}
          >
            {duplicatedTestimonials.map((testimonial, index) => (
              <Card
                key={`${testimonial.name}-${index}`}
                className="testimonial-card group relative w-[350px] shrink-0 overflow-hidden border-border/50 bg-card/50 backdrop-blur-sm hover:border-border hover:shadow-lg transition-all duration-300"
              >
                <CardContent className="p-6 flex flex-col h-full">
                  {/* Quote icon */}
                  <Quote className="h-8 w-8 text-muted-foreground/20 mb-4 rotate-180" />

                  {/* Quote */}
                  <p className="text-sm leading-relaxed text-foreground/90 flex-1">
                    &ldquo;{testimonial.quote}&rdquo;
                  </p>

                  {/* Rating */}
                  <div className="flex gap-0.5 mt-4 mb-4">
                    {Array.from({ length: testimonial.rating }).map((_, i) => (
                      <Star
                        key={i}
                        className="h-4 w-4 fill-amber-400 text-amber-400"
                      />
                    ))}
                  </div>

                  {/* Author */}
                  <div className="flex items-center gap-3 pt-4 border-t border-border/50">
                    <div
                      className={cn(
                        'flex h-10 w-10 items-center justify-center rounded-full text-white text-sm font-semibold shrink-0',
                        testimonial.color
                      )}
                    >
                      {testimonial.initials}
                    </div>
                    <div>
                      <p className="text-sm font-medium">
                        {testimonial.name}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {testimonial.role}, {testimonial.company}
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}

export default TestimonialsSection
