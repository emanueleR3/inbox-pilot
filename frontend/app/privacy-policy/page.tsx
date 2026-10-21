'use client'

import Link from 'next/link'
import { ArrowLeft } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { ThemeLanguageSwitcher } from '@/components/theme-language-switcher'
import { useLanguage } from '@/lib/context/language-context'
import Logo from '@/components/shadcn-studio/logo'

const privacyPolicyIT = `
**Ultimo aggiornamento:** 27/01/2026

## 1. Introduzione

La presente Privacy Policy descrive come Corretto (di seguito "Corretto" o il "Fornitore"), tratta i dati personali nell'ambito della piattaforma SaaS B2B denominata Corretto (la "Piattaforma").

La Piattaforma fornisce strumenti basati su intelligenza artificiale per la gestione delle comunicazioni aziendali (email, chiamate vocali tramite centralino virtuale, calendari, automazioni e analisi semantiche).

Corretto opera prevalentemente in qualità di Responsabile del trattamento ai sensi dell'art. 28 del Regolamento (UE) 2016/679 ("GDPR") rispetto ai dati trattati per conto dei propri clienti aziendali.

## 2. Ruoli nel trattamento
- **Clienti aziendali:** Titolari del trattamento dei dati personali dei propri dipendenti, collaboratori, clienti e contatti.
- **Corretto:** Responsabile del trattamento per i dati trattati tramite la Piattaforma; Titolare autonomo limitatamente ai dati amministrativi, contrattuali, di fatturazione e di utilizzo del servizio.
- **Sub-responsabili:** Fornitori tecnologici selezionati (es. provider cloud, AI, infrastruttura), nominati tramite accordi conformi all'art. 28 GDPR.

## 3. Tipologie di dati trattati

A seconda della configurazione scelta dal Cliente, Corretto può trattare:
- Dati identificativi e di contatto
- Contenuti di email aziendali
- Metadati di comunicazione
- Trascrizioni di chiamate vocali
- Registrazioni audio (se abilitate)
- Dati di calendario e appuntamenti
- Log di utilizzo e sicurezza

Il trattamento può includere incidentalmente dati particolari ex art. 9 GDPR, che vengono gestiti con misure rafforzate di sicurezza e minimizzazione.

## 4. Finalità del trattamento

I dati personali sono trattati esclusivamente per:
- Erogazione e gestione del servizio
- Analisi automatizzata delle comunicazioni su istruzione del Cliente
- Miglioramento delle prestazioni del servizio
- Sicurezza, prevenzione abusi e incidenti
- Adempimenti legali e contrattuali

## 5. Base giuridica

A seconda dei casi:
- Esecuzione di un contratto (art. 6.1.b GDPR)
- Legittimo interesse del Titolare (art. 6.1.f GDPR)
- Obblighi di legge (art. 6.1.c GDPR)
- Consenso, ove richiesto (es. chiamate automatizzate promozionali)

## 6. Trattamenti automatizzati e AI

La Piattaforma utilizza sistemi di intelligenza artificiale per analisi, classificazione, sintesi e generazione di contenuti. Tali processi:
- Avvengono sotto controllo del Cliente
- Non producono decisioni giuridiche automatizzate senza intervento umano
- Possono essere disattivati o limitati dal Cliente

## 7. Conservazione dei dati

I dati sono conservati per il tempo strettamente necessario alle finalità del servizio e secondo le policy configurabili dal Cliente. In assenza di istruzioni diverse:
- Email e contenuti: max 24 mesi
- Trascrizioni vocali: max 6 mesi
- Log tecnici: max 12 mesi

## 8. Sicurezza

Corretto adotta misure tecniche e organizzative adeguate, tra cui:
- Crittografia dei dati a riposo e in transito
- Segregazione per tenant
- Controlli di accesso e logging
- Audit periodici

## 9. Trasferimenti extra-UE

Qualora i dati vengano trasferiti fuori dallo SEE:
- Sono adottate Clausole Contrattuali Standard (SCC)
- Sono implementate misure supplementari
- È privilegiata la localizzazione dei dati in UE

## 10. Diritti degli interessati

Gli interessati possono esercitare i diritti previsti dagli artt. 15-22 GDPR tramite il Titolare del trattamento (Cliente). Corretto fornisce piena cooperazione.

## 11. Contatti

Email: [contact@example.com](mailto:contact@example.com)

## 12. Utilizzo dei Dati Utente Google

L'utilizzo e il trasferimento ad altre app di qualsiasi informazione ricevuta dalle API di Google aderiranno alla [Google API Services User Data Policy](https://developers.google.com/terms/api-services-user-data-policy), inclusi i requisiti di "Limited Use".

Nello specifico:
- **Accesso ai dati:** previa autorizzazione dell'utente, l'applicazione accede ai dati di Gmail (per lettura, invio e gestione bozze) e Google Calendar (per lettura e creazione eventi).
- **Utilizzo:** tali dati sono utilizzati esclusivamente per fornire le funzionalità di analisi, automazione delle risposte e gestione del calendario richieste dall'utente all'interno della Piattaforma.
- **Condivisione:** i dati non vengono trasferiti a terzi se non per le finalità essenziali del servizio (es. modelli AI), conformemente alle policy di Google, e non vengono mai venduti.
- **Pubblicità:** i dati dell'utente Google non sono utilizzati per scopi pubblicitari.
`

const privacyPolicyEn = `
**Last updated:** 27/01/2026

## 1. Introduction

This Privacy Policy explains how Corretto ("Corretto" or the "Provider") processes personal data through the Corretto B2B SaaS platform.

Corretto mainly acts as a Data Processor under Article 28 GDPR on behalf of its business customers.

## 2. Roles
- **Customers:** Data Controllers
- **Corretto:** Data Processor; independent Controller for administrative data
- **Sub-processors:** Authorized technology providers

## 3. Categories of Data

Including but not limited to:
- Identification and contact data
- Business email content
- Call transcriptions
- Audio recordings (if enabled)
- Calendars and metadata

## 4. Purposes
- Service provision
- AI-powered communication management
- Security and compliance

## 5. Legal Bases
- Contract performance
- Legitimate interest
- Legal obligations
- Consent where required

## 6. AI Processing

AI systems support content analysis and automation under customer instructions. No solely automated decisions with legal effects are made.

## 7. Data Retention

Configurable by customers; default maximum retention applies.

## 8. Security Measures

Encryption, access controls, segregation, and audits are implemented.

## 9. International Transfers

Transfers outside the EEA rely on SCCs and supplementary safeguards.

## 10. Data Subject Rights

Exercised via the Data Controller. Corretto provides assistance.

## 11. Contact

Email: [contact@example.com](mailto:contact@example.com)

## 12. Google User Data Policy

Corretto's use and transfer to any other app of information received from Google APIs will adhere to the [Google API Services User Data Policy](https://developers.google.com/terms/api-services-user-data-policy), including the Limited Use requirements.

Specifically:
- **Data Access:** Upon user authorization, the application accesses Gmail data (read, send, manage drafts) and Google Calendar data (read, create events).
- **Use:** This data is used exclusively to provide the analysis, response automation, and calendar management features requested by the user within the Platform.
- **Sharing:** Data is not transferred to third parties except for essential service purposes (e.g., AI models), in compliance with Google's policies, and is never sold.
- **Advertising:** Google User Data is not used for advertising purposes.
`

export default function PrivacyPolicyPage() {
    const { language, t } = useLanguage()
    const content = language === 'it' ? privacyPolicyIT : privacyPolicyEn

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
                        {t('legal.privacyPolicy')}
                    </h1>

                    <div className="whitespace-pre-line text-foreground [&_h2]:text-xl [&_h2]:font-semibold [&_h2]:mt-8 [&_h2]:mb-4 [&_ul]:list-disc [&_ul]:pl-6 [&_ul]:my-4 [&_li]:my-1 [&_strong]:font-semibold [&_a]:text-primary [&_a]:underline">
                        {content.split('\n').map((line: string, index: number) => {
                            // Handle headers
                            if (line.startsWith('## ')) {
                                return <h2 key={index} className="text-xl font-semibold mt-8 mb-4">{line.replace('## ', '')}</h2>
                            }
                            // Handle bold text at start
                            if (line.startsWith('**') && line.includes(':**')) {
                                const match = line.match(/\*\*(.+?):\*\*\s*(.*)/)
                                if (match) {
                                    return <p key={index} className="mb-2"><strong>{match[1]}:</strong> {match[2]}</p>
                                }
                            }
                            // Handle list items
                            if (line.startsWith('- ')) {
                                const content = line.replace('- ', '')
                                // Check for bold items
                                if (content.startsWith('**')) {
                                    const match = content.match(/\*\*(.+?):\*\*\s*(.*)/)
                                    if (match) {
                                        return <li key={index} className="ml-6 list-disc"><strong>{match[1]}:</strong> {match[2]}</li>
                                    }
                                }
                                // Handle links
                                if (content.includes('[') && content.includes('](mailto:')) {
                                    const match = content.match(/\[(.+?)\]\(mailto:(.+?)\)/)
                                    if (match) {
                                        return <li key={index} className="ml-6 list-disc"><a href={`mailto:${match[2]}`} className="text-primary underline">{match[1]}</a></li>
                                    }
                                }
                                return <li key={index} className="ml-6 list-disc">{content}</li>
                            }
                            // Handle email links
                            if (line.includes('[') && line.includes('](mailto:')) {
                                const match = line.match(/Email:\s*\[(.+?)\]\(mailto:(.+?)\)/)
                                if (match) {
                                    return <p key={index} className="mt-4">Email: <a href={`mailto:${match[2]}`} className="text-primary underline">{match[1]}</a></p>
                                }
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
