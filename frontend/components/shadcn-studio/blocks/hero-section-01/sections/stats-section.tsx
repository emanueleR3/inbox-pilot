'use client'

import { motion, useInView, AnimatePresence } from 'framer-motion'
import { useRef, useState } from 'react'
import {
  Clock,
  TrendingUp,
  Mail,
  Users,
  ArrowUpRight,
  Sparkles,
} from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { cn } from '@/lib/utils'
import { useLanguage } from '@/lib/context/language-context'

const stats = [
  {
    icon: Clock,
    value: '12+',
    unit: ' ore',
    labelKey: 'landing.stats.hoursSaved.label',
    descriptionKey: 'landing.stats.hoursSaved.description',
    color: 'text-blue-500',
    bgColor: 'bg-blue-500/10',
  },
  {
    icon: Mail,
    value: '95',
    unit: '% delle email',
    labelKey: 'landing.stats.autoCategorized.label',
    descriptionKey: 'landing.stats.autoCategorized.description',
    color: 'text-emerald-500',
    bgColor: 'bg-emerald-500/10',
  },
  {
    icon: TrendingUp,
    value: '21',
    unit: ' volte',
    labelKey: 'landing.stats.fasterResponses.label',
    descriptionKey: 'landing.stats.fasterResponses.description',
    color: 'text-violet-500',
    bgColor: 'bg-violet-500/10',
  },
  {
    icon: Users,
    value: '4',
    unit: '+ utenti',
    labelKey: 'landing.stats.betaUsers.label',
    descriptionKey: 'landing.stats.betaUsers.description',
    color: 'text-amber-500',
    bgColor: 'bg-amber-500/10',
  },
]

const AnimatedCounter = ({
  value,
  unit,
  isInView,
}: {
  value: string
  unit: string
  isInView: boolean
}) => {
  return (
    <span className="tabular-nums">
      <motion.span
        initial={{ opacity: 0, y: 10 }}
        animate={isInView ? { opacity: 1, y: 0 } : {}}
        transition={{ duration: 0.5, delay: 0.3 }}
      >
        {value}
      </motion.span>
      <span className="text-muted-foreground text-2xl sm:text-3xl">
        {unit}
      </span>
    </span>
  )
}

const StatsSection = () => {
  const ref = useRef<HTMLDivElement>(null)
  const isInView = useInView(ref, { once: true, margin: '-80px' })
  const { t } = useLanguage()

  return (
    <section className="relative py-24 sm:py-32 overflow-hidden">
      {/* Background accent */}
      <div className="absolute inset-0">
        <div className="absolute inset-0 bg-gradient-to-b from-muted/50 via-muted/30 to-background" />
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[400px] bg-gradient-to-b from-slate-200/40 dark:from-slate-700/20 rounded-full blur-3xl" />
      </div>

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
            <Sparkles className="h-3 w-3 mr-1" />
            {t('landing.stats.badge')}
          </Badge>
          <h2 className="text-3xl font-bold tracking-tight sm:text-4xl lg:text-5xl">
            {t('landing.stats.title')}{' '}
            <span className="text-slate-500 dark:text-slate-400">
              {t('landing.stats.titleHighlight')}
            </span>
          </h2>
          <p className="mt-4 text-lg text-muted-foreground">
            {t('landing.stats.subtitle')}
          </p>
        </motion.div>

        {/* Stats Grid */}
        <div ref={ref} className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4 ">
          {stats.map((stat, index) => (
            <motion.div
              key={stat.labelKey}
              initial={{ opacity: 0, y: 30, scale: 0.95 }}
              animate={
                isInView ? { opacity: 1, y: 0, scale: 1 } : {}
              }
              transition={{
                duration: 0.5,
                delay: index * 0.1,
                ease: 'easeOut',
              }}
            >
              <Card className="group relative h-full min-h-[180px] overflow-hidden border-border/50 bg-card/80 backdrop-blur-sm hover:border-border hover:shadow-lg transition-all duration-300">
                <CardContent className="p-6">
                  <div
                    className={cn(
                      'flex h-10 w-10 items-center justify-center rounded-lg mb-4 transition-transform duration-300 group-hover:scale-110',
                      stat.bgColor
                    )}
                  >
                    <stat.icon className={cn('h-5 w-5', stat.color)} />
                  </div>

                  <div className="space-y-1">
                    <div className="text-4xl sm:text-5xl font-bold tracking-tight">
                      <AnimatedCounter
                        value={stat.value}
                        unit={stat.unit}
                        isInView={isInView}
                      />
                    </div>
                    <p className="text-sm font-medium">{t(stat.labelKey)}</p>
                    <p className="text-s text-muted-foreground">
                      {t(stat.descriptionKey)}
                    </p>
                  </div>

                  {/* Decorative corner */}
                  <div className="absolute top-0 right-0 w-16 h-16 bg-gradient-to-bl from-muted/40 to-transparent rounded-bl-3xl opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
                </CardContent>
              </Card>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  )
}

export default StatsSection
