'use client'

import { useEffect, useState, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth, useSubscriptionConfig } from '@/lib/context/auth-context'
import { useLanguage } from '@/lib/context/language-context'
import { Skeleton } from '@/components/ui/skeleton'
import { Button } from '@/components/ui/button'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Card } from '@/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select"
import {
    AlertCircle,
    RefreshCw,
    Inbox,
    AlertTriangle,
    XCircle,
    Mail
} from 'lucide-react'
import {
    backendService,
    type EmailThreadSummary,
    type FailedOutboundEmail,
    type SubscriptionService
} from '@/lib/api/backend-service'
import { ThreadList } from '@/components/email/thread-list'
import { ThreadDetail } from '@/components/email/thread-detail'

type EmailTab = 'inbox' | 'review' | 'failed'

export function EmailTabContent() {
    const router = useRouter()
    const { isLoading, isAuthenticated, currentSubscription, activeServiceId } = useAuth()
    const { isConfigured } = useSubscriptionConfig()
    const { t } = useLanguage()
    const [isReady, setIsReady] = useState(false)
    const [isRefreshing, setIsRefreshing] = useState(false)
    const [activeTab, setActiveTab] = useState<EmailTab>('review')
    const [selectedCategory, setSelectedCategory] = useState<string>('all')
    const [page, setPage] = useState(0)
    const [hasMore, setHasMore] = useState(true)

    const CATEGORIES = [
        { value: 'PROMOTION', label: t('email.category.promotion') || 'Promotion' },
        { value: 'SOCIAL_NOTIFICATION', label: t('email.category.socialNotification') || 'Social Notification' },
        { value: 'INFO_PROVIDED', label: t('email.category.infoProvided') || 'Info Provided' },
        { value: 'INFO_REQUESTED', label: t('email.category.infoRequested') || 'Info Requested' },
        { value: 'CALENDAR_EVENT', label: t('email.category.calendarEvent') || 'Calendar Event' },
        { value: 'TRANSACTIONAL', label: t('email.category.transactional') || 'Transactional' },
        { value: 'OTHER', label: t('email.category.other') || 'Other' },
    ]

    // Data states
    const [inboxThreads, setInboxThreads] = useState<EmailThreadSummary[]>([])
    const [reviewThreads, setReviewThreads] = useState<EmailThreadSummary[]>([])
    const [failedEmails, setFailedEmails] = useState<FailedOutboundEmail[]>([])
    const [selectedThread, setSelectedThread] = useState<EmailThreadSummary | null>(null)

    // Loading states
    const [inboxLoading, setInboxLoading] = useState(true)
    const [reviewLoading, setReviewLoading] = useState(true)
    const [failedLoading, setFailedLoading] = useState(true)

    const [error, setError] = useState<string | null>(null)
    const [serviceEmail, setServiceEmail] = useState<string | null>(null)
    const [serviceId, setServiceId] = useState<string | null>(null)

    // Auth redirects
    useEffect(() => {
        if (!isLoading && !isAuthenticated) {
            router.push('/login')
        }
    }, [isLoading, isAuthenticated, router])

    useEffect(() => {
        if (!isLoading && isAuthenticated && !isConfigured) {
            router.push('/setup')
        }
    }, [isLoading, isAuthenticated, isConfigured, router])

    useEffect(() => {
        if (!isLoading && isAuthenticated && isConfigured) {
            const timer = setTimeout(() => setIsReady(true), 100)
            return () => clearTimeout(timer)
        }
    }, [isLoading, isAuthenticated, isConfigured])

    // Fetch service email
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
                    setServiceId(service.service_id)
                }
            } catch (err) {
                console.error('Error fetching subscription service:', err)
            }
        }

        if (isReady) {
            fetchServiceInfo()
        }
    }, [isReady, currentSubscription?.subscription_id])

    // Fetch inbox threads
    const fetchInbox = useCallback(async (pageNum: number = 0) => {
        if (!serviceEmail) return
        setInboxLoading(true)
        try {
            const limit = 20
            const offset = pageNum * limit

            const response = await backendService.getInboxThreads({
                box_email: serviceEmail,
                limit,
                offset,
                category: selectedCategory !== 'all' ? selectedCategory : undefined
            })

            const newThreads = response || []

            if (pageNum === 0) {
                setInboxThreads(newThreads)
            } else {
                setInboxThreads(prev => [...prev, ...newThreads])
            }

            setHasMore(newThreads.length === limit)
        } catch (err) {
            console.error('Error fetching inbox:', err)
            setError(t('email.errorLoading'))
        } finally {
            setInboxLoading(false)
        }
    }, [serviceEmail, t, selectedCategory])

    // Fetch human review threads
    const fetchReview = useCallback(async () => {
        if (!serviceEmail) return
        setReviewLoading(true)
        try {
            const response = await backendService.getHumanReviewThreads(serviceEmail, 50, 0)
            setReviewThreads(response || [])
        } catch (err) {
            console.error('Error fetching review threads:', err)
        } finally {
            setReviewLoading(false)
        }
    }, [serviceEmail])

    // Fetch failed emails
    const fetchFailed = useCallback(async () => {
        if (!serviceId) return
        setFailedLoading(true)
        try {
            const response = await backendService.getFailedOutboundEmails(serviceId)
            setFailedEmails(response || [])
        } catch (err) {
            console.error('Error fetching failed emails:', err)
        } finally {
            setFailedLoading(false)
        }
    }, [serviceId])

    // Fetch all data when service email and id are available
    useEffect(() => {
        if (serviceEmail && serviceId) {
            setPage(0)
            fetchInbox(0)
            fetchReview()
            fetchFailed()
        }
    }, [serviceEmail, serviceId, fetchInbox, fetchReview, fetchFailed])

    const handleRefresh = async () => {
        setIsRefreshing(true)
        setError(null)
        setPage(0)
        setHasMore(true)
        await Promise.all([fetchInbox(0), fetchReview(), fetchFailed()])
        setIsRefreshing(false)
    }

    const handleLoadMore = () => {
        if (!hasMore || inboxLoading) return
        const nextPage = page + 1
        setPage(nextPage)
        fetchInbox(nextPage)
    }

    const handleSelectThread = (thread: EmailThreadSummary) => {
        setSelectedThread(thread)
    }

    const handleBackToList = () => {
        setSelectedThread(null)
    }

    // Convert failed emails to thread summary format for display
    // Note: last_sender_email and summary are placeholders here;
    // the real values are resolved when ThreadDetail fetches via thread_id
    const failedAsThreads: EmailThreadSummary[] = failedEmails.map(email => ({
        thread_id: email.thread_id,
        subject: `Failed: ${email.outcome}`,
        status: 'PENDING' as const,
        last_message_at: email.datetime,
        last_sender_email: '',
        human_response: false,
        summary: email.body,
        email_count: 1,
        has_attachments: false,
        max_priority: 1
    }))

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
        <div className="flex flex-col gap-4 h-full animate-in fade-in duration-300">
            {/* Header */}
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                <div>
                    <h2 className="text-xl font-semibold tracking-tight">{t('email.title')}</h2>
                    <p className="text-muted-foreground text-sm">
                        {t('email.subtitle')}
                    </p>
                </div>
                <div className="flex items-center gap-2">
                    <Select value={selectedCategory} onValueChange={setSelectedCategory}>
                        <SelectTrigger className="w-[180px]">
                            <SelectValue placeholder={t('email.filterByCategory') || "Filter by category"} />
                        </SelectTrigger>
                        <SelectContent>
                            <SelectItem value="all">{t('email.allCategories')}</SelectItem>
                            {CATEGORIES.map((cat) => (
                                <SelectItem key={cat.value} value={cat.value}>
                                    {cat.label}
                                </SelectItem>
                            ))}
                        </SelectContent>
                    </Select>
                    <Button
                        variant="outline"
                        size="sm"
                        onClick={handleRefresh}
                        disabled={isRefreshing}
                    >
                        <RefreshCw className={`h-4 w-4 mr-2 ${isRefreshing ? 'animate-spin' : ''}`} />
                        {t('email.refresh')}
                    </Button>
                </div>
            </div>

            {/* Error Alert */}
            {error && (
                <Alert variant="destructive">
                    <AlertCircle className="h-4 w-4" />
                    <AlertTitle>{t('common.error')}</AlertTitle>
                    <AlertDescription>{error}</AlertDescription>
                </Alert>
            )}

            {/* Main Content */}
            <Tabs
                value={activeTab}
                onValueChange={(v) => {
                    setActiveTab(v as EmailTab)
                    setSelectedThread(null)
                }}
                className="flex-1 flex flex-col"
            >
                <TabsList className="grid w-full grid-cols-3 mb-4 max-w-lg">
                    <TabsTrigger value="review" className="gap-2">
                        <AlertTriangle className="h-4 w-4" />
                        <span className="hidden sm:inline">{t('email.needsReview')}</span>
                        {reviewThreads.length > 0 && (
                            <span className="ml-1 bg-amber-500/20 text-amber-600 dark:text-amber-400 px-1.5 py-0.5 rounded-full text-xs">
                                {reviewThreads.length}
                            </span>
                        )}
                    </TabsTrigger>
                    <TabsTrigger value="failed" className="gap-2">
                        <XCircle className="h-4 w-4" />
                        <span className="hidden sm:inline">{t('email.failed')}</span>
                        {failedEmails.length > 0 && (
                            <span className="ml-1 bg-red-500/20 text-red-600 dark:text-red-400 px-1.5 py-0.5 rounded-full text-xs">
                                {failedEmails.length}
                            </span>
                        )}
                    </TabsTrigger>
                    <TabsTrigger value="inbox" className="gap-2">
                        <Inbox className="h-4 w-4" />
                        <span className="hidden sm:inline">{t('email.inbox')}</span>
                        {inboxThreads.length > 0 && (
                            <span className="ml-1 bg-blue-500/20 text-blue-600 dark:text-blue-400 px-1.5 py-0.5 rounded-full text-xs">
                                {inboxThreads.length}
                            </span>
                        )}
                    </TabsTrigger>
                </TabsList>

                {/* Dynamic layout: full width list or split pane */}
                <div className={`grid gap-4 h-[700px] ${selectedThread ? 'grid-cols-1 lg:grid-cols-2' : 'grid-cols-1'}`}>
                    {/* Thread List */}
                    <Card className="overflow-hidden flex flex-col h-full min-h-0">
                        <TabsContent value="inbox" className="m-0 h-full overflow-hidden">
                            <ThreadList
                                threads={inboxThreads}
                                selectedThreadId={selectedThread?.thread_id}
                                variant="inbox"
                                isLoading={inboxLoading && page === 0}
                                onSelectThread={handleSelectThread}
                                onLoadMore={handleLoadMore}
                                hasMore={hasMore}
                            />
                        </TabsContent>
                        <TabsContent value="review" className="m-0 h-full overflow-hidden">
                            <ThreadList
                                threads={reviewThreads}
                                selectedThreadId={selectedThread?.thread_id}
                                variant="review"
                                isLoading={reviewLoading}
                                onSelectThread={handleSelectThread}
                            />
                        </TabsContent>
                        <TabsContent value="failed" className="m-0 h-full overflow-hidden">
                            <ThreadList
                                threads={failedAsThreads}
                                selectedThreadId={selectedThread?.thread_id}
                                variant="failed"
                                isLoading={failedLoading}
                                onSelectThread={handleSelectThread}
                            />
                        </TabsContent>
                    </Card>

                    {/* Detail View - only shown when a thread is selected */}
                    {selectedThread && (
                        <Card className="overflow-hidden h-full min-h-0 flex flex-col">
                            <ThreadDetail
                                thread={selectedThread}
                                variant={activeTab}
                                serviceEmail={serviceEmail || undefined}
                                onBack={handleBackToList}
                            />
                        </Card>
                    )}
                </div>
            </Tabs>
        </div>
    )
}
