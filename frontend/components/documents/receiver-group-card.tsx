'use client'

import { type ReceiverGroup } from '@/lib/api/backend-service'
import { useLanguage } from '@/lib/context/language-context'
import { Badge } from '@/components/ui/badge'
import { formatFileSize } from './attachment-card'
import {
    Building2,
    Files,
    HardDrive,
    ChevronRight,
    Clock,
} from 'lucide-react'
import { cn } from '@/lib/utils'

interface ReceiverGroupCardProps {
    group: ReceiverGroup
    isSelected?: boolean
    onClick?: () => void
}

export function ReceiverGroupCard({ group, isSelected, onClick }: ReceiverGroupCardProps) {
    const { t } = useLanguage()

    const totalSize = group.attachments.reduce((sum, a) => sum + a.size_bytes, 0)
    const uniqueTypes = new Set(group.attachments.map(a => {
        const ext = a.file_name.split('.').pop()?.toUpperCase()
        return ext || 'FILE'
    }))

    const latestDate = group.attachments.length > 0
        ? group.attachments.reduce((latest, a) => {
            const d = new Date(a.created_at)
            return d > latest ? d : latest
        }, new Date(0))
        : null

    const formatTimeAgo = (date: Date) => {
        const now = new Date()
        const diffMs = now.getTime() - date.getTime()
        const diffMins = Math.floor(diffMs / 60000)
        const diffHours = Math.floor(diffMs / 3600000)
        const diffDays = Math.floor(diffMs / 86400000)

        if (diffMins < 60) return `${diffMins}m`
        if (diffHours < 24) return `${diffHours}h`
        if (diffDays < 7) return `${diffDays}d`
        return date.toLocaleDateString([], { month: 'short', day: 'numeric' })
    }

    // Extract the domain / company name from the receiver email
    const companyName = group.receiver.split('@')[1]?.split('.')[0] || group.receiver
    const displayName = companyName.charAt(0).toUpperCase() + companyName.slice(1)

    return (
        <div
            onClick={onClick}
            className={cn(
                'group flex items-center gap-4 px-4 py-3.5 cursor-pointer transition-all duration-200 border-b',
                isSelected
                    ? 'bg-primary/5 ring-1 ring-inset ring-primary/20'
                    : 'hover:bg-muted/30'
            )}
        >
            {/* Company icon */}
            <div className="rounded-lg p-2.5 shrink-0 bg-blue-500/10">
                <Building2 className="h-5 w-5 text-blue-600 dark:text-blue-400" />
            </div>

            {/* Info */}
            <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                    <p className="text-sm font-semibold truncate">{displayName}</p>
                    <Badge variant="secondary" className="text-[10px] h-4 px-1.5 shrink-0">
                        {group.count} {t('documents.attachments')}
                    </Badge>
                </div>
                <p className="text-xs text-muted-foreground truncate mt-0.5">
                    {group.receiver}
                </p>
                <div className="flex items-center gap-3 mt-1 text-xs text-muted-foreground">
                    <span className="flex items-center gap-1">
                        <HardDrive className="h-3 w-3" />
                        {formatFileSize(totalSize)}
                    </span>
                    <span className="flex items-center gap-1">
                        <Files className="h-3 w-3" />
                        {uniqueTypes.size} {uniqueTypes.size === 1 ? 'type' : 'types'}
                    </span>
                    {latestDate && (
                        <span className="flex items-center gap-1">
                            <Clock className="h-3 w-3" />
                            {formatTimeAgo(latestDate)}
                        </span>
                    )}
                </div>
            </div>

            {/* Chevron */}
            <ChevronRight className="h-4 w-4 text-muted-foreground shrink-0 group-hover:translate-x-0.5 transition-transform" />
        </div>
    )
}
