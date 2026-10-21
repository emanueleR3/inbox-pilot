'use client'

import { useState, useEffect } from 'react'
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
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Switch } from '@/components/ui/switch'
import { Badge } from '@/components/ui/badge'
import { Loader2, X, Plus } from 'lucide-react'

interface EventFormDialogProps {
    open: boolean
    onOpenChange: (open: boolean) => void
    event?: CalendarEvent | null  // If provided, we're editing
    defaultDate?: Date             // Pre-fill date for new events
    isSubmitting?: boolean
    onSubmit: (data: EventFormData) => void
}

export interface EventFormData {
    title: string
    description: string
    location: string
    start: string  // datetime-local value
    end: string
    is_all_day: boolean
    attendees: string[]
}

function toDatetimeLocal(date: Date): string {
    const pad = (n: number) => n.toString().padStart(2, '0')
    return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`
}

function toDateOnly(date: Date): string {
    const pad = (n: number) => n.toString().padStart(2, '0')
    return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`
}

export function EventFormDialog({
    open,
    onOpenChange,
    event,
    defaultDate,
    isSubmitting = false,
    onSubmit,
}: EventFormDialogProps) {
    const { t } = useLanguage()
    const isEditing = !!event

    const [title, setTitle] = useState('')
    const [description, setDescription] = useState('')
    const [location, setLocation] = useState('')
    const [start, setStart] = useState('')
    const [end, setEnd] = useState('')
    const [isAllDay, setIsAllDay] = useState(false)
    const [attendees, setAttendees] = useState<string[]>([])
    const [attendeeInput, setAttendeeInput] = useState('')

    // Reset form when dialog opens
    useEffect(() => {
        if (!open) return

        if (event) {
            // Editing: populate from event
            setTitle(event.title)
            setDescription(event.description || '')
            setLocation(event.location || '')
            setIsAllDay(event.is_all_day)

            if (event.is_all_day) {
                setStart(toDateOnly(new Date(event.start)))
                setEnd(toDateOnly(new Date(event.end)))
            } else {
                setStart(toDatetimeLocal(new Date(event.start)))
                setEnd(toDatetimeLocal(new Date(event.end)))
            }

            setAttendees(event.attendees?.map(a => a.email) || [])
        } else {
            // Creating: defaults
            const baseDate = defaultDate || new Date()
            const startDate = new Date(baseDate)
            startDate.setMinutes(0, 0, 0)
            if (startDate < new Date()) {
                startDate.setHours(new Date().getHours() + 1)
            }
            const endDate = new Date(startDate)
            endDate.setHours(endDate.getHours() + 1)

            setTitle('')
            setDescription('')
            setLocation('')
            setIsAllDay(false)
            setStart(toDatetimeLocal(startDate))
            setEnd(toDatetimeLocal(endDate))
            setAttendees([])
        }
        setAttendeeInput('')
    }, [open, event, defaultDate])

    const handleAddAttendee = () => {
        const email = attendeeInput.trim().toLowerCase()
        if (email && /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email) && !attendees.includes(email)) {
            setAttendees(prev => [...prev, email])
            setAttendeeInput('')
        }
    }

    const handleAttendeeKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
        if (e.key === 'Enter') {
            e.preventDefault()
            handleAddAttendee()
        }
    }

    const handleRemoveAttendee = (email: string) => {
        setAttendees(prev => prev.filter(a => a !== email))
    }

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault()
        if (!title.trim() || !start || !end) return

        onSubmit({
            title: title.trim(),
            description: description.trim(),
            location: location.trim(),
            start,
            end,
            is_all_day: isAllDay,
            attendees,
        })
    }

    const isValid = title.trim() && start && end

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-lg max-h-[90vh] overflow-y-auto">
                <DialogHeader>
                    <DialogTitle>
                        {isEditing ? t('calendar.editEvent') : t('calendar.newEvent')}
                    </DialogTitle>
                    <DialogDescription>
                        {isEditing
                            ? t('calendar.editEvent')
                            : t('calendar.createEvent')
                        }
                    </DialogDescription>
                </DialogHeader>

                <form onSubmit={handleSubmit} className="space-y-4 mt-2">
                    {/* Title */}
                    <div className="space-y-2">
                        <Label htmlFor="event-title">{t('calendar.eventTitle')} *</Label>
                        <Input
                            id="event-title"
                            value={title}
                            onChange={(e) => setTitle(e.target.value)}
                            placeholder={t('calendar.eventTitlePlaceholder') || ''}
                            disabled={isSubmitting}
                            required
                        />
                    </div>

                    {/* All Day Toggle */}
                    <div className="flex items-center gap-3">
                        <Switch
                            id="all-day"
                            checked={isAllDay}
                            onCheckedChange={(checked) => {
                                setIsAllDay(checked)
                                // Convert between datetime-local and date
                                if (checked && start) {
                                    setStart(start.split('T')[0])
                                    setEnd(end.split('T')[0])
                                } else if (!checked && start) {
                                    setStart(start + 'T09:00')
                                    setEnd(end + 'T10:00')
                                }
                            }}
                            disabled={isSubmitting}
                        />
                        <Label htmlFor="all-day">{t('calendar.eventAllDay')}</Label>
                    </div>

                    {/* Start / End */}
                    <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-2">
                            <Label htmlFor="event-start">{t('calendar.eventStart')} *</Label>
                            <Input
                                id="event-start"
                                type={isAllDay ? 'date' : 'datetime-local'}
                                value={start}
                                onChange={(e) => setStart(e.target.value)}
                                disabled={isSubmitting}
                                required
                            />
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="event-end">{t('calendar.eventEnd')} *</Label>
                            <Input
                                id="event-end"
                                type={isAllDay ? 'date' : 'datetime-local'}
                                value={end}
                                onChange={(e) => setEnd(e.target.value)}
                                disabled={isSubmitting}
                                required
                            />
                        </div>
                    </div>

                    {/* Location */}
                    <div className="space-y-2">
                        <Label htmlFor="event-location">{t('calendar.eventLocation')}</Label>
                        <Input
                            id="event-location"
                            value={location}
                            onChange={(e) => setLocation(e.target.value)}
                            placeholder={t('calendar.eventLocationPlaceholder') || ''}
                            disabled={isSubmitting}
                        />
                    </div>

                    {/* Description */}
                    <div className="space-y-2">
                        <Label htmlFor="event-description">{t('calendar.eventDescription')}</Label>
                        <Textarea
                            id="event-description"
                            value={description}
                            onChange={(e) => setDescription(e.target.value)}
                            placeholder={t('calendar.eventDescriptionPlaceholder') || ''}
                            className="min-h-[80px] resize-y"
                            disabled={isSubmitting}
                        />
                    </div>

                    {/* Attendees */}
                    <div className="space-y-2">
                        <Label>{t('calendar.eventAttendees')}</Label>
                        <div className="flex gap-2">
                            <Input
                                type="email"
                                value={attendeeInput}
                                onChange={(e) => setAttendeeInput(e.target.value)}
                                onKeyDown={handleAttendeeKeyDown}
                                placeholder={t('calendar.eventAttendeesPlaceholder') || ''}
                                disabled={isSubmitting}
                                className="flex-1"
                            />
                            <Button
                                type="button"
                                variant="outline"
                                size="icon"
                                onClick={handleAddAttendee}
                                disabled={isSubmitting || !attendeeInput.trim()}
                            >
                                <Plus className="h-4 w-4" />
                            </Button>
                        </div>
                        {attendees.length > 0 && (
                            <div className="flex flex-wrap gap-1.5 mt-2">
                                {attendees.map((email) => (
                                    <Badge key={email} variant="secondary" className="gap-1 pr-1">
                                        {email}
                                        <button
                                            type="button"
                                            onClick={() => handleRemoveAttendee(email)}
                                            className="ml-1 hover:text-destructive transition-colors"
                                            disabled={isSubmitting}
                                        >
                                            <X className="h-3 w-3" />
                                        </button>
                                    </Badge>
                                ))}
                            </div>
                        )}
                    </div>

                    <DialogFooter className="gap-2 pt-2">
                        <Button
                            type="button"
                            variant="outline"
                            onClick={() => onOpenChange(false)}
                            disabled={isSubmitting}
                        >
                            {t('calendar.cancel')}
                        </Button>
                        <Button
                            type="submit"
                            disabled={!isValid || isSubmitting}
                            className="gap-2"
                        >
                            {isSubmitting ? (
                                <>
                                    <Loader2 className="h-4 w-4 animate-spin" />
                                    {isEditing ? t('calendar.saving') : t('calendar.creating')}
                                </>
                            ) : (
                                isEditing ? t('calendar.saveChanges') : t('calendar.createEvent')
                            )}
                        </Button>
                    </DialogFooter>
                </form>
            </DialogContent>
        </Dialog>
    )
}
