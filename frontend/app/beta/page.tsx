'use client'

import Link from 'next/link'
import { ArrowLeft, ArrowRight, Mail, Calendar, Phone, FileText, Check } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '@/components/ui/card'
import { ThemeLanguageSwitcher } from '@/components/theme-language-switcher'
import { useLanguage } from '@/lib/context/language-context'
import Logo from '@/components/shadcn-studio/logo'

const services = [
    {
        icon: Mail,
        titleKey: 'beta.emailManagement',
        descriptionKey: 'beta.emailManagementDesc',
    },
    {
        icon: Calendar,
        titleKey: 'beta.calendar',
        descriptionKey: 'beta.calendarDesc',
    },
    {
        icon: Phone,
        titleKey: 'beta.centralino',
        descriptionKey: 'beta.centralinoDesc',
    },
    {
        icon: FileText,
        titleKey: 'beta.documents',
        descriptionKey: 'beta.documentsDesc',
    },
]

export default function BetaPage() {
    const { t } = useLanguage()

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
            <main className="mx-auto max-w-2xl px-4 py-12 sm:px-6 lg:px-8">
                {/* Title Section */}
                <div className="text-center mb-8">
                    <Badge variant="secondary" className="mb-4">
                        {t('beta.badge')}
                    </Badge>
                    <h1 className="text-3xl font-bold tracking-tight sm:text-4xl mb-3">
                        {t('beta.title')}
                    </h1>
                    <p className="text-muted-foreground text-lg">
                        {t('beta.subtitle')}
                    </p>
                </div>

                {/* Services Card */}
                <Card className="mb-6">
                    <CardHeader>
                        <CardTitle>{t('beta.servicesTitle')}</CardTitle>
                        <CardDescription>{t('beta.servicesSubtitle')}</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        {services.map((service, index) => (
                            <div
                                key={index}
                                className="flex items-start gap-4 p-3 rounded-lg border bg-muted/30"
                            >
                                <div className="flex-shrink-0 w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
                                    <service.icon className="h-5 w-5 text-primary" />
                                </div>
                                <div className="flex-1 min-w-0">
                                    <h3 className="font-medium text-sm">
                                        {t(service.titleKey)}
                                    </h3>
                                    <p className="text-xs text-muted-foreground mt-0.5">
                                        {t(service.descriptionKey)}
                                    </p>
                                </div>
                                <Check className="h-4 w-4 text-primary flex-shrink-0 mt-1" />
                            </div>
                        ))}
                    </CardContent>
                    <CardFooter className="flex-col gap-4">
                        <Button
                            size="lg"
                            className="w-full group gap-2"
                            asChild
                        >
                            <Link href="/login?mode=register">
                                {t('beta.getStarted')}
                                <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
                            </Link>
                        </Button>
                        <p className="text-xs text-muted-foreground text-center">
                            {t('beta.footerText')}
                        </p>
                    </CardFooter>
                </Card>
            </main>
        </div>
    )
}
