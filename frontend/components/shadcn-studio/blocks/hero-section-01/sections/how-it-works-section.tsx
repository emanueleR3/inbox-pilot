'use client'

import { motion, useInView } from 'framer-motion'
import { useRef } from 'react'
import { Mail, ArrowRight, Brain, Send, CheckCircle2 } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import { useLanguage } from '@/lib/context/language-context'

const steps = [
  {
    number: '01',
    icon: Mail,
    titleKey: 'landing.howItWorks.step01.title',
    descriptionKey: 'landing.howItWorks.step01.description',
    color: 'text-blue-500',
    bgColor: 'bg-blue-500/10',
    borderColor: 'border-blue-500/20',
  },
  {
    number: '02',
    icon: Brain,
    titleKey: 'landing.howItWorks.step02.title',
    descriptionKey: 'landing.howItWorks.step02.description',
    color: 'text-violet-500',
    bgColor: 'bg-violet-500/10',
    borderColor: 'border-violet-500/20',
  },
  {
    number: '03',
    icon: Send,
    titleKey: 'landing.howItWorks.step03.title',
    descriptionKey: 'landing.howItWorks.step03.description',
    color: 'text-emerald-500',
    bgColor: 'bg-emerald-500/10',
    borderColor: 'border-emerald-500/20',
  },
  {
    number: '04',
    icon: CheckCircle2,
    titleKey: 'landing.howItWorks.step04.title',
    descriptionKey: 'landing.howItWorks.step04.description',
    color: 'text-amber-500',
    bgColor: 'bg-amber-500/10',
    borderColor: 'border-amber-500/20',
  },
]

const HowItWorksSection = () => {
  const ref = useRef<HTMLDivElement>(null)
  const isInView = useInView(ref, { once: true, margin: '-100px' })
  const { t } = useLanguage()

  return (
    <section className="relative py-24 sm:py-32 overflow-hidden">
      {/* Background */}
      <div className="absolute inset-0 bg-gradient-to-b from-background via-muted/20 to-background" />

      <div className="relative z-10 mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        {/* Section Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: '-100px' }}
          transition={{ duration: 0.6 }}
          className="mx-auto max-w-2xl text-center mb-20"
        >
          <Badge variant="secondary" className="mb-4 px-4 py-1.5">
            {t('landing.howItWorks.badge')}
          </Badge>
          <h2 className="text-3xl font-bold tracking-tight sm:text-4xl lg:text-5xl">
            {t('landing.howItWorks.title')}{' '}
            <span className="text-slate-500 dark:text-slate-400">{t('landing.howItWorks.titleHighlight')}</span>
          </h2>
          <p className="mt-4 text-lg text-muted-foreground">
            {t('landing.howItWorks.subtitle')}
          </p>
        </motion.div>

        {/* Steps */}
        <div ref={ref} className="relative">
          {/* Connecting line */}
          <div className="absolute left-8 top-0 bottom-0 w-px bg-gradient-to-b from-transparent via-border to-transparent hidden lg:block lg:left-1/2 lg:-translate-x-px" />

          <div className="space-y-16 lg:space-y-0">
            {steps.map((step, index) => (
              <motion.div
                key={step.number}
                initial={{ opacity: 0, x: index % 2 === 0 ? -40 : 40 }}
                animate={isInView ? { opacity: 1, x: 0 } : {}}
                transition={{
                  duration: 0.6,
                  delay: index * 0.15,
                  ease: 'easeOut',
                }}
                className={cn(
                  'relative lg:grid lg:grid-cols-2 lg:gap-16 lg:py-12',
                  index % 2 === 0 ? '' : 'lg:direction-rtl'
                )}
              >
                {/* Content side */}
                <div
                  className={cn(
                    'flex items-start gap-8',
                    index % 2 === 0
                      ? 'lg:justify-end lg:text-right lg:pr-16'
                      : 'lg:col-start-2 lg:direction-ltr lg:pl-16'
                  )}
                >
                  {/* Mobile icon */}
                  <div
                    className={cn(
                      'flex h-16 w-16 shrink-0 items-center justify-center rounded-2xl border lg:hidden',
                      step.bgColor,
                      step.borderColor
                    )}
                  >
                    <step.icon className={cn('h-7 w-7', step.color)} />
                  </div>

                  <div className="max-w-md pt-1">
                    <span
                      className={cn(
                        'text-sm font-mono font-bold tracking-wider',
                        step.color
                      )}
                    >
                      Step {step.number}
                    </span>
                    <h3 className="mt-3 text-xl font-semibold tracking-tight">
                      {t(step.titleKey)}
                    </h3>
                    <p className="mt-2 text-muted-foreground leading-relaxed">
                      {t(step.descriptionKey)}
                    </p>
                  </div>
                </div>

                {/* Center node (desktop) */}
                <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 hidden lg:flex items-center justify-center">
                  <motion.div
                    initial={{ scale: 0 }}
                    animate={isInView ? { scale: 1 } : {}}
                    transition={{
                      duration: 0.4,
                      delay: index * 0.15 + 0.2,
                      type: 'spring',
                      stiffness: 200,
                    }}
                    className={cn(
                      'flex h-16 w-16 items-center justify-center rounded-2xl border-2 bg-background shadow-lg ring-4 ring-background',
                      step.borderColor
                    )}
                  >
                    <step.icon className={cn('h-6 w-6', step.color)} />
                  </motion.div>
                </div>

                {/* Empty side (desktop) */}
                <div
                  className={cn(
                    'hidden lg:block',
                    index % 2 === 0 ? 'lg:col-start-2' : 'lg:col-start-1 lg:row-start-1'
                  )}
                />
              </motion.div>
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}

export default HowItWorksSection
