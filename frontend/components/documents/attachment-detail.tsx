'use client'

import { Attachment } from '@/lib/api/backend-service'
import { useLanguage } from '@/lib/context/language-context'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import {
    ArrowLeft,
    Download,
    Eye,
    Mail,
    Clock,
    User,
    Users,
    HardDrive,
    FileText,
    Copy,
    Check,
} from 'lucide-react'
import { getFileConfig, formatFileSize } from './attachment-card'
import { cn } from '@/lib/utils'
import { useState } from 'react'

interface AttachmentDetailProps {
    attachment: Attachment
    onBack: () => void
    onPreview?: () => void
    onDownload?: () => void
}

export function AttachmentDetail({ attachment, onBack, onPreview, onDownload }: AttachmentDetailProps) {
    const { t } = useLanguage()
    const config = getFileConfig(attachment.mime_type)
    const Icon = config.icon
    const [copiedField, setCopiedField] = useState<string | null>(null)

    const formatDate = (dateString: string) => {
        const date = new Date(dateString)
        return date.toLocaleDateString([], {
            weekday: 'long',
            year: 'numeric',
            month: 'long',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
        })
    }

    const copyToClipboard = (text: string, field: string) => {
        navigator.clipboard.writeText(text)
        setCopiedField(field)
        setTimeout(() => setCopiedField(null), 2000)
    }

    const DetailRow = ({ label, value, copyable = false }: { label: string; value: string; copyable?: boolean }) => (
        <div className="flex items-start justify-between gap-4 py-2">
            <span className="text-sm text-muted-foreground shrink-0">{label}</span>
            <div className="flex items-center gap-1.5 min-w-0">
                <span className="text-sm font-medium text-right truncate">{value}</span>
                {copyable && (
                    <Button
                        variant="ghost"
                        size="icon"
                        className="h-6 w-6 shrink-0"
                        onClick={() => copyToClipboard(value, label)}
                    >
                        {copiedField === label ? (
                            <Check className="h-3 w-3 text-green-500" />
                        ) : (
                            <Copy className="h-3 w-3" />
                        )}
                    </Button>
                )}
            </div>
        </div>
    )

    return (
        <div className="h-full flex flex-col min-h-0 overflow-hidden">
            {/* Header */}
            <div className="p-4 border-b bg-muted/30 shrink-0">
                <Button variant="ghost" size="sm" onClick={onBack} className="mb-3">
                    <ArrowLeft className="h-4 w-4 mr-1" />
                    {t('email.backToList')}
                </Button>

                <div className="flex items-start gap-4">
                    <div className={cn('rounded-xl p-3', config.bgColor)}>
                        <Icon className={cn('h-8 w-8', config.color)} />
                    </div>
                    <div className="flex-1 min-w-0">
                        <h2 className="text-lg font-semibold truncate" title={attachment.file_name}>
                            {attachment.file_name}
                        </h2>
                        <div className="flex items-center gap-2 mt-1 flex-wrap">
                            <Badge variant="outline" className={cn('text-xs', config.bgColor, config.color)}>
                                {config.label}
                            </Badge>
                            <span className="text-xs text-muted-foreground">
                                {formatFileSize(attachment.size_bytes)}
                            </span>
                        </div>
                    </div>
                </div>

                {/* Action buttons */}
                <div className="flex gap-2 mt-4">
                    {onPreview && (
                        <Button variant="outline" size="sm" onClick={onPreview} className="flex-1">
                            <Eye className="h-4 w-4 mr-2" />
                            {t('documents.preview')}
                        </Button>
                    )}
                    {onDownload && (
                        <Button size="sm" onClick={onDownload} className="flex-1">
                            <Download className="h-4 w-4 mr-2" />
                            {t('documents.download')}
                        </Button>
                    )}
                </div>
            </div>

            {/* Details */}
            <div className="flex-1 overflow-y-auto min-h-0 p-4 space-y-4">
                {/* Email Context / Subject */}
                {attachment.email_context && (
                    <div className="rounded-lg border bg-muted/40 p-4 space-y-3">
                        <div>
                            <h3 className="text-sm font-semibold text-foreground">
                                {attachment.email_context.subject || t('documents.noSubject')}
                            </h3>
                            <div className="flex gap-2 mt-2">
                                <Badge variant="secondary" className="bg-blue-100 text-blue-700 hover:bg-blue-100/80 dark:bg-blue-900/30 dark:text-blue-300">
                                    {t(`email.category.${attachment.email_context.category.toLowerCase().replace(/_([a-z])/g, (g) => g[1].toUpperCase())}`) ||
                                        attachment.email_context.category.replace(/_/g, ' ').toLowerCase().replace(/\b\w/g, l => l.toUpperCase())}
                                </Badge>
                                {attachment.email_context?.subcategory && (
                                    <Badge variant="outline">
                                        {attachment.email_context.subcategory}
                                    </Badge>
                                )}
                            </div>
                        </div>

                        {attachment.email_context.summary && (
                            <div className="mt-2 text-sm text-muted-foreground bg-background/50 p-3 rounded-md border">
                                <p>{attachment.email_context.summary}</p>
                            </div>
                        )}
                    </div>
                )}

                {/* File Info */}
                <div>
                    <h3 className="text-sm font-semibold flex items-center gap-2 mb-2">
                        <FileText className="h-4 w-4" />
                        {t('documents.details')}
                    </h3>
                    <div className="rounded-lg border bg-muted/20 px-4 divide-y">
                        <DetailRow label={t('documents.fileName')} value={attachment.file_name} copyable />
                        <DetailRow label={t('documents.type')} value={attachment.mime_type} />
                        <DetailRow label={t('documents.size')} value={formatFileSize(attachment.size_bytes)} />
                        {attachment.email_context?.started_at ? (
                            <DetailRow label={t('documents.date')} value={formatDate(attachment.email_context!.started_at)} />
                        ) : (
                            <DetailRow label={t('documents.date')} value={formatDate(attachment.created_at)} />
                        )}
                    </div>
                </div>

                <Separator />

                {/* Email Info */}
                <div>
                    <h3 className="text-sm font-semibold flex items-center gap-2 mb-2">
                        <Mail className="h-4 w-4" />
                        {t('documents.thread')}
                    </h3>
                    <div className="rounded-lg border bg-muted/20 px-4 divide-y">
                        <DetailRow
                            label={t('documents.sender')}
                            value={attachment.email_context?.sender_email || attachment.sender}
                            copyable
                        />
                        {/* Display receiver only if not in context or different, usually context captures it well */}
                        <DetailRow
                            label={t('documents.receiver')}
                            value={attachment.receiver}
                            copyable
                        />
                        {/* CC from context or fallback */}
                        {((attachment.email_context?.cc_emails && attachment.email_context.cc_emails.length > 0) || (attachment.cc && attachment.cc.length > 0)) && (
                            <DetailRow
                                label={t('documents.cc')}
                                value={(attachment.email_context?.cc_emails || attachment.cc || []).join(', ')}
                                copyable
                            />
                        )}
                    </div>
                </div>


            </div>
        </div>
    )
}
