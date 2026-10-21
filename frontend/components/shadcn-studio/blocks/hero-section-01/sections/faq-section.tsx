'use client'

import { motion, useInView } from 'framer-motion'
import { useRef, useState } from 'react'
import { ChevronDown } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import { useLanguage } from '@/lib/context/language-context'

const faqKeys = [
  { questionKey: 'landing.faq.q1', answerKey: 'landing.faq.a1' },
  { questionKey: 'landing.faq.q3', answerKey: 'landing.faq.a3' },
  { questionKey: 'landing.faq.q4', answerKey: 'landing.faq.a4' },
  { questionKey: 'landing.faq.q5', answerKey: 'landing.faq.a5' },
  //{ questionKey: 'landing.faq.q6', answerKey: 'landing.faq.a6' },
]

const FAQItem = ({
  faq,
  index,
  isOpen,
  toggle,
  t,
}: {
  faq: (typeof faqKeys)[0]
  index: number
  isOpen: boolean
  toggle: () => void
  t: (key: string) => string
}) => {
  const contentRef = useRef<HTMLDivElement>(null)

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      transition={{ duration: 0.4, delay: index * 0.05 }}
      className="border-b border-border/50 last:border-b-0"
    >
      <button
        onClick={toggle}
        className="flex w-full items-center justify-between gap-4 py-5 text-left transition-colors hover:text-foreground/80"
      >
        <h3 className="text-base font-medium pr-4">{t(faq.questionKey)}</h3>
        <ChevronDown
          className={cn(
            'h-5 w-5 shrink-0 text-muted-foreground transition-transform duration-300',
            isOpen && 'rotate-180'
          )}
        />
      </button>
      <div
        ref={contentRef}
        className={cn(
          'overflow-hidden transition-all duration-300 ease-in-out',
          isOpen ? 'max-h-[500px] pb-5' : 'max-h-0'
        )}
      >
        <p className="text-sm text-muted-foreground leading-relaxed pr-12">
          {t(faq.answerKey)}
        </p>
      </div>
    </motion.div>
  )
}

const FAQSection = () => {
  const [openIndex, setOpenIndex] = useState<number | null>(0)
  const { t } = useLanguage()

  return (
    <section className="relative py-24 sm:py-32 overflow-hidden">
      <div className="absolute inset-0 bg-gradient-to-b from-background via-muted/20 to-background" />

      <div className="relative z-10 mx-auto max-w-3xl px-4 sm:px-6 lg:px-8">
        {/* Section Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: '-100px' }}
          transition={{ duration: 0.6 }}
          className="text-center mb-16"
        >
          <Badge variant="secondary" className="mb-4 px-4 py-1.5">
            {t('landing.faq.badge')}
          </Badge>
          <h2 className="text-3xl font-bold tracking-tight sm:text-4xl lg:text-5xl">
            {t('landing.faq.title')}{' '}
            <span className="text-slate-500 dark:text-slate-400">
              {t('landing.faq.titleHighlight')}
            </span>
          </h2>
          <p className="mt-4 text-lg text-muted-foreground">
            {t('landing.faq.subtitle')}
          </p>
        </motion.div>

        {/* FAQ Items */}
        <div className="rounded-2xl border border-border/50 bg-card/50 backdrop-blur-sm p-2 sm:p-6">
          {faqKeys.map((faq, index) => (
            <FAQItem
              key={index}
              faq={faq}
              index={index}
              isOpen={openIndex === index}
              toggle={() =>
                setOpenIndex(openIndex === index ? null : index)
              }
              t={t}
            />
          ))}
        </div>
      </div>
    </section>
  )
}

export default FAQSection
