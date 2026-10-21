'use client'

import { useEffect, useState, useCallback, useMemo } from 'react'
import { EmailThreadDetail, EmailThreadSummary, EmailMessage } from '@/lib/api/backend-service'
import { useLanguage } from '@/lib/context/language-context'
import { backendService } from '@/lib/api/backend-service'
import { useAuth } from '@/lib/context/auth-context'
import { EmailMessageCard } from './email-message'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Skeleton } from '@/components/ui/skeleton'
import { Badge } from '@/components/ui/badge'
import { Textarea } from '@/components/ui/textarea'
import {
    ArrowLeft,
    MessageSquare,
    AlertTriangle,
    Send,
    Bot,
    CheckCircle2,
    Loader2,
    Mail,
    User
} from 'lucide-react'


interface ThreadDetailProps {
    thread: EmailThreadSummary
    variant?: 'inbox' | 'review' | 'failed'
    serviceEmail?: string
    onBack: () => void
}

export function ThreadDetail({ thread, variant = 'inbox', serviceEmail, onBack }: ThreadDetailProps) {
    const { t } = useLanguage()
    const { currentSubscription, activeServiceId } = useAuth()
    const [detail, setDetail] = useState<EmailThreadDetail | null>(null)
    const [isLoading, setIsLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)

    // Send email state
    const [editableBody, setEditableBody] = useState('')
    const [isSending, setIsSending] = useState(false)
    const [sendResult, setSendResult] = useState<{ success: boolean; message: string } | null>(null)

    const fetchDetail = useCallback(async () => {
        setIsLoading(true)
        setError(null)
        setSendResult(null)
        try {
            const response = await backendService.getThreadConversation(thread.thread_id)
            setDetail(response)
        } catch (err) {
            console.error('Error fetching thread detail:', err)
            setError(t('email.errorLoading'))
        } finally {
            setIsLoading(false)
        }
    }, [thread.thread_id, t])

    useEffect(() => {
        fetchDetail()
    }, [fetchDetail])

    // Find the AI-generated draft or failed message (suggested response)
    const aiDraftMessage: EmailMessage | null = useMemo(() => {
        if (!detail?.messages || (variant !== 'review' && variant !== 'failed')) return null
        // Look for the last outbound AI-generated message that is a draft or failed to send
        const candidates = detail.messages.filter(
            (m) => m.direction === 'OUTBOUND' && m.ai_generated &&
                (m.outcome === 'DRAFT' || m.outcome === 'SMTP_ERROR')
        )
        return candidates.length > 0 ? candidates[candidates.length - 1] : null
    }, [detail, variant])

    // Find the last inbound message (original email to reply to)
    const lastInboundMessage: EmailMessage | null = useMemo(() => {
        if (!detail?.messages) return null
        const inbound = detail.messages.filter((m) => m.direction === 'INBOUND')
        return inbound.length > 0 ? inbound[inbound.length - 1] : null
    }, [detail])

    const isHighPriority = thread.max_priority > 0.7
    const showResponseEditor = variant === 'review' || variant === 'failed'

    // Compute the contact email — thread summary (from the list API) is the primary source,
    // since the thread detail API (/threads/{id}) does NOT return last_sender_email
    const contactEmail = useMemo(() => {
        if (thread.last_sender_email) return thread.last_sender_email
        return null
    }, [thread.last_sender_email])

    // Initialize the editable body from the AI draft/failed message.
    // For 'failed' variant, thread.summary contains the failed response body as fallback.
    useEffect(() => {
        if (aiDraftMessage) {
            setEditableBody(aiDraftMessage.body)
        } else if (variant === 'failed' && thread.summary) {
            setEditableBody(thread.summary)
        }
    }, [aiDraftMessage, variant, thread.summary])

    // Determine the email provider from the service
    const emailProvider: 'google' | 'microsoft' | null = useMemo(() => {
        if (!currentSubscription?.services || currentSubscription.services.length === 0) return null
        const svc = activeServiceId
            ? currentSubscription.services.find(s => s.service_id === activeServiceId) || currentSubscription.services[0]
            : currentSubscription.services[0]
        if (svc.email_provider === 'google') return 'google'
        if (svc.email_provider === 'microsoft') return 'microsoft'
        return null
    }, [currentSubscription, activeServiceId])

    const handleSendEmail = async () => {
        if (!editableBody.trim() || !serviceEmail || !emailProvider || !contactEmail) return

        setIsSending(true)
        setSendResult(null)
        try {
            const result = await backendService.sendEmail({
                provider: emailProvider,
                email: serviceEmail,
                to: [contactEmail],
                subject: detail?.subject || thread.subject,
                body: editableBody,
                is_html: false,
            })
            setSendResult({ success: true, message: t('email.sentSuccess') })
            // Refresh to show the sent message
            await fetchDetail()
        } catch (err) {
            console.error('Error sending email:', err)
            setSendResult({
                success: false,
                message: err instanceof Error ? err.message : t('email.sentError')
            })
        } finally {
            setIsSending(false)
        }
    }

    // Filter out the draft/failed outbound message from the displayed conversation
    // so it only appears in the editable response section.
    // Always keep inbound messages and non-draft outbound messages visible.
    const displayMessages = useMemo(() => {
        if (!detail?.messages) return []
        if (!showResponseEditor || !aiDraftMessage) return detail.messages
        return detail.messages.filter((m) => m.id !== aiDraftMessage.id)
    }, [detail, showResponseEditor, aiDraftMessage])

    if (isLoading) {
        return (
            <div className="h-full flex flex-col">
                <div className="p-4 border-b">
                    <Skeleton className="h-6 w-3/4 mb-2" />
                    <Skeleton className="h-4 w-1/2" />
                </div>
                <div className="flex-1 p-4 space-y-4">
                    <Skeleton className="h-32 w-full" />
                    <Skeleton className="h-32 w-full" />
                </div>
            </div>
        )
    }

    if (error) {
        return (
            <div className="h-full flex flex-col items-center justify-center p-8 text-center">
                <div className="rounded-full bg-red-500/10 p-4 mb-4">
                    <AlertTriangle className="h-8 w-8 text-red-500" />
                </div>
                <p className="text-sm text-muted-foreground">{error}</p>
                <Button variant="outline" className="mt-4" onClick={fetchDetail}>
                    {t('email.refresh')}
                </Button>
            </div>
        )
    }

    return (
        <div className="h-full flex flex-col min-h-0 overflow-hidden">
            {/* Header — compact */}
            <div className="p-4 border-b bg-muted/30 shrink-0">
                <div className="flex items-center gap-2 mb-2">
                    <Button variant="ghost" size="sm" onClick={onBack}>
                        <ArrowLeft className="h-4 w-4 mr-1" />
                        {t('email.backToList')}
                    </Button>
                </div>

                <h2 className="text-lg font-semibold">
                    {detail?.subject || thread.subject}
                </h2>

                {/* Contact / sender info — always show when available */}
                {contactEmail && (
                    <div className="mt-1 flex items-center gap-2 text-sm text-muted-foreground">
                        <User className="h-3.5 w-3.5" />
                        <span>{contactEmail}</span>
                    </div>
                )}

                <div className="mt-2 flex items-center gap-2 flex-wrap">
                    {thread.category && (
                        <Badge variant="outline" className="text-xs">
                            {thread.category}
                            {thread.subcategory && ` / ${thread.subcategory}`}
                        </Badge>
                    )}
                    <Badge variant="outline" className="text-xs gap-1">
                        <MessageSquare className="h-3 w-3" />
                        {detail?.message_count || thread.email_count} {
                            (detail?.message_count || thread.email_count) === 1
                                ? t('email.message')
                                : t('email.messages')
                        }
                    </Badge>
                    {isHighPriority && (
                        <Badge
                            variant="outline"
                            className="text-xs bg-orange-500/10 text-orange-600 dark:text-orange-400 border-orange-500/20"
                        >
                            <AlertTriangle className="h-3 w-3 mr-1" />
                            {t('email.highPriority')}
                        </Badge>
                    )}
                </div>
            </div>

            {/* Scrollable content: Summary + Conversation + Response editor */}
            <ScrollArea className="flex-1 min-h-0">
                <div className="p-4 space-y-6">

                    {/* ── Section 1: Thread Summary (from list API, not shown for 'failed' since summary there is the response body) ── */}
                    {thread.summary && variant !== 'failed' && (
                        <div className="rounded-lg border bg-muted/40 p-4">
                            <div className="flex items-center gap-2 mb-2">
                                <MessageSquare className="h-4 w-4 text-primary" />
                                <span className="text-sm font-semibold">{t('email.summary')}</span>
                            </div>
                            <p className="text-sm leading-relaxed text-foreground">
                                {thread.summary}
                            </p>
                        </div>
                    )}

                    {/* ── Section 2: Conversation ── */}
                    <div>
                        <div className="flex items-center gap-2 mb-3">
                            <Mail className="h-4 w-4 text-muted-foreground" />
                            <span className="text-sm font-semibold text-muted-foreground">
                                {t('email.conversation') || 'Conversation'}
                            </span>
                        </div>

                        {displayMessages.length > 0 ? (
                            <div className="space-y-4">
                                {displayMessages.map((message) => (
                                    <EmailMessageCard key={message.id} message={message} />
                                ))}
                            </div>
                        ) : (
                            /* Fallback: no visible messages after filtering the draft —
                               show the original email context so the user knows what they're replying to */
                            <div className="rounded-lg border bg-muted/30 p-4 text-sm text-muted-foreground">
                                <p className="italic">{t('email.noConversationMessages') || 'No conversation messages to display for this thread.'}</p>
                            </div>
                        )}
                    </div>

                    {/* ── Section 3: Suggested Response Editor (review / failed only) ── */}
                    {showResponseEditor && (
                        <div className="rounded-lg border bg-muted/20 p-4 space-y-3">
                            {/* Section header */}
                            <div className="flex items-center gap-2">
                                {aiDraftMessage ? (
                                    <Bot className="h-4 w-4 text-violet-500" />
                                ) : (
                                    <Send className="h-4 w-4 text-primary" />
                                )}
                                <span className="text-sm font-semibold">
                                    {aiDraftMessage ? t('email.suggestedResponse') : t('email.writeResponse')}
                                </span>
                                {contactEmail && (
                                    <span className="text-xs text-muted-foreground ml-auto">
                                        {t('email.replyTo')} {contactEmail}
                                    </span>
                                )}
                            </div>

                            <p className="text-xs text-muted-foreground">
                                {aiDraftMessage ? t('email.editResponse') : t('email.writeResponseHint')}
                            </p>

                            <Textarea
                                value={editableBody}
                                onChange={(e) => setEditableBody(e.target.value)}
                                placeholder={!aiDraftMessage ? (t('email.writeResponsePlaceholder') || 'Write your response here...') : undefined}
                                className="min-h-[140px] max-h-[300px] resize-y text-sm"
                                disabled={isSending || sendResult?.success === true}
                            />

                            {/* Send result feedback */}
                            {sendResult && (
                                <div className={`flex items-center gap-2 text-sm rounded-lg p-2 ${
                                    sendResult.success
                                        ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400'
                                        : 'bg-red-500/10 text-red-600 dark:text-red-400'
                                }`}>
                                    {sendResult.success ? (
                                        <CheckCircle2 className="h-4 w-4" />
                                    ) : (
                                        <AlertTriangle className="h-4 w-4" />
                                    )}
                                    {sendResult.message}
                                </div>
                            )}

                            {/* Send button */}
                            {!sendResult?.success && (
                                <div className="flex justify-end pt-1">
                                    <Button
                                        onClick={handleSendEmail}
                                        disabled={
                                            isSending ||
                                            !editableBody.trim() ||
                                            !serviceEmail ||
                                            !emailProvider
                                        }
                                        size="default"
                                        className="gap-2"
                                    >
                                        {isSending ? (
                                            <>
                                                <Loader2 className="h-4 w-4 animate-spin" />
                                                {t('email.sending')}
                                            </>
                                        ) : (
                                            <>
                                                <Send className="h-4 w-4" />
                                                {t('email.sendResponse')}
                                            </>
                                        )}
                                    </Button>
                                </div>
                            )}
                        </div>
                    )}
                </div>
            </ScrollArea>
        </div>
    )
}
