"use client"

import { useState, useEffect, useCallback } from "react"
import { useSearchParams, useRouter, usePathname } from "next/navigation"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Mail, Calendar, FileText } from "lucide-react"
import { useLanguage } from "@/lib/context/language-context"
import { useAuth } from "@/lib/context/auth-context"
import { backendService, type OverviewMetricsResponse, type SubscriptionService } from '@/lib/api/backend-service'
import { EmailTabContent } from "./email-tab-content"
import { CalendarTabContent } from "./calendar-tab-content"
import { DocumentsTabContent } from "./documents-tab-content"
import { OverviewKPIs } from '@/components/dashboard/kpi-cards'

export function DashboardTabs() {
    const router = useRouter()
    const pathname = usePathname()
    const searchParams = useSearchParams()
    const { t } = useLanguage()
    const { currentSubscription, activeServiceId } = useAuth()

    // Get active tab from URL query param or default to 'email'
    const currentTab = searchParams.get('tab') || 'email'
    const [activeTab, setActiveTab] = useState(currentTab)

    // Metrics state
    const [metrics, setMetrics] = useState<OverviewMetricsResponse | null>(null)
    const [metricsLoading, setMetricsLoading] = useState(true)

    // Update URL when tab changes
    const handleTabChange = (value: string) => {
        setActiveTab(value)
        const params = new URLSearchParams(searchParams.toString())
        params.set('tab', value)
        router.push(`${pathname}?${params.toString()}`, { scroll: false })
    }

    // Sync state with URL if it changes externally
    useEffect(() => {
        if (currentTab !== activeTab) {
            setActiveTab(currentTab)
        }
    }, [currentTab])

    // Fetch metrics
    const fetchMetrics = useCallback(async () => {
        if (!currentSubscription?.subscription_id) return

        setMetricsLoading(true)

        try {
            const services = await backendService.getSubscriptionService(currentSubscription.subscription_id)
            if (!services || services.length === 0) return

            const service = (activeServiceId
                ? services.find((s: SubscriptionService) => s.service_id === activeServiceId)
                : null) || services[0] as SubscriptionService

            const overview = await backendService.getOverviewMetrics(service.service_id)
            setMetrics(overview)
        } catch (error) {
            console.error('Error fetching metrics:', error)
        } finally {
            setMetricsLoading(false)
        }
    }, [currentSubscription?.subscription_id, activeServiceId])

    useEffect(() => {
        if (currentSubscription?.subscription_id) {
            fetchMetrics()
        }
    }, [currentSubscription?.subscription_id, activeServiceId, fetchMetrics])

    return (
        <div className="flex-1 space-y-4 p-4 md:p-8 pt-6">
            {/* KPI Cards Section */}
            <div className="mx-auto w-full">
                <OverviewKPIs
                    ticketTotal={metrics?.ticket_total || 0}
                    ticketAutomatizzati={metrics?.ticket_automatizzati || 0}
                    deflectionRate={metrics?.deflection_rate_pct || 0}
                    avgResponseTime={metrics?.avg_response_time_seconds || 0}
                    alertAttivi={metrics?.alert_attivi || 0}
                    isLoading={metricsLoading}
                />
            </div>

            <Tabs
                value={activeTab}
                onValueChange={handleTabChange}
                className="space-y-4 h-full flex flex-col"
            >
                <div className="flex items-center justify-between pb-4">
                    {/* Full width TabsList as requested */}
                    <TabsList className="grid w-full grid-cols-3 h-9 p-1">
                        <TabsTrigger value="email" className="gap-1.5 text-sm">
                            <Mail className="h-3.5 w-3.5" />
                            <span className="hidden sm:inline">{t('tabs.email') || "Email"}</span>
                        </TabsTrigger>
                        <TabsTrigger value="calendar" className="gap-1.5 text-sm">
                            <Calendar className="h-3.5 w-3.5" />
                            <span className="hidden sm:inline">{t('tabs.calendar') || "Calendar"}</span>
                        </TabsTrigger>
                        <TabsTrigger value="documents" className="gap-1.5 text-sm">
                            <FileText className="h-3.5 w-3.5" />
                            <span className="hidden sm:inline">{t('tabs.documents') || "Documents"}</span>
                        </TabsTrigger>
                    </TabsList>
                </div>

                <div className="flex-1 bg-background/50 rounded-lg border p-4 sm:p-6 min-h-[600px] shadow-sm">
                    <TabsContent value="email" className="m-0 h-full border-0 p-0">
                        <EmailTabContent />
                    </TabsContent>

                    <TabsContent value="calendar" className="m-0 h-full border-0 p-0">
                        <CalendarTabContent />
                    </TabsContent>

                    <TabsContent value="documents" className="m-0 h-full border-0 p-0">
                        <DocumentsTabContent />
                    </TabsContent>
                </div>
            </Tabs>
        </div>
    )
}
