'use client'

import { useEffect, useState, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth, useSubscriptionConfig } from '@/lib/context/auth-context'
import { useLanguage } from '@/lib/context/language-context'
import { Skeleton } from '@/components/ui/skeleton'
import { Button } from '@/components/ui/button'
import { AlertCircle, RefreshCw } from 'lucide-react'
import {
    backendService,
    type CalendarEvent,
    type GetCalendarEventsRequest,
    type SubscriptionService,
} from '@/lib/api/backend-service'
import { CalendarView } from '@/components/calendar/calendar-view'
import { type EventFormData } from '@/components/calendar/event-form-dialog'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'

export function CalendarTabContent() {
    const router = useRouter()
    const { isLoading, isAuthenticated, currentSubscription, activeServiceId } = useAuth()
    const { isConfigured } = useSubscriptionConfig()
    const { t } = useLanguage()
    const [isReady, setIsReady] = useState(false)
    const [isRefreshing, setIsRefreshing] = useState(false)
    const [eventsLoading, setEventsLoading] = useState(true)
    const [events, setEvents] = useState<CalendarEvent[]>([])
    const [error, setError] = useState<string | null>(null)
    const [serviceEmail, setServiceEmail] = useState<string | null>(null)
    const [serviceProvider, setServiceProvider] = useState<'google' | 'microsoft' | null>(null)

    // Redirect to login if not authenticated
    useEffect(() => {
        if (!isLoading && !isAuthenticated) {
            router.push('/login')
        }
    }, [isLoading, isAuthenticated, router])

    // Redirect to setup if not configured
    useEffect(() => {
        if (!isLoading && isAuthenticated && !isConfigured) {
            router.push('/setup')
        }
    }, [isLoading, isAuthenticated, isConfigured, router])

    // Set ready state after auth checks pass
    useEffect(() => {
        if (!isLoading && isAuthenticated && isConfigured) {
            const timer = setTimeout(() => setIsReady(true), 100)
            return () => clearTimeout(timer)
        }
    }, [isLoading, isAuthenticated, isConfigured])

    // Fetch subscription service to get email and provider
    useEffect(() => {
        const fetchServiceInfo = async () => {
            if (!currentSubscription?.subscription_id) return

            try {
                const services = await backendService.getSubscriptionService(currentSubscription.subscription_id)
                if (services && services.length > 0) {
                    const service = (activeServiceId
                        ? services.find(s => s.service_id === activeServiceId)
                        : null) || services[0] as SubscriptionService
                    setServiceEmail(service.email)
                    if (service.email_provider === 'google' || service.email_provider === 'microsoft') {
                        setServiceProvider(service.email_provider)
                    }
                }
            } catch (err) {
                console.error('Error fetching subscription service:', err)
            }
        }

        if (isReady) {
            fetchServiceInfo()
        }
    }, [isReady, currentSubscription?.subscription_id])

    const fetchEvents = useCallback(async (year?: number, month?: number) => {
        if (!serviceEmail || !serviceProvider) return

        setEventsLoading(true)
        setError(null)

        const now = new Date()
        const targetYear = year ?? now.getFullYear()
        const targetMonth = month ?? now.getMonth()

        // Get first and last day of the month with some padding
        const timeMin = new Date(targetYear, targetMonth - 1, 1).toISOString()
        const timeMax = new Date(targetYear, targetMonth + 2, 0).toISOString()

        const payload: GetCalendarEventsRequest = {
            provider: serviceProvider,
            email: serviceEmail,
            time_min: timeMin,
            time_max: timeMax,
            max_results: 100,
        }

        try {
            const response = await backendService.getCalendarEvents(payload)
            setEvents(response || [])
        } catch (err) {
            console.error('Error fetching events:', err)
            setError('Failed to load calendar events')
            setEvents([])
        } finally {
            setEventsLoading(false)
        }
    }, [serviceEmail, serviceProvider])

    // Fetch events when service info is available
    useEffect(() => {
        if (serviceEmail && serviceProvider) {
            fetchEvents()
        }
    }, [serviceEmail, serviceProvider, fetchEvents])

    const handleRefresh = async () => {
        setIsRefreshing(true)
        await fetchEvents()
        setIsRefreshing(false)
    }

    const handleMonthChange = (year: number, month: number) => {
        fetchEvents(year, month)
    }

    // Convert datetime-local string to ISO 8601
    const toISO = (val: string, isAllDay: boolean): string => {
        if (isAllDay) {
            // date-only → full day ISO
            return new Date(val + 'T00:00:00').toISOString()
        }
        return new Date(val).toISOString()
    }

    const handleCreateEvent = useCallback(async (data: EventFormData) => {
        if (!serviceEmail || !serviceProvider) return
        await backendService.createCalendarEvent({
            provider: serviceProvider,
            email: serviceEmail,
            title: data.title,
            description: data.description || undefined,
            location: data.location || undefined,
            start: toISO(data.start, data.is_all_day),
            end: toISO(data.end, data.is_all_day),
            is_all_day: data.is_all_day,
            attendees: data.attendees.length > 0 ? data.attendees : undefined,
            timezone: 'Europe/Rome',
        })
        // Refresh events after creation
        await fetchEvents()
    }, [serviceEmail, serviceProvider, fetchEvents])

    const handleUpdateEvent = useCallback(async (eventId: string, data: EventFormData) => {
        if (!serviceEmail || !serviceProvider) return
        await backendService.updateCalendarEvent(eventId, {
            provider: serviceProvider,
            email: serviceEmail,
            title: data.title,
            description: data.description || undefined,
            location: data.location || undefined,
            start: toISO(data.start, data.is_all_day),
            end: toISO(data.end, data.is_all_day),
            is_all_day: data.is_all_day,
            attendees: data.attendees.length > 0 ? data.attendees : undefined,
            timezone: 'Europe/Rome',
        })
        await fetchEvents()
    }, [serviceEmail, serviceProvider, fetchEvents])

    const handleDeleteEvent = useCallback(async (eventId: string) => {
        if (!serviceEmail || !serviceProvider) return
        await backendService.deleteCalendarEvent(eventId, {
            provider: serviceProvider,
            email: serviceEmail,
        })
        await fetchEvents()
    }, [serviceEmail, serviceProvider, fetchEvents])

    if (isLoading || !isReady) {
        return (
            <div className="flex items-center justify-center p-8 h-full">
                <div className="space-y-4 w-full max-w-md">
                    <Skeleton className="h-8 w-48" />
                    <Skeleton className="h-4 w-32" />
                    <div className="space-y-2 mt-8">
                        <Skeleton className="h-24 w-full" />
                        <Skeleton className="h-64 w-full" />
                    </div>
                </div>
            </div>
        )
    }

    return (
        <div className="flex flex-col gap-6 h-full animate-in fade-in duration-300">
            {/* Header */}
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                <div>
                    <h2 className="text-xl font-semibold tracking-tight">{t('calendar.title')}</h2>
                    <p className="text-muted-foreground text-sm">
                        {t('calendar.subtitle')}
                    </p>
                </div>
                <Button
                    variant="outline"
                    size="sm"
                    onClick={handleRefresh}
                    disabled={isRefreshing || eventsLoading}
                >
                    <RefreshCw className={`h-4 w-4 mr-2 ${isRefreshing ? 'animate-spin' : ''}`} />
                    {t('calendar.refresh')}
                </Button>
            </div>

            {/* Error Alert */}
            {error && (
                <Alert variant="destructive">
                    <AlertCircle className="h-4 w-4" />
                    <AlertTitle>{t('common.error')}</AlertTitle>
                    <AlertDescription>{error}</AlertDescription>
                </Alert>
            )}

            {/* Calendar View */}
            <div className="flex-1 h-[calc(100vh-220px)] min-h-[600px] overflow-hidden">
                <CalendarView
                    events={events}
                    isLoading={eventsLoading}
                    onMonthChange={handleMonthChange}
                    onCreateEvent={handleCreateEvent}
                    onUpdateEvent={handleUpdateEvent}
                    onDeleteEvent={handleDeleteEvent}
                />
            </div>
        </div>
    )
}
