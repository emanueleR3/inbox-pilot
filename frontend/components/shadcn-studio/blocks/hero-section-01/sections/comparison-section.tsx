'use client'

import { motion, useInView } from 'framer-motion'
import { useRef } from 'react'
import { Check, X, ArrowRight, Sparkles } from 'lucide-react'
import Link from 'next/link'
import { SiGmail, SiGooglecalendar } from 'react-icons/si'
import { MdEmail, MdOutlineMail } from 'react-icons/md'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { cn } from '@/lib/utils'
import { useLanguage } from '@/lib/context/language-context'

// Integration Logos usando React Icons
const GmailLogo = () => (
  <SiGmail className="h-6 w-6 text-[#EA4335]" />
)

const OutlookLogo = () => (
  <svg className="h-6 w-6" viewBox="0 0 24 24" fill="none">
    <path d="M24 7.387v9.226a3.387 3.387 0 01-3.387 3.387h-6.84V5.419l10.227-2.032v4z" fill="#0364B8" />
    <path d="M13.773 3.387v17.226H3.387A3.387 3.387 0 010 17.226V6.774a3.387 3.387 0 013.387-3.387h10.386z" fill="#0078D4" />
    <path d="M13.773 5.419v14.194H20.613a3.387 3.387 0 003.387-3.387V7.387l-10.227-1.968z" fill="#28A8EA" />
    <ellipse cx="6.887" cy="12" rx="3.5" ry="4.5" fill="#0078D4" />
    <ellipse cx="6.887" cy="12" rx="2.5" ry="3.2" fill="#fff" />
  </svg>
)

const GoogleCalendarLogo = () => (
  <SiGooglecalendar className="h-6 w-6 text-[#4285F4]" />
)

const Microsoft365Logo = () => (
  <svg className="h-6 w-6" viewBox="0 0 24 24" fill="none">
    <rect x="1" y="1" width="10" height="10" fill="#F25022" />
    <rect x="13" y="1" width="10" height="10" fill="#7FBA00" />
    <rect x="1" y="13" width="10" height="10" fill="#00A4EF" />
    <rect x="13" y="13" width="10" height="10" fill="#FFB900" />
  </svg>
)

const IMAPLogo = () => (
  <MdEmail className="h-6 w-6 text-slate-600 dark:text-slate-400" />
)

const SMTPLogo = () => (
  <MdOutlineMail className="h-6 w-6 text-blue-600 dark:text-blue-400" />
)

const comparisonData = [
  { featureKey: 'landing.comparison.emailCategorization', corretto: true, traditional: false },
  { featureKey: 'landing.comparison.aiDraftReplies', corretto: true, traditional: false },
  { featureKey: 'landing.comparison.calendarIntegration', corretto: true, traditional: true },
  { featureKey: 'landing.comparison.learnsStyle', corretto: true, traditional: false },
  { featureKey: 'landing.comparison.workflowAutomation', corretto: true, traditional: false },
  { featureKey: 'landing.comparison.realTimeAnalytics', corretto: true, traditional: false },
  { featureKey: 'landing.comparison.crossPlatform', corretto: true, traditional: true },
  { featureKey: 'landing.comparison.zeroManualSorting', corretto: true, traditional: false },
]

const integrations = [
  { name: 'Gmail', logo: <GmailLogo /> },
  { name: 'Outlook', logo: <OutlookLogo /> },
  { name: 'Google Calendar', logo: <GoogleCalendarLogo /> },
  { name: 'Microsoft 365', logo: <Microsoft365Logo /> },
  { name: 'IMAP', logo: <IMAPLogo /> },
  { name: 'SMTP', logo: <SMTPLogo /> },
]

const ComparisonSection = () => {
  const ref = useRef<HTMLDivElement>(null)
  const isInView = useInView(ref, { once: true, margin: '-80px' })
  const { t } = useLanguage()

  return (
    <section className="relative py-24 sm:py-32 overflow-hidden">
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
            {t('landing.comparison.badge')}
          </Badge>
          <h2 className="text-3xl font-bold tracking-tight sm:text-4xl lg:text-5xl">
            {t('landing.comparison.title')}{' '}
            <span className="text-slate-500 dark:text-slate-400">
              {t('landing.comparison.titleHighlight')}
            </span>
          </h2>
          <p className="mt-4 text-lg text-muted-foreground">
            {t('landing.comparison.subtitle')}
          </p>
        </motion.div>

        <div ref={ref} className="grid gap-12 lg:grid-cols-2 items-start">
          {/* Inline Comparison List */}
          <motion.div
            initial={{ opacity: 0, x: -30 }}
            animate={isInView ? { opacity: 1, x: 0 } : {}}
            transition={{ duration: 0.6 }}
          >
            <Card className="overflow-hidden border-border/50 bg-card/50 backdrop-blur-sm">
              <CardContent className="p-6">
                <div className="space-y-4">
                  {comparisonData.map((row, index) => (
                    <motion.div
                      key={row.featureKey}
                      initial={{ opacity: 0, y: 10 }}
                      animate={isInView ? { opacity: 1, y: 0 } : {}}
                      transition={{ duration: 0.3, delay: index * 0.05 }}
                      className="flex items-center gap-4 p-4 rounded-xl bg-muted/30 hover:bg-muted/50 transition-colors"
                    >
                      {/* Feature Name */}
                      <span className="flex-1 text-sm font-medium">
                        {t(row.featureKey)}
                      </span>

                      {/* Corretto */}
                      <div className={cn(
                        "flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium",
                        row.corretto
                          ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400"
                          : "bg-muted text-muted-foreground"
                      )}>
                        {row.corretto ? (
                          <Check className="h-3.5 w-3.5" />
                        ) : (
                          <X className="h-3.5 w-3.5" />
                        )}
                        <span className="hidden sm:inline">Corretto</span>
                      </div>

                      {/* VS Divider */}
                      <span className="text-xs text-muted-foreground font-medium">vs</span>

                      {/* Traditional */}
                      <div className={cn(
                        "flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium",
                        row.traditional
                          ? "bg-slate-500/10 text-slate-600 dark:text-slate-400"
                          : "bg-red-500/10 text-red-600 dark:text-red-400"
                      )}>
                        {row.traditional ? (
                          <Check className="h-3.5 w-3.5" />
                        ) : (
                          <X className="h-3.5 w-3.5" />
                        )}
                        <span className="hidden sm:inline">{t('landing.comparison.traditional')}</span>
                      </div>
                    </motion.div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </motion.div>

          {/* Integrations + CTA */}
          <motion.div
            initial={{ opacity: 0, x: 30 }}
            animate={isInView ? { opacity: 1, x: 0 } : {}}
            transition={{ duration: 0.6, delay: 0.15 }}
            className="space-y-8"
          >
            {/* Integrations */}
            <Card className="border-border/50 bg-card/50 backdrop-blur-sm">
              <CardContent className="p-6 sm:p-8">
                <h3 className="text-lg font-semibold mb-2">
                  {t('landing.comparison.integrations.title')}
                </h3>
                <p className="text-sm text-muted-foreground mb-6">
                  {t('landing.comparison.integrations.subtitle')}
                </p>

                <div className="grid grid-cols-2 gap-4">
                  {integrations.map((integration, index) => (
                    <motion.div
                      key={integration.name}
                      initial={{ opacity: 0, scale: 0.9 }}
                      animate={
                        isInView ? { opacity: 1, scale: 1 } : {}
                      }
                      transition={{
                        duration: 0.4,
                        delay: 0.3 + index * 0.08,
                      }}
                      className="flex items-center gap-3 rounded-xl border border-border/50 bg-background/50 p-4 transition-colors hover:bg-muted/50"
                    >
                      <div className="flex-shrink-0">{integration.logo}</div>
                      <span className="text-sm font-medium">
                        {integration.name}
                      </span>
                    </motion.div>
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* Mini CTA */}
            <Card className="border-border/50 bg-gradient-to-br from-primary/5 to-primary/[0.02] backdrop-blur-sm overflow-hidden">
              <CardContent className="p-6 sm:p-8">
                <h3 className="text-lg font-semibold mb-2">
                  {t('landing.comparison.cta.title')}
                </h3>
                <p className="text-sm text-muted-foreground mb-6">
                  {t('landing.comparison.cta.subtitle')}
                </p>
                <Button className="group gap-2 w-full sm:w-auto" asChild>
                  <Link href="/login?mode=register">
                    {t('landing.comparison.cta.button')}
                    <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
                  </Link>
                </Button>
              </CardContent>
            </Card>
          </motion.div>
        </div>
      </div>
    </section>
  )
}

export default ComparisonSection
