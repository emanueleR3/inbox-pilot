'use client'

import { useState, useMemo, useRef, useEffect } from 'react'
import { CalendarEvent } from '@/lib/api/backend-service'
import { useLanguage } from '@/lib/context/language-context'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { EventCard } from './event-card'
import { EventDetailDialog } from './event-detail-dialog'
import { EventFormDialog, EventFormData } from './event-form-dialog'
import { ChevronLeft, ChevronRight, CalendarDays, Plus, Pencil, Trash2 } from 'lucide-react'
import { cn } from '@/lib/utils'

interface CalendarViewProps {
    events: CalendarEvent[]
    isLoading?: boolean
    onMonthChange?: (year: number, month: number) => void
    onCreateEvent?: (data: EventFormData) => Promise<void>
    onUpdateEvent?: (eventId: string, data: EventFormData) => Promise<void>
    onDeleteEvent?: (eventId: string) => Promise<void>
}

const DAYS_OF_WEEK = ['common.sunday', 'common.monday', 'common.tuesday', 'common.wednesday', 'common.thursday', 'common.friday', 'common.saturday']

export function CalendarView({ events, isLoading, onMonthChange, onCreateEvent, onUpdateEvent, onDeleteEvent }: CalendarViewProps) {
    const { t } = useLanguage()
    const [currentDate, setCurrentDate] = useState(new Date())
    const [selectedDate, setSelectedDate] = useState<Date>(new Date())
    const [selectedEvent, setSelectedEvent] = useState<CalendarEvent | null>(null)
    const [dialogOpen, setDialogOpen] = useState(false)

    // Form dialog state
    const [formDialogOpen, setFormDialogOpen] = useState(false)
    const [editingEvent, setEditingEvent] = useState<CalendarEvent | null>(null)
    const [isSubmitting, setIsSubmitting] = useState(false)
    const [isDeleting, setIsDeleting] = useState(false)

    // Update selected date when current date (month) changes, if needed
    // For now, let's keep selectedDate independent of month view unless user clicks

    const year = currentDate.getFullYear()
    const month = currentDate.getMonth()

    // Get calendar grid data
    const calendarDays = useMemo(() => {
        const firstDay = new Date(year, month, 1)
        const lastDay = new Date(year, month + 1, 0)
        const daysInMonth = lastDay.getDate()
        const startingDay = firstDay.getDay()

        const days: { date: Date; isCurrentMonth: boolean; events: CalendarEvent[] }[] = []

        // Previous month's days
        const prevMonthLastDay = new Date(year, month, 0).getDate()
        for (let i = startingDay - 1; i >= 0; i--) {
            const date = new Date(year, month - 1, prevMonthLastDay - i)
            days.push({ date, isCurrentMonth: false, events: [] })
        }

        // Current month's days
        for (let i = 1; i <= daysInMonth; i++) {
            const date = new Date(year, month, i)
            const dayEvents = events.filter(event => {
                const eventDate = new Date(event.start)
                return eventDate.getFullYear() === year &&
                    eventDate.getMonth() === month &&
                    eventDate.getDate() === i
            })
            days.push({ date, isCurrentMonth: true, events: dayEvents })
        }

        // Next month's days (to complete the grid)
        const remainingDays = 42 - days.length // 6 rows * 7 days
        for (let i = 1; i <= remainingDays; i++) {
            const date = new Date(year, month + 1, i)
            days.push({ date, isCurrentMonth: false, events: [] })
        }

        return days
    }, [year, month, events])

    // Get events for the selected date
    const selectedDateEvents = useMemo(() => {
        return events.filter(event => {
            const eventDate = new Date(event.start)
            return eventDate.getDate() === selectedDate.getDate() &&
                eventDate.getMonth() === selectedDate.getMonth() &&
                eventDate.getFullYear() === selectedDate.getFullYear()
        }).sort((a, b) => new Date(a.start).getTime() - new Date(b.start).getTime())
    }, [events, selectedDate])

    const goToPreviousMonth = () => {
        const newDate = new Date(year, month - 1, 1)
        setCurrentDate(newDate)
        onMonthChange?.(newDate.getFullYear(), newDate.getMonth())
    }

    const goToNextMonth = () => {
        const newDate = new Date(year, month + 1, 1)
        setCurrentDate(newDate)
        onMonthChange?.(newDate.getFullYear(), newDate.getMonth())
    }

    const goToToday = () => {
        const today = new Date()
        setCurrentDate(today)
        setSelectedDate(today)
        onMonthChange?.(today.getFullYear(), today.getMonth())
    }

    const handleDateClick = (date: Date) => {
        setSelectedDate(date)
        // If clicking a date in another month, optionally switch view
        if (date.getMonth() !== month) {
            setCurrentDate(date)
            onMonthChange?.(date.getFullYear(), date.getMonth())
        }
    }

    const handleEventClick = (event: CalendarEvent) => {
        setSelectedEvent(event)
        setDialogOpen(true)
    }

    const handleCreateClick = () => {
        setEditingEvent(null)
        setFormDialogOpen(true)
    }

    const handleEditEvent = (event: CalendarEvent) => {
        setDialogOpen(false)
        setEditingEvent(event)
        setFormDialogOpen(true)
    }

    const handleDeleteEvent = async (event: CalendarEvent) => {
        if (!onDeleteEvent) return
        setIsDeleting(true)
        try {
            await onDeleteEvent(event.id)
            setDialogOpen(false)
            setSelectedEvent(null)
        } finally {
            setIsDeleting(false)
        }
    }

    const handleFormSubmit = async (data: EventFormData) => {
        setIsSubmitting(true)
        try {
            if (editingEvent && onUpdateEvent) {
                await onUpdateEvent(editingEvent.id, data)
            } else if (onCreateEvent) {
                await onCreateEvent(data)
            }
            setFormDialogOpen(false)
            setEditingEvent(null)
        } finally {
            setIsSubmitting(false)
        }
    }

    const isToday = (date: Date) => {
        const today = new Date()
        return date.getDate() === today.getDate() &&
            date.getMonth() === today.getMonth() &&
            date.getFullYear() === today.getFullYear()
    }

    const isSelected = (date: Date) => {
        return date.getDate() === selectedDate.getDate() &&
            date.getMonth() === selectedDate.getMonth() &&
            date.getFullYear() === selectedDate.getFullYear()
    }

    const monthName = currentDate.toLocaleString('default', { month: 'long', year: 'numeric' })
    const selectedDateName = selectedDate.toLocaleDateString('default', { weekday: 'long', month: 'long', day: 'numeric' })

    // Generate hours for timeline
    const hours = Array.from({ length: 24 }, (_, i) => i)

    // Ref for the daily schedule scroll container
    const dailyScrollRef = useRef<HTMLDivElement>(null)

    // Auto-scroll the daily view: current time for today, 8 AM for other days
    useEffect(() => {
        const container = dailyScrollRef.current
        if (!container) return

        let scrollTarget: number
        if (isToday(selectedDate)) {
            const now = new Date()
            // Scroll so the current time is near the top (with a small offset for context)
            scrollTarget = now.getHours() * 60 + now.getMinutes() - 30
        } else {
            // 8:00 AM = 8 * 60 = 480px
            scrollTarget = 8 * 60 - 30
        }

        container.scrollTop = Math.max(0, scrollTarget)
    }, [selectedDate])

    // Helper to calculate event position and height
    const getEventStyle = (event: CalendarEvent) => {
        const start = new Date(event.start)
        const end = new Date(event.end)

        const startMinutes = start.getHours() * 60 + start.getMinutes()
        const endMinutes = end.getHours() * 60 + end.getMinutes()
        const durationMinutes = endMinutes - startMinutes

        // 60px per hour = 1px per minute
        const top = startMinutes // 1px per minute
        const height = Math.max(durationMinutes, 20) // Minimum 20px height

        return {
            top: `${top}px`,
            height: `${height}px`
        }
    }

    return (
        <div className="flex flex-col lg:flex-row gap-6 h-[800px]">
            {/* Main Calendar Grid */}
            <Card className="flex-1 lg:flex-[2] h-full flex flex-col min-h-0">
                <CardHeader className="pb-3 shrink-0">
                    <div className="flex items-center justify-between">
                        <CardTitle className="flex items-center gap-2">
                            <CalendarDays className="h-5 w-5" />
                            <span className="capitalize">{monthName}</span>
                        </CardTitle>
                        <div className="flex items-center gap-2">
                            {onCreateEvent && (
                                <Button
                                    size="sm"
                                    onClick={handleCreateClick}
                                    className="gap-1"
                                >
                                    <Plus className="h-4 w-4" />
                                    {t('calendar.newEvent')}
                                </Button>
                            )}
                            <Button
                                variant="outline"
                                size="sm"
                                onClick={goToToday}
                            >
                                {t('calendar.today')}
                            </Button>
                            <Button
                                variant="ghost"
                                size="icon"
                                onClick={goToPreviousMonth}
                                aria-label={t('calendar.previousMonth')}
                            >
                                <ChevronLeft className="h-4 w-4" />
                            </Button>
                            <Button
                                variant="ghost"
                                size="icon"
                                onClick={goToNextMonth}
                                aria-label={t('calendar.nextMonth')}
                            >
                                <ChevronRight className="h-4 w-4" />
                            </Button>
                        </div>
                    </div>
                </CardHeader>
                <CardContent className="flex-1 flex flex-col min-h-0 p-3 pt-0">
                    {/* Days of week header */}
                    <div className="grid grid-cols-7 gap-px mb-2 shrink-0">
                        {DAYS_OF_WEEK.map((day) => (
                            <div
                                key={day}
                                className="text-center text-sm font-medium text-muted-foreground py-2"
                            >
                                {t(day).slice(0, 3)}
                            </div>
                        ))}
                    </div>

                    {/* Calendar grid */}
                    <div className="grid grid-cols-7 grid-rows-6 gap-px bg-border rounded-lg overflow-hidden flex-1 border">
                        {calendarDays.map((day, index) => (
                            <div
                                key={index}
                                onClick={() => handleDateClick(day.date)}
                                className={cn(
                                    'bg-background p-1 sm:p-2 transition-colors cursor-pointer hover:bg-muted/30 flex flex-col gap-1 overflow-hidden min-h-0',
                                    !day.isCurrentMonth && 'bg-muted/20 text-muted-foreground',
                                    isSelected(day.date) && 'bg-primary/5 ring-1 ring-inset ring-primary'
                                )}
                            >
                                <div
                                    className={cn(
                                        'text-xs font-medium w-6 h-6 flex items-center justify-center rounded-full shrink-0',
                                        isToday(day.date)
                                            ? 'bg-primary text-primary-foreground'
                                            : isSelected(day.date) ? 'text-primary font-bold' : 'text-foreground',
                                        !day.isCurrentMonth && !isToday(day.date) && 'text-muted-foreground'
                                    )}
                                >
                                    {day.date.getDate()}
                                </div>

                                {/* Events in grid - limited view */}
                                <div className="flex-1 flex flex-col gap-1 overflow-hidden">
                                    {day.events.slice(0, 3).map((event) => (
                                        <div
                                            key={event.id}
                                            className={cn(
                                                "text-[10px] truncate px-1 rounded-sm border-l-2 shrink-0",
                                                event.created_by_ai
                                                    ? "bg-purple-500/10 border-purple-500 text-purple-700 dark:text-purple-300"
                                                    : "bg-blue-500/10 border-blue-500 text-blue-700 dark:text-blue-300"
                                            )}
                                        >
                                            {event.title}
                                        </div>
                                    ))}
                                    {day.events.length > 3 && (
                                        <div className="text-[10px] text-muted-foreground px-1 shrink-0">
                                            +{day.events.length - 3} more
                                        </div>
                                    )}
                                </div>
                            </div>
                        ))}
                    </div>
                </CardContent>
            </Card>

            {/* Daily Schedule - Right Side */}
            <Card className="flex-1 overflow-hidden h-full flex flex-col">
                <CardHeader className="pb-3 border-b shrink-0">
                    <CardTitle className="text-lg capitalize">
                        {selectedDateName}
                    </CardTitle>
                </CardHeader>
                <CardContent ref={dailyScrollRef} className="p-0 flex-1 overflow-y-auto relative min-h-0">
                    <div className="relative w-full" style={{ height: '1440px' }}> {/* 24 hours * 60px/hr = 1440px */}
                        {/* Time Grid */}
                        {hours.map((hour) => (
                            <div
                                key={hour}
                                className="absolute w-full border-b border-border/50 flex items-start"
                                style={{ top: `${hour * 60}px`, height: '60px' }}
                            >
                                <span className="text-xs text-muted-foreground w-12 text-right pr-2 -mt-2 bg-background">
                                    {hour.toString().padStart(2, '0')}:00
                                </span>
                                <div className="flex-1 h-full border-l border-border/30" />
                            </div>
                        ))}

                        {/* Events */}
                        {selectedDateEvents.map((event) => (
                            <div
                                key={event.id}
                                className={cn(
                                    "absolute left-14 right-2 rounded-md border-l-4 p-2 text-xs overflow-hidden cursor-pointer hover:brightness-95 transition-all shadow-sm z-10 group",
                                    event.created_by_ai
                                        ? "bg-purple-100 dark:bg-purple-900/40 border-purple-500 text-purple-900 dark:text-purple-100"
                                        : "bg-blue-100 dark:bg-blue-900/40 border-blue-500 text-blue-900 dark:text-blue-100"
                                )}
                                style={getEventStyle(event)}
                                onClick={() => handleEventClick(event)}
                            >
                                {/* Inline edit / delete buttons */}
                                {(onUpdateEvent || onDeleteEvent) && (
                                    <div className="absolute top-1 right-1 flex gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity z-20">
                                        {onUpdateEvent && (
                                            <button
                                                type="button"
                                                onClick={(e) => { e.stopPropagation(); handleEditEvent(event) }}
                                                className={cn(
                                                    "p-0.5 rounded hover:bg-black/10 dark:hover:bg-white/10 transition-colors",
                                                    event.created_by_ai ? "text-purple-700 dark:text-purple-200" : "text-blue-700 dark:text-blue-200"
                                                )}
                                                aria-label={t('calendar.editEvent')}
                                            >
                                                <Pencil className="h-3 w-3" />
                                            </button>
                                        )}
                                        {onDeleteEvent && (
                                            <button
                                                type="button"
                                                onClick={(e) => { e.stopPropagation(); handleDeleteEvent(event) }}
                                                className={cn(
                                                    "p-0.5 rounded hover:bg-black/10 dark:hover:bg-white/10 transition-colors",
                                                    event.created_by_ai ? "text-purple-700 dark:text-purple-200" : "text-blue-700 dark:text-blue-200"
                                                )}
                                                aria-label={t('calendar.deleteEvent')}
                                            >
                                                <Trash2 className="h-3 w-3" />
                                            </button>
                                        )}
                                    </div>
                                )}
                                <div className="font-semibold truncate pr-12">{event.title}</div>
                                <div className="opacity-80 truncate">
                                    {new Date(event.start).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                    {' - '}
                                    {new Date(event.end).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                </div>
                                {event.location && (
                                    <div className="opacity-70 truncate mt-0.5">{event.location}</div>
                                )}
                            </div>
                        ))}

                        {/* Current Time Indicator (if selected date is today) */}
                        {isToday(selectedDate) && (
                            <div
                                className="absolute left-12 right-0 border-t-2 border-red-500 z-20 pointer-events-none flex items-center"
                                style={{ top: `${new Date().getHours() * 60 + new Date().getMinutes()}px` }}
                            >
                                <div className="w-2 h-2 rounded-full bg-red-500 -ml-1" />
                            </div>
                        )}
                    </div>
                </CardContent>
            </Card>

            <EventDetailDialog
                event={selectedEvent}
                open={dialogOpen}
                onOpenChange={setDialogOpen}
                onEdit={onUpdateEvent ? handleEditEvent : undefined}
                onDelete={onDeleteEvent ? handleDeleteEvent : undefined}
                isDeleting={isDeleting}
            />

            <EventFormDialog
                open={formDialogOpen}
                onOpenChange={setFormDialogOpen}
                event={editingEvent}
                defaultDate={selectedDate}
                isSubmitting={isSubmitting}
                onSubmit={handleFormSubmit}
            />
        </div>
    )
}
