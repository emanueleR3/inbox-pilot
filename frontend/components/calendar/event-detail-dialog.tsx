'use client'

import { useState } from 'react'
import { CalendarEvent } from '@/lib/api/backend-service'
import { useLanguage } from '@/lib/context/language-context'
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
    DialogDescription,
    DialogFooter,
} from '@/components/ui/dialog'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Separator } from '@/components/ui/separator'
import {
    MapPin,
    User,
    Users,
    Bot,
    ExternalLink,
    Calendar,
    Clock,
    Pencil,
    Trash2,
    Loader2,
    AlertTriangle,
} from 'lucide-react'

interface EventDetailDialogProps {
    event: CalendarEvent | null
    open: boolean
    onOpenChange: (open: boolean) => void
    onEdit?: (event: CalendarEvent) => void
    onDelete?: (event: CalendarEvent) => void
    isDeleting?: boolean
}

export function EventDetailDialog({ event, open, onOpenChange, onEdit, onDelete, isDeleting = false }: EventDetailDialogProps) {
    const { t } = useLanguage()
    const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)

    if (!event) return null

    const formatTime = (dateString: string) => {

        const date = new Date(dateString)
        return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }

    const formatDate = (dateString: string) => {
        const date = new Date(dateString)
        return date.toLocaleDateString([], {
            weekday: 'long',
            year: 'numeric',
            month: 'long',
            day: 'numeric',
        })
    }

    const getStatusBadge = () => {
        const statusConfig = {
            confirmed: { label: t('calendar.confirmed'), variant: 'default' as const, className: 'bg-emerald-500' },
            tentative: { label: t('calendar.tentative'), variant: 'secondary' as const, className: 'bg-amber-500' },
            cancelled: { label: t('calendar.cancelled'), variant: 'destructive' as const, className: '' },
        }
        const config = statusConfig[event.status] || statusConfig.confirmed
        return (
            <Badge variant={config.variant} className={config.className}>
                {config.label}
            </Badge>
        )
    }

    const getResponseStatusLabel = (status?: string) => {
        switch (status) {
            case 'accepted': return t('calendar.accepted')
            case 'declined': return t('calendar.declined')
            case 'tentative': return t('calendar.tentative')
            default: return t('calendar.pending')
        }
    }

    const isAIGenerated = event.thread_summary !== 'Evento non generato da email gestita da AI'

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-lg">
                <DialogHeader>
                    <div className="flex items-start justify-between gap-4">
                        <div>
                            <DialogTitle className="text-xl">{event.title}</DialogTitle>
                            <DialogDescription className="mt-1 flex items-center gap-2">
                                {getStatusBadge()}
                                {isAIGenerated && (
                                    <Badge variant="outline" className="gap-1 bg-violet-500/10 text-violet-600 dark:text-violet-400 border-violet-500/20">
                                        <Bot className="h-3 w-3" />
                                        AI Generated
                                    </Badge>
                                )}
                            </DialogDescription>
                        </div>
                    </div>
                </DialogHeader>

                <div className="space-y-4 mt-4">
                    {/* Time */}
                    <div className="flex items-start gap-3">
                        <Clock className="h-5 w-5 text-muted-foreground mt-0.5" />
                        <div>
                            {event.is_all_day ? (
                                <div>
                                    <p className="font-medium">{t('calendar.allDay')}</p>
                                    <p className="text-sm text-muted-foreground">{formatDate(event.start)}</p>
                                </div>
                            ) : (
                                <div>
                                    <p className="font-medium">{formatTime(event.start)} - {formatTime(event.end)}</p>
                                    <p className="text-sm text-muted-foreground">{formatDate(event.start)}</p>
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Location */}
                    {event.location && (
                        <div className="flex items-start gap-3">
                            <MapPin className="h-5 w-5 text-muted-foreground mt-0.5" />
                            <div>
                                <p className="font-medium">{t('calendar.location')}</p>
                                <p className="text-sm text-muted-foreground">{event.location}</p>
                            </div>
                        </div>
                    )}

                    {/* Organizer */}
                    {event.organizer && (
                        <div className="flex items-start gap-3">
                            <User className="h-5 w-5 text-muted-foreground mt-0.5" />
                            <div>
                                <p className="font-medium">{t('calendar.organizer')}</p>
                                <p className="text-sm text-muted-foreground">
                                    {event.organizer.name || event.organizer.email}
                                </p>
                            </div>
                        </div>
                    )}

                    {/* Attendees */}
                    {event.attendees && event.attendees.length > 0 && (
                        <div className="flex items-start gap-3">
                            <Users className="h-5 w-5 text-muted-foreground mt-0.5" />
                            <div className="flex-1">
                                <p className="font-medium">{t('calendar.attendees')}</p>
                                <div className="mt-1 space-y-1">
                                    {event.attendees.slice(0, 5).map((attendee, index) => (
                                        <div key={index} className="flex items-center justify-between text-sm">
                                            <span className="text-muted-foreground">
                                                {attendee.name || attendee.email}
                                            </span>
                                            <Badge variant="outline" className="text-xs">
                                                {getResponseStatusLabel(attendee.response_status)}
                                            </Badge>
                                        </div>
                                    ))}
                                    {event.attendees.length > 5 && (
                                        <p className="text-xs text-muted-foreground">
                                            +{event.attendees.length - 5} more
                                        </p>
                                    )}
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Description */}
                    {event.description && (
                        <>
                            <Separator />
                            <div>
                                <p className="text-sm text-muted-foreground whitespace-pre-wrap">
                                    {event.description}
                                </p>
                            </div>
                        </>
                    )}

                    {/* AI Summary */}
                    {isAIGenerated && (
                        <>
                            <Separator />
                            <div className="rounded-lg bg-violet-500/10 p-3 border border-violet-500/20">
                                <div className="flex items-center gap-2 mb-2">
                                    <Bot className="h-4 w-4 text-violet-600 dark:text-violet-400" />
                                    <span className="font-medium text-sm text-violet-600 dark:text-violet-400">
                                        {t('calendar.threadSummary')}
                                    </span>
                                </div>
                                <p className="text-sm text-muted-foreground">
                                    {event.thread_summary}
                                </p>
                            </div>
                        </>
                    )}

                    {/* Actions */}
                    <Separator />

                    {/* Delete Confirmation */}
                    {showDeleteConfirm ? (
                        <div className="rounded-lg border border-destructive/30 bg-destructive/5 p-3 space-y-3">
                            <div className="flex items-center gap-2 text-sm font-medium text-destructive">
                                <AlertTriangle className="h-4 w-4" />
                                {t('calendar.deleteConfirm')}
                            </div>
                            <p className="text-xs text-muted-foreground">
                                {t('calendar.deleteConfirmDescription')}
                            </p>
                            <div className="flex gap-2 justify-end">
                                <Button
                                    variant="outline"
                                    size="sm"
                                    onClick={() => setShowDeleteConfirm(false)}
                                    disabled={isDeleting}
                                >
                                    {t('calendar.cancel')}
                                </Button>
                                <Button
                                    variant="destructive"
                                    size="sm"
                                    onClick={() => {
                                        onDelete?.(event)
                                        setShowDeleteConfirm(false)
                                    }}
                                    disabled={isDeleting}
                                    className="gap-2"
                                >
                                    {isDeleting ? (
                                        <>
                                            <Loader2 className="h-3 w-3 animate-spin" />
                                            {t('calendar.deleting')}
                                        </>
                                    ) : (
                                        <>
                                            <Trash2 className="h-3 w-3" />
                                            {t('calendar.deleteEvent')}
                                        </>
                                    )}
                                </Button>
                            </div>
                        </div>
                    ) : (
                        <div className="flex gap-2">
                            {event.html_link && (
                                <Button variant="outline" className="flex-1" asChild>
                                    <a href={event.html_link} target="_blank" rel="noopener noreferrer">
                                        <Calendar className="h-4 w-4 mr-2" />
                                        {t('calendar.openInCalendar')}
                                        <ExternalLink className="h-4 w-4 ml-2" />
                                    </a>
                                </Button>
                            )}
                            {onEdit && (
                                <Button
                                    variant="outline"
                                    size="icon"
                                    onClick={() => onEdit(event)}
                                >
                                    <Pencil className="h-4 w-4" />
                                </Button>
                            )}
                            {onDelete && (
                                <Button
                                    variant="outline"
                                    size="icon"
                                    className="text-destructive hover:text-destructive"
                                    onClick={() => setShowDeleteConfirm(true)}
                                >
                                    <Trash2 className="h-4 w-4" />
                                </Button>
                            )}
                        </div>
                    )}
                </div>
            </DialogContent>
        </Dialog>
    )
}
