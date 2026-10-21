'use client'

import Link from 'next/link'
import { ArrowLeft } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { ThemeLanguageSwitcher } from '@/components/theme-language-switcher'
import { useLanguage } from '@/lib/context/language-context'
import Logo from '@/components/shadcn-studio/logo'

const termsOfServiceIT = `
## 1. Oggetto

I presenti Termini regolano l'utilizzo della piattaforma Corretto.

## 2. Natura del servizio

Corretto fornisce una piattaforma tecnologica. Non garantisce risultati specifici né sostituisce valutazioni umane.

## 3. Obblighi del Cliente

Il Cliente:
- È Titolare del trattamento
- Garantisce la liceità dei dati
- Fornisce informative e basi giuridiche

## 4. Uso lecito

È vietato usare il servizio per:
- Attività illecite
- Violazioni privacy
- Trattamenti non autorizzati

## 5. Sub-fornitori

Corretto può avvalersi di sub-responsabili selezionati.

## 6. Responsabilità

La responsabilità di Corretto è limitata nei limiti di legge. Nessuna responsabilità per contenuti forniti dal Cliente.

## 7. SLA e disponibilità

Il servizio è fornito "as is" con obiettivi di continuità.

## 8. Recesso

Ciascuna parte può recedere secondo contratto.

## 9. Legge applicabile

Legge italiana, foro esclusivo di Torino.
`

const termsOfServiceEN = `
## 1. Scope

These Terms govern the use of the Corretto platform.

## 2. Service Nature

Technology platform provided "as is".

## 3. Customer Obligations

Customer acts as Data Controller and ensures lawful use.

## 4. Acceptable Use

No unlawful or privacy-infringing use.

## 5. Sub-processors

Authorized subcontractors may be used.

## 6. Liability

Limited to the maximum extent permitted by law.

## 7. Availability

Best-effort availability, no guarantee of uptime.

## 8. Termination

According to contract terms.

## 9. Governing Law

Italian law; exclusive jurisdiction of Torino.
`

export default function TermsOfServicePage() {
    const { language, t } = useLanguage()
    const content = language === 'it' ? termsOfServiceIT : termsOfServiceEN

    return (
        <div className="min-h-screen bg-background">
            <ThemeLanguageSwitcher />

            {/* Header */}
            <header className="bg-background/80 backdrop-blur-md sticky top-0 z-40 border-b border-border/50">
                <div className="mx-auto flex h-16 max-w-4xl items-center justify-between gap-6 px-4 sm:px-6 lg:px-8">
                    <Link href="/">
                        <Logo className="gap-3" />
                    </Link>
                    <Button variant="ghost" size="sm" asChild>
                        <Link href="/" className="gap-2">
                            <ArrowLeft className="h-4 w-4" />
                            {t('legal.backToHome')}
                        </Link>
                    </Button>
                </div>
            </header>

            {/* Content */}
            <main className="mx-auto max-w-4xl px-4 py-12 sm:px-6 lg:px-8">
                <article className="prose prose-slate dark:prose-invert max-w-none">
                    <h1 className="text-3xl font-bold tracking-tight sm:text-4xl mb-8">
                        {t('legal.termsOfService')}
                    </h1>

                    <div className="whitespace-pre-line text-foreground">
                        {content.split('\n').map((line, index) => {
                            // Handle headers
                            if (line.startsWith('## ')) {
                                return <h2 key={index} className="text-xl font-semibold mt-8 mb-4">{line.replace('## ', '')}</h2>
                            }
                            // Handle list items
                            if (line.startsWith('- ')) {
                                return <li key={index} className="ml-6 list-disc">{line.replace('- ', '')}</li>
                            }
                            // Regular paragraph
                            if (line.trim()) {
                                return <p key={index} className="mb-4">{line}</p>
                            }
                            return null
                        })}
                    </div>
                </article>
            </main>
        </div>
    )
}
