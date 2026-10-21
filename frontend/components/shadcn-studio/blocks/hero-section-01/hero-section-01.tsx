'use client'

import { useEffect, useRef, useState } from 'react'
import Link from 'next/link'
import Image from 'next/image'
import { ArrowRight } from 'lucide-react'
import gsap from 'gsap'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { InteractiveGridPattern } from '@/components/ui/shadcn-io/interactive-grid-pattern'
import { Particles } from '@/components/ui/shadcn-io/particles'
import { cn } from '@/lib/utils'
import { useLanguage } from '@/lib/context/language-context'

const HeroSection = () => {
  const { t } = useLanguage()
  const [isReady, setIsReady] = useState(false)
  const underlineRef = useRef<SVGPathElement>(null)
  const logoRef = useRef<HTMLDivElement>(null)
  const badgeRef = useRef<HTMLDivElement>(null)
  const titleRef = useRef<HTMLHeadingElement>(null)
  const subtitleRef = useRef<HTMLParagraphElement>(null)
  const buttonRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    // Set ready immediately to show content
    setIsReady(true)

    const ctx = gsap.context(() => {
      // Set initial state for all elements
      gsap.set([logoRef.current, badgeRef.current, titleRef.current, subtitleRef.current, buttonRef.current], {
        opacity: 0,
        y: 20
      })

      // Set initial state for underline
      gsap.set(underlineRef.current, {
        strokeDasharray: 300,
        strokeDashoffset: 300
      })

      // Create timeline for staggered reveal
      const tl = gsap.timeline({ defaults: { ease: 'power2.out' } })

      // Logo
      tl.to(logoRef.current, {
        opacity: 1,
        y: 0,
        duration: 0.4
      }, 0.1)

        // Badge
        .to(badgeRef.current, {
          opacity: 1,
          y: 0,
          duration: 0.4
        }, 0.2)

        // Title
        .to(titleRef.current, {
          opacity: 1,
          y: 0,
          duration: 0.4
        }, 0.35)

        // Underline draws
        .to(underlineRef.current, {
          strokeDashoffset: 0,
          duration: 0.5,
          ease: 'power2.inOut'
        }, 1.3)

        // Subtitle
        .to(subtitleRef.current, {
          opacity: 1,
          y: 0,
          duration: 0.4
        }, 0.5)

        // Button
        .to(buttonRef.current, {
          opacity: 1,
          y: 0,
          duration: 0.4
        }, 0.65)
    })

    return () => ctx.revert()
  }, [])

  return (
    <section className={cn(
      'relative flex min-h-[calc(100dvh-4rem)] flex-1 flex-col justify-center overflow-hidden transition-opacity duration-300',
      isReady ? 'opacity-100' : 'opacity-0'
    )}>
      {/* Interactive Grid Background with 3D perspective */}
      <div className='absolute inset-0 [perspective:550px]'>
        <InteractiveGridPattern
          width={50}
          height={50}
          squares={[60, 60]}
          className={cn(
            'absolute inset-y-[-30%] h-[200%] w-[3000px] left-1/2 -translate-x-1/2',
            '[transform:rotateX(45deg)]',
            '[mask-image:radial-gradient(ellipse_at_center,white_10%,transparent_50%)]'
          )}
          squaresClassName='hover:fill-slate-400/50 dark:hover:fill-slate-500/50'
        />
      </div>

      {/* Particles overlay */}
      <Particles
        className="absolute inset-0 z-[1]"
        quantity={80}
        ease={80}
        color="#64748b"
        size={0.6}
        staticity={40}
      />

      {/* Subtle gradient overlay - pointer-events-none so grid stays interactive */}
      <div className='absolute inset-0 bg-gradient-to-b from-background/90 via-background/50 to-background/90 pointer-events-none' />

      {/* Hero Content - pointer-events-none so grid stays interactive behind text */}
      <div className='relative z-10 mx-auto flex max-w-5xl flex-col items-center gap-2 px-4 text-center sm:px-6 lg:px-8 pointer-events-none mb-16'>

        {/* Logo */}
        <div ref={logoRef} className='opacity-0'>
          <Image
            src='/corretto-avatar.png'
            alt='Corretto'
            width={100}
            height={100}
            className='rounded-2xl'
            priority
          />
        </div>

        {/* Badge */}
        <div ref={badgeRef} className='flex items-center gap-2.5 rounded-full border bg-background/50 backdrop-blur-sm px-2.5 py-1 shadow-sm opacity-0'>
          <Badge className='bg-primary text-primary-foreground'>{t('landing.hero.badge')}</Badge>
          <span className='text-sm text-muted-foreground'>{t('landing.hero.badgeSubtitle')}</span>
        </div>

        {/* Main Headline */}
        <h1 ref={titleRef} className='text-4xl leading-none font-bold tracking-tight sm:text-5xl lg:text-6xl opacity-0'>
          <span className="block mt-5">{t('landing.hero.titleLine1')}</span>
          <span className='relative inline-block mt-1 mb-6'>
            <span className="text-slate-800 dark:text-slate-200">{t('landing.hero.titleLine2')}</span>
            {/* Underline */}
            <svg
              width='100%'
              height='14'
              viewBox='0 0 300 14'
              fill='none'
              xmlns='http://www.w3.org/2000/svg'
              className='absolute -bottom-3 left-0 w-full'
              preserveAspectRatio='none'
            >
              <path
                ref={underlineRef}
                d='M2 12C50 4 100 2 150 2C200 2 250 4 298 12'
                stroke='url(#heroGradient)'
                strokeWidth='4'
                strokeLinecap='round'
              />
              <defs>
                <linearGradient id='heroGradient' x1='0' y1='0' x2='300' y2='0'>
                  <stop stopColor='#64748b' stopOpacity='0.8' />
                  <stop offset='0.5' stopColor='#475569' />
                  <stop offset='1' stopColor='#64748b' stopOpacity='0.8' />
                </linearGradient>
              </defs>
            </svg>
          </span>
        </h1>

        {/* Subheadline */}
        <p ref={subtitleRef} className='max-w-2xl text-base text-muted-foreground sm:text-lg opacity-0 mb-3'>
          {t('landing.hero.subtitle')}
          <span className='hidden sm:inline'>{t('landing.hero.subtitleExtra')}</span>
        </p>

        {/* CTA Button - pointer-events-auto so button is clickable */}
        <div ref={buttonRef} className='opacity-0'>
          <Button size='lg' className='group gap-2 px-8 pointer-events-auto' asChild>
            <Link href='/beta'>
              {t('landing.hero.cta')}
              <ArrowRight className='h-4 w-4 transition-transform group-hover:translate-x-1' />
            </Link>
          </Button>
        </div>
      </div>
    </section>
  )
}

export default HeroSection
