'use client'

import { Attachment } from '@/lib/api/backend-service'
import { useLanguage } from '@/lib/context/language-context'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
    FileText,
    FileImage,
    FileSpreadsheet,
    FileArchive,
    File,
    Download,
    Eye,
    Clock,
    User,
} from 'lucide-react'
import { cn } from '@/lib/utils'

interface AttachmentCardProps {
    attachment: Attachment
    variant?: 'grid' | 'list'
    isSelected?: boolean
    onClick?: () => void
    onPreview?: () => void
    onDownload?: () => void
}

const FILE_TYPE_CONFIG: Record<string, { icon: typeof File; color: string; bgColor: string; label: string }> = {
    'application/pdf': { icon: FileText, color: 'text-red-600 dark:text-red-400', bgColor: 'bg-red-500/10', label: 'PDF' },
    'image/png': { icon: FileImage, color: 'text-blue-600 dark:text-blue-400', bgColor: 'bg-blue-500/10', label: 'PNG' },
    'image/jpeg': { icon: FileImage, color: 'text-blue-600 dark:text-blue-400', bgColor: 'bg-blue-500/10', label: 'JPG' },
    'image/gif': { icon: FileImage, color: 'text-purple-600 dark:text-purple-400', bgColor: 'bg-purple-500/10', label: 'GIF' },
    'image/webp': { icon: FileImage, color: 'text-blue-600 dark:text-blue-400', bgColor: 'bg-blue-500/10', label: 'WEBP' },
    'image/svg+xml': { icon: FileImage, color: 'text-orange-600 dark:text-orange-400', bgColor: 'bg-orange-500/10', label: 'SVG' },
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': { icon: FileSpreadsheet, color: 'text-green-600 dark:text-green-400', bgColor: 'bg-green-500/10', label: 'XLSX' },
    'application/vnd.ms-excel': { icon: FileSpreadsheet, color: 'text-green-600 dark:text-green-400', bgColor: 'bg-green-500/10', label: 'XLS' },
    'text/csv': { icon: FileSpreadsheet, color: 'text-green-600 dark:text-green-400', bgColor: 'bg-green-500/10', label: 'CSV' },
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': { icon: FileText, color: 'text-blue-700 dark:text-blue-300', bgColor: 'bg-blue-600/10', label: 'DOCX' },
    'application/msword': { icon: FileText, color: 'text-blue-700 dark:text-blue-300', bgColor: 'bg-blue-600/10', label: 'DOC' },
    'application/zip': { icon: FileArchive, color: 'text-amber-600 dark:text-amber-400', bgColor: 'bg-amber-500/10', label: 'ZIP' },
    'application/x-rar-compressed': { icon: FileArchive, color: 'text-amber-600 dark:text-amber-400', bgColor: 'bg-amber-500/10', label: 'RAR' },
    'text/plain': { icon: FileText, color: 'text-gray-600 dark:text-gray-400', bgColor: 'bg-gray-500/10', label: 'TXT' },
}

function getFileConfig(mimeType: string) {
    if (FILE_TYPE_CONFIG[mimeType]) return FILE_TYPE_CONFIG[mimeType]
    if (mimeType.startsWith('image/')) return { icon: FileImage, color: 'text-blue-600 dark:text-blue-400', bgColor: 'bg-blue-500/10', label: mimeType.split('/')[1]?.toUpperCase() || 'IMG' }
    if (mimeType.startsWith('text/')) return { icon: FileText, color: 'text-gray-600 dark:text-gray-400', bgColor: 'bg-gray-500/10', label: 'TXT' }
    return { icon: File, color: 'text-muted-foreground', bgColor: 'bg-muted', label: mimeType.split('/')[1]?.toUpperCase() || 'FILE' }
}

export function formatFileSize(bytes: number): string {
    if (bytes === 0) return '0 B'
    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i]
}

export function AttachmentCard({ attachment, variant = 'list', isSelected, onClick, onPreview, onDownload }: AttachmentCardProps) {
    const { t } = useLanguage()
    const config = getFileConfig(attachment.mime_type)
    const Icon = config.icon

    const formatDate = (dateString: string) => {
        const date = new Date(dateString)
        return date.toLocaleDateString([], { month: 'short', day: 'numeric', year: 'numeric' })
    }

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
        return formatDate(dateString)
    }

    if (variant === 'grid') {
        return (
            <div
                onClick={onClick}
                className={cn(
                    'group relative flex flex-col items-center gap-3 rounded-lg border p-4 cursor-pointer transition-all duration-200 hover:shadow-md',
                    isSelected
                        ? 'bg-primary/5 ring-1 ring-primary border-primary/30'
                        : 'bg-background hover:bg-muted/30'
                )}
            >
                <div className={cn('rounded-xl p-4', config.bgColor)}>
                    <Icon className={cn('h-8 w-8', config.color)} />
                </div>

                <div className="text-center w-full min-w-0">
                    <p className="text-sm font-medium truncate" title={attachment.file_name}>
                        {attachment.file_name}
                    </p>
                    <p className="text-xs text-muted-foreground mt-0.5">
                        {formatFileSize(attachment.size_bytes)}
                    </p>
                </div>

                <Badge variant="outline" className={cn('text-[10px]', config.bgColor, config.color)}>
                    {config.label}
                </Badge>

                {/* Hover actions */}
                <div className="absolute top-2 right-2 flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    {onPreview && (
                        <Button
                            variant="ghost"
                            size="icon"
                            className="h-7 w-7"
                            onClick={(e) => { e.stopPropagation(); onPreview() }}
                        >
                            <Eye className="h-3.5 w-3.5" />
                        </Button>
                    )}
                    {onDownload && (
                        <Button
                            variant="ghost"
                            size="icon"
                            className="h-7 w-7"
                            onClick={(e) => { e.stopPropagation(); onDownload() }}
                        >
                            <Download className="h-3.5 w-3.5" />
                        </Button>
                    )}
                </div>
            </div>
        )
    }

    // List variant
    return (
        <div
            onClick={onClick}
            className={cn(
                'group flex items-center gap-4 px-4 py-3 cursor-pointer transition-all duration-200 border-b',
                isSelected
                    ? 'bg-primary/5 ring-1 ring-inset ring-primary/20'
                    : 'hover:bg-muted/30'
            )}
        >
            <div className={cn('rounded-lg p-2.5 shrink-0', config.bgColor)}>
                <Icon className={cn('h-5 w-5', config.color)} />
            </div>

            <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                    <p className="text-sm font-medium truncate">{attachment.file_name}</p>
                    <Badge variant="outline" className={cn('text-[10px] shrink-0', config.bgColor, config.color)}>
                        {config.label}
                    </Badge>
                </div>
                <div className="flex items-center gap-3 mt-1 text-xs text-muted-foreground">
                    <span className="flex items-center gap-1 truncate">
                        <User className="h-3 w-3 shrink-0" />
                        {attachment.sender}
                    </span>
                    <span className="shrink-0">{formatFileSize(attachment.size_bytes)}</span>
                </div>
            </div>

            <div className="flex items-center gap-2 shrink-0">
                <span className="text-xs text-muted-foreground flex items-center gap-1">
                    <Clock className="h-3 w-3" />
                    {formatTimeAgo(attachment.created_at)}
                </span>

                <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    {onPreview && (
                        <Button
                            variant="ghost"
                            size="icon"
                            className="h-7 w-7"
                            onClick={(e) => { e.stopPropagation(); onPreview() }}
                            title={t('documents.preview')}
                        >
                            <Eye className="h-3.5 w-3.5" />
                        </Button>
                    )}
                    {onDownload && (
                        <Button
                            variant="ghost"
                            size="icon"
                            className="h-7 w-7"
                            onClick={(e) => { e.stopPropagation(); onDownload() }}
                            title={t('documents.download')}
                        >
                            <Download className="h-3.5 w-3.5" />
                        </Button>
                    )}
                </div>
            </div>
        </div>
    )
}

export { getFileConfig }
