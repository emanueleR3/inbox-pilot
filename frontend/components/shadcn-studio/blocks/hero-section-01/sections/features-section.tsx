'use client'

import { useRef } from 'react'
import { Mail, Calendar, Bot, Zap, Shield, BarChart3 } from 'lucide-react'
import { motion, useInView } from 'framer-motion'

import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import { useLanguage } from '@/lib/context/language-context'

const features = [
  {
    icon: Mail,
    titleKey: 'landing.features.smartTriage.title',
    descriptionKey: 'landing.features.smartTriage.description',
    badgeKey: 'landing.features.smartTriage.badge',
    gradient: 'from-blue-500/10 to-blue-600/5',
    iconColor: 'text-blue-500',
  },
  {
    icon: Bot,
    titleKey: 'landing.features.autoResponses.title',
    descriptionKey: 'landing.features.autoResponses.description',
    badgeKey: 'landing.features.autoResponses.badge',
    gradient: 'from-violet-500/10 to-violet-600/5',
    iconColor: 'text-violet-500',
  },
  {
    icon: Calendar,
    titleKey: 'landing.features.calendarIntel.title',
    descriptionKey: 'landing.features.calendarIntel.description',
    badgeKey: 'landing.features.calendarIntel.badge',
    gradient: 'from-emerald-500/10 to-emerald-600/5',
    iconColor: 'text-emerald-500',
  },
  {
    icon: Zap,
    titleKey: 'landing.features.workflow.title',
    descriptionKey: 'landing.features.workflow.description',
    badgeKey: 'landing.features.workflow.badge',
    gradient: 'from-amber-500/10 to-amber-600/5',
    iconColor: 'text-amber-500',
  },
  {
    icon: BarChart3,
    titleKey: 'landing.features.analytics.title',
    descriptionKey: 'landing.features.analytics.description',
    badgeKey: 'landing.features.analytics.badge',
    gradient: 'from-pink-500/10 to-pink-600/5',
    iconColor: 'text-pink-500',
  },
  {
    icon: Shield,
    titleKey: 'landing.features.security.title',
    descriptionKey: 'landing.features.security.description',
    badgeKey: 'landing.features.security.badge',
    gradient: 'from-red-500/10 to-orange-600/5',
    iconColor: 'text-red-500',
  },
]

const containerVariants = {
  hidden: {},
  visible: {
    transition: {
      staggerChildren: 0.1,
    },
  },
}

const cardVariants = {
  hidden: { opacity: 0, y: 30 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.5, ease: 'easeOut' },
  },
}

const FeaturesSection = () => {
  const ref = useRef<HTMLDivElement>(null)
  const isInView = useInView(ref, { once: true, margin: '-100px' })
  const { t } = useLanguage()

  return (
    <section className="relative py-24 sm:py-32 overflow-hidden">
      {/* Subtle background gradient */}
      <div className="absolute inset-0 bg-gradient-to-b from-background via-muted/30 to-background" />

      <div className="relative z-10 mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        {/* Section Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: '-100px' }}
          transition={{ duration: 0.6 }}
          className="mx-auto max-w-2xl text-center mb-16"
        >
          <Badge variant="secondary" className="mb-4 px-4 py-1.5">
            {t('landing.features.badge')}
          </Badge>
          <h2 className="text-3xl font-bold tracking-tight sm:text-4xl lg:text-5xl">
            {t('landing.features.title')}{' '}
            <span className="text-slate-500 dark:text-slate-400">
              {t('landing.features.titleHighlight')}
            </span>
          </h2>
          <p className="mt-4 text-lg text-muted-foreground">
            {t('landing.features.subtitle')}
          </p>
        </motion.div>

        {/* Feature Cards Grid */}
        <motion.div
          ref={ref}
          variants={containerVariants}
          initial="hidden"
          animate={isInView ? 'visible' : 'hidden'}
          className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3"
        >
          {features.map((feature, index) => (
            <motion.div key={feature.titleKey} variants={cardVariants}>
              <Card
                className={cn(
                  'group relative h-full min-h-[140px] overflow-hidden border border-border/50 bg-card/50 backdrop-blur-sm transition-all duration-300',
                  'hover:border-border hover:shadow-lg hover:shadow-slate-200/50 dark:hover:shadow-slate-900/50',
                  'hover:-translate-y-1'
                )}
              >
                {/* Gradient overlay on hover */}
                <div
                  className={cn(
                    'absolute inset-0 bg-gradient-to-br opacity-0 transition-opacity duration-300 group-hover:opacity-100',
                    feature.gradient
                  )}
                />

                <CardContent className="relative p-6">
                  <div className="flex items-start gap-4">
                    <div
                      className={cn(
                        'flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-muted/80 transition-colors duration-300',
                        'group-hover:bg-background/80'
                      )}
                    >
                      <feature.icon
                        className={cn('h-6 w-6', feature.iconColor)}
                      />
                    </div>
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <h3 className="font-semibold tracking-tight">
                          {t(feature.titleKey)}
                        </h3>
                        <Badge
                          variant="outline"
                          className="text-[10px] px-1.5 py-0"
                        >
                          {t(feature.badgeKey)}
                        </Badge>
                      </div>
                      <p className="text-sm text-muted-foreground leading-relaxed">
                        {t(feature.descriptionKey)}
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </section>
  )
}

export default FeaturesSection
