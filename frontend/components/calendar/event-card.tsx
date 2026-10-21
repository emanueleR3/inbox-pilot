'use client'

import { CalendarEvent } from '@/lib/api/backend-service'
import { useLanguage } from '@/lib/context/language-context'
import { Badge } from '@/components/ui/badge'
import { Bot, Clock, MapPin } from 'lucide-react'
import { cn } from '@/lib/utils'

interface EventCardProps {
    event: CalendarEvent
    onClick?: () => void
}

export function EventCard({ event, onClick }: EventCardProps) {
    const { t } = useLanguage()

    const formatTime = (dateString: string) => {
        const date = new Date(dateString)
        return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }

    const getStatusColor = () => {
        switch (event.status) {
            case 'confirmed':
                return 'bg-emerald-500/10 border-emerald-500/20 hover:bg-emerald-500/15'
            case 'tentative':
                return 'bg-amber-500/10 border-amber-500/20 hover:bg-amber-500/15'
            case 'cancelled':
                return 'bg-red-500/10 border-red-500/20 hover:bg-red-500/15 opacity-60'
            default:
                return 'bg-primary/10 border-primary/20 hover:bg-primary/15'
        }
    }

    const isAIGenerated = event.thread_summary !== 'Evento non generato da email gestita da AI'

    return (
        <div
            onClick={onClick}
            className={cn(
                'group p-3 rounded-lg border cursor-pointer transition-all duration-200',
                getStatusColor()
            )}
        >
            <div className="flex items-start justify-between gap-2">
                <div className="flex-1 min-w-0">
                    <h4 className="font-medium text-sm truncate group-hover:text-primary transition-colors">
                        {event.title}
                    </h4>

                    <div className="flex items-center gap-2 mt-1 text-xs text-muted-foreground">
                        <Clock className="h-3 w-3 flex-shrink-0" />
                        {event.is_all_day ? (
                            <span>{t('calendar.allDay')}</span>
                        ) : (
                            <span>
                                {formatTime(event.start)} - {formatTime(event.end)}
                            </span>
                        )}
                    </div>

                    {event.location && (
                        <div className="flex items-center gap-2 mt-1 text-xs text-muted-foreground">
                            <MapPin className="h-3 w-3 flex-shrink-0" />
                            <span className="truncate">{event.location}</span>
                        </div>
                    )}
                </div>

                <div className="flex flex-col items-end gap-1">
                    {isAIGenerated && (
                        <Badge variant="outline" className="text-xs gap-1 bg-violet-500/10 text-violet-600 dark:text-violet-400 border-violet-500/20">
                            <Bot className="h-3 w-3" />
                            AI
                        </Badge>
                    )}
                </div>
            </div>
        </div>
    )
}
