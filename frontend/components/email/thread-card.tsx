'use client'

import { EmailThreadSummary } from '@/lib/api/backend-service'
import { useLanguage } from '@/lib/context/language-context'
import { Badge } from '@/components/ui/badge'
import {
    Bot,
    Clock,
    Mail,
    Paperclip,
    AlertTriangle,
    User
} from 'lucide-react'
import { cn } from '@/lib/utils'

interface ThreadCardProps {
    thread: EmailThreadSummary
    isSelected?: boolean
    variant?: 'inbox' | 'review' | 'failed'
    onClick?: () => void
}

export function ThreadCard({ thread, isSelected, variant = 'inbox', onClick }: ThreadCardProps) {
    const { t } = useLanguage()

    const formatTimeAgo = (dateString: string) => {
        const date = new Date(dateString)
        const now = new Date()
        const diffMs = now.getTime() - date.getTime()
        const diffMins = Math.floor(diffMs / 60000)
        const diffHours = Math.floor(diffMs / 3600000)
        const diffDays = Math.floor(diffMs / 86400000)

        if (diffMins < 60) return `${diffMins}m`
        if (diffHours < 24) return `${diffHours}h`
        if (diffDays < 7) return `${diffDays}d`
        return date.toLocaleDateString()
    }

    const getVariantStyles = () => {
        switch (variant) {
            case 'review':
                return {
                    border: 'border-l-4 border-l-amber-500',
                    bg: isSelected ? 'bg-amber-500/15' : 'hover:bg-amber-500/5',
                    badge: 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20'
                }
            case 'failed':
                return {
                    border: 'border-l-4 border-l-red-500',
                    bg: isSelected ? 'bg-red-500/15' : 'hover:bg-red-500/5',
                    badge: 'bg-red-500/10 text-red-600 dark:text-red-400 border-red-500/20'
                }
            default:
                return {
                    border: 'border-l-4 border-l-blue-500',
                    bg: isSelected ? 'bg-blue-500/15' : 'hover:bg-muted/50',
                    badge: 'bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/20'
                }
        }
    }

    const styles = getVariantStyles()
    const isHighPriority = thread.max_priority > 0.7

    const getStatusLabel = () => {
        switch (thread.status) {
            case 'OPEN': return t('email.status.open')
            case 'HUMAN_REVIEW': return t('email.status.humanReview')
            case 'CLOSED': return t('email.status.closed')
            case 'PENDING': return t('email.status.pending')
            default: return thread.status
        }
    }

    return (
        <div
            onClick={onClick}
            className={cn(
                'group p-4 pr-6 cursor-pointer transition-all duration-200 border-b',
                styles.border,
                styles.bg,
                isSelected && 'ring-1 ring-primary/20'
            )}
        >
            <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0 pr-2">
                    {/* Subject */}
                    <h4 className={cn(
                        'font-medium text-sm truncate transition-colors',
                        isSelected ? 'text-primary' : 'group-hover:text-primary'
                    )}>
                        {thread.subject || '(No Subject)'}
                    </h4>

                    {/* Sender and preview */}
                    {thread.last_sender_email && (
                        <div className="mt-1 flex items-center gap-2">
                            <User className="h-3 w-3 text-muted-foreground flex-shrink-0" />
                            <span className="text-xs text-muted-foreground truncate">
                                {thread.last_sender_email}
                            </span>
                        </div>
                    )}

                    {/* Summary - truncated */}
                    {thread.summary && (
                        <p className="mt-1 text-xs text-muted-foreground truncate">
                            {thread.summary.length > 60 ? thread.summary.slice(0, 60) + '…' : thread.summary}
                        </p>
                    )}

                    {/* Meta info */}
                    <div className="mt-2 flex items-center gap-2 flex-wrap">
                        {thread.category && (
                            <Badge variant="outline" className="text-xs bg-blue-50 text-blue-700 hover:bg-blue-50/80 dark:bg-blue-900/30 dark:text-blue-300 border-blue-200 dark:border-blue-800">
                                {t(`email.category.${thread.category.toLowerCase().replace(/_([a-z])/g, (g) => g[1].toUpperCase())}`) ||
                                    thread.category.replace(/_/g, ' ').toLowerCase().replace(/\b\w/g, l => l.toUpperCase())}
                                {thread.subcategory && ` / ${thread.subcategory.replace(/_/g, ' ').toLowerCase().replace(/\b\w/g, l => l.toUpperCase())}`}
                            </Badge>
                        )}
                        <Badge variant="outline" className={cn('text-xs', styles.badge)}>
                            {getStatusLabel()}
                        </Badge>
                        {isHighPriority && (
                            <Badge variant="outline" className="text-xs bg-orange-500/10 text-orange-600 dark:text-orange-400 border-orange-500/20">
                                <AlertTriangle className="h-3 w-3 mr-1" />
                                {t('email.highPriority')}
                            </Badge>
                        )}
                    </div>
                </div>

                {/* Right column - time and indicators */}
                <div className="flex flex-col items-end gap-1 flex-shrink-0">
                    <span className="text-xs text-muted-foreground flex items-center gap-1">
                        <Clock className="h-3 w-3" />
                        {formatTimeAgo(thread.last_message_at)}
                    </span>

                    <div className="flex items-center gap-1 mt-1">
                        {thread.has_attachments && (
                            <Paperclip className="h-3.5 w-3.5 text-muted-foreground" />
                        )}
                        {!thread.human_response && thread.email_count > 1 && (
                            <Bot className="h-3.5 w-3.5 text-violet-500" />
                        )}
                        <div className="flex items-center gap-0.5 text-xs text-muted-foreground">
                            <Mail className="h-3 w-3" />
                            {thread.email_count}
                        </div>
                    </div>

                    {/* Priority bar */}
                    {isHighPriority && (
                        <div className="w-12 h-1 rounded-full bg-muted overflow-hidden mt-1">
                            <div
                                className="h-full bg-gradient-to-r from-orange-500 to-red-500"
                                style={{ width: `${thread.max_priority * 100}%` }}
                            />
                        </div>
                    )}
                </div>
            </div>
        </div>
    )
}
