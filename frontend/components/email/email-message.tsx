'use client'

import { EmailMessage } from '@/lib/api/backend-service'
import { useLanguage } from '@/lib/context/language-context'
import { Badge } from '@/components/ui/badge'
import { Bot, Paperclip, ArrowDownLeft, ArrowUpRight } from 'lucide-react'
import { cn } from '@/lib/utils'

interface EmailMessageCardProps {
    message: EmailMessage
}

export function EmailMessageCard({ message }: EmailMessageCardProps) {
    const { t } = useLanguage()

    const isInbound = message.direction === 'INBOUND'
    const isAI = message.ai_generated

    const formatDateTime = (dateString: string) => {
        const date = new Date(dateString)
        return date.toLocaleString([], {
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
        })
    }

    const getOutcomeLabel = () => {
        if (!message.outcome) return null
        switch (message.outcome) {
            case 'SENT': return t('email.outcome.sent')
            case 'DRAFT': return t('email.outcome.draft')
            case 'SMTP_ERROR': return t('email.outcome.smtpError')
            default: return message.outcome
        }
    }

    const outcomeLabel = getOutcomeLabel()
    const isError = message.outcome === 'SMTP_ERROR'

    return (
        <div className={cn(
            'rounded-lg border p-4',
            isInbound
                ? 'bg-muted/30 border-border ml-0 mr-8'
                : 'bg-primary/5 border-primary/20 ml-8 mr-0'
        )}>
            {/* Header */}
            <div className="flex items-start justify-between gap-2 mb-3">
                <div className="flex items-center gap-2">
                    {isInbound ? (
                        <div className="flex items-center gap-1.5 text-sm">
                            <ArrowDownLeft className="h-4 w-4 text-blue-500" />
                            <span className="font-medium">{t('email.inbound')}</span>
                        </div>
                    ) : (
                        <div className="flex items-center gap-1.5 text-sm">
                            <ArrowUpRight className="h-4 w-4 text-emerald-500" />
                            <span className="font-medium">{t('email.outbound')}</span>
                        </div>
                    )}
                    {isAI && (
                        <Badge variant="outline" className="text-xs gap-1 bg-violet-500/10 text-violet-600 dark:text-violet-400 border-violet-500/20">
                            <Bot className="h-3 w-3" />
                            AI
                        </Badge>
                    )}
                    {outcomeLabel && (
                        <Badge
                            variant="outline"
                            className={cn(
                                'text-xs',
                                isError
                                    ? 'bg-red-500/10 text-red-600 dark:text-red-400 border-red-500/20'
                                    : 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20'
                            )}
                        >
                            {outcomeLabel}
                        </Badge>
                    )}
                </div>
                <span className="text-xs text-muted-foreground">
                    {formatDateTime(message.datetime)}
                </span>
            </div>

            {/* Subject if different */}
            {message.subject && (
                <div className="mb-2">
                    <span className="text-xs text-muted-foreground">{t('email.subject')}: </span>
                    <span className="text-sm font-medium">{message.subject}</span>
                </div>
            )}

            {/* Body */}
            <div className="text-sm text-foreground whitespace-pre-wrap leading-relaxed break-words [word-break:break-word] w-full">
                {message.body}
            </div>

            {/* Attachment indicator */}
            {message.has_attachment && (
                <div className="mt-3 pt-3 border-t flex items-center gap-2 text-xs text-muted-foreground">
                    <Paperclip className="h-3.5 w-3.5" />
                    <span>{t('email.attachments')}</span>
                </div>
            )}

            {/* Priority for inbound */}
            {isInbound && message.priority_score !== undefined && message.priority_score > 0.5 && (
                <div className="mt-3 pt-3 border-t">
                    <div className="flex items-center gap-2">
                        <span className="text-xs text-muted-foreground">{t('email.priority')}:</span>
                        <div className="flex-1 h-1.5 rounded-full bg-muted overflow-hidden max-w-24">
                            <div
                                className={cn(
                                    'h-full rounded-full',
                                    message.priority_score > 0.8
                                        ? 'bg-gradient-to-r from-orange-500 to-red-500'
                                        : 'bg-gradient-to-r from-blue-500 to-violet-500'
                                )}
                                style={{ width: `${message.priority_score * 100}%` }}
                            />
                        </div>
                        <span className="text-xs font-medium">
                            {Math.round(message.priority_score * 100)}%
                        </span>
                    </div>
                </div>
            )}
        </div>
    )
}
