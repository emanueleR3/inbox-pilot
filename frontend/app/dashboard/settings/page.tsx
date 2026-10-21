'use client'

import { Suspense, useEffect, useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import Link from 'next/link'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { useAuth } from '@/lib/context/auth-context'
import { useLanguage } from '@/lib/context/language-context'
import { Skeleton } from '@/components/ui/skeleton'
import { User, Briefcase, Sliders, ArrowLeft } from 'lucide-react'
import { Button } from '@/components/ui/button'

import { ProfileSettings } from '@/components/settings/profile-settings'
import { ServiceSettingsPanel } from '@/components/settings/service-settings'
import { SubscriptionSettingsPanel } from '@/components/settings/subscription-settings'

function SettingsContent() {
    const router = useRouter()
    const searchParams = useSearchParams()
    const { isLoading, isAuthenticated } = useAuth()
    const { t } = useLanguage()
    const [isReady, setIsReady] = useState(false)

    // Get initial tab from URL params or default to 'profile'
    const initialTab = searchParams.get('tab') || 'profile'
    const [activeTab, setActiveTab] = useState(initialTab)

    // Update URL when tab changes
    const handleTabChange = (tab: string) => {
        setActiveTab(tab)
        const newParams = new URLSearchParams(searchParams.toString())
        newParams.set('tab', tab)
        router.replace(`/dashboard/settings?${newParams.toString()}`, { scroll: false })
    }

    // Redirect to login if not authenticated
    useEffect(() => {
        if (!isLoading && !isAuthenticated) {
            router.push('/login')
        }
    }, [isLoading, isAuthenticated, router])

    // Set ready state after auth check
    useEffect(() => {
        if (!isLoading && isAuthenticated) {
            const timer = setTimeout(() => setIsReady(true), 100)
            return () => clearTimeout(timer)
        }
    }, [isLoading, isAuthenticated])

    if (isLoading || !isReady) {
        return (
            <div className="flex bg-background p-8 justify-center">
                <div className="space-y-4 w-full max-w-md">
                    <Skeleton className="h-8 w-48" />
                    <Skeleton className="h-4 w-32" />
                    <div className="space-y-2 mt-8">
                        <Skeleton className="h-12 w-full" />
                        <Skeleton className="h-64 w-full" />
                    </div>
                </div>
            </div>
        )
    }

    return (
        <div className="container mx-auto py-8 px-4 max-w-5xl animate-in fade-in duration-300">
            {/* Header */}
            <div className="mb-8 flex flex-col gap-4">
                <Link href="/dashboard" passHref>
                    <Button variant="ghost" size="sm" className="w-fit gap-2 -ml-2 text-muted-foreground hover:text-foreground">
                        <ArrowLeft className="h-4 w-4" />
                        {t('common.back')}
                    </Button>
                </Link>
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">{t('settings.title')}</h1>
                    <p className="text-muted-foreground mt-2">{t('settings.subtitle')}</p>
                </div>
            </div>

            {/* Tabbed Content */}
            <Tabs value={activeTab} onValueChange={handleTabChange} className="w-full space-y-6">
                <TabsList className="grid w-full grid-cols-3 h-auto p-1 bg-muted/50 rounded-lg">
                    <TabsTrigger value="profile" className="flex items-center gap-2 py-2.5">
                        <User className="h-4 w-4" />
                        <span className="hidden sm:inline">{t('settings.profile')}</span>
                    </TabsTrigger>
                    <TabsTrigger value="service" className="flex items-center gap-2 py-2.5">
                        <Briefcase className="h-4 w-4" />
                        <span className="hidden sm:inline">{t('settings.service')}</span>
                    </TabsTrigger>
                    <TabsTrigger value="ai" className="flex items-center gap-2 py-2.5">
                        <Sliders className="h-4 w-4" />
                        <span className="hidden sm:inline">{t('settings.aiSettings')}</span>
                    </TabsTrigger>
                </TabsList>

                <div className="mt-6">
                    <TabsContent value="profile" className="m-0 focus-visible:outline-none focus-visible:ring-0">
                        <ProfileSettings />
                    </TabsContent>

                    <TabsContent value="service" className="m-0 focus-visible:outline-none focus-visible:ring-0">
                        <ServiceSettingsPanel />
                    </TabsContent>

                    <TabsContent value="ai" className="m-0 focus-visible:outline-none focus-visible:ring-0">
                        <SubscriptionSettingsPanel />
                    </TabsContent>
                </div>
            </Tabs>
        </div>
    )
}

function SettingsLoadingFallback() {
    return (
        <div className="flex bg-background p-8 justify-center">
            <div className="space-y-4 w-full max-w-md">
                <Skeleton className="h-8 w-48" />
                <Skeleton className="h-4 w-32" />
                <div className="space-y-2 mt-8">
                    <Skeleton className="h-12 w-full" />
                    <Skeleton className="h-64 w-full" />
                </div>
            </div>
        </div>
    )
}

export default function SettingsPage() {
    return (
        <Suspense fallback={<SettingsLoadingFallback />}>
            <SettingsContent />
        </Suspense>
    )
}
