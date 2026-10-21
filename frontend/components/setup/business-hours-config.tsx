'use client'

import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import { Switch } from '@/components/ui/switch'
import { Card, CardContent } from '@/components/ui/card'
import { Clock, Plus, Trash2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { useLanguage } from '@/lib/context/language-context'

interface BusinessHoursConfigProps {
    value: {
        duration: number
        hours: Record<string, string[]>
    }
    onChange: (value: { duration: number; hours: Record<string, string[]> }) => void
    disabled?: boolean
}

const DAYS = [
    { id: '0', key: 'common.monday' },
    { id: '1', key: 'common.tuesday' },
    { id: '2', key: 'common.wednesday' },
    { id: '3', key: 'common.thursday' },
    { id: '4', key: 'common.friday' },
    { id: '5', key: 'common.saturday' },
    { id: '6', key: 'common.sunday' },
]

export function BusinessHoursConfig({ value, onChange, disabled }: BusinessHoursConfigProps) {
    const { t } = useLanguage()

    const handleDurationChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const duration = parseInt(e.target.value) || 0
        onChange({ ...value, duration })
    }

    const handleDayToggle = (dayId: string, enabled: boolean) => {
        const newHours = { ...value.hours }
        if (enabled) {
            // Default 9-5 if enabled
            newHours[dayId] = ['09:00-17:00']
        } else {
            delete newHours[dayId]
        }
        onChange({ ...value, hours: newHours })
    }

    const handleTimeChange = (dayId: string, index: number, type: 'start' | 'end', time: string) => {
        const newHours = { ...value.hours }
        const ranges = [...(newHours[dayId] || [])]
        const [start, end] = ranges[index].split('-')

        if (type === 'start') {
            ranges[index] = `${time}-${end}`
        } else {
            ranges[index] = `${start}-${time}`
        }

        newHours[dayId] = ranges
        onChange({ ...value, hours: newHours })
    }

    const addTimeRange = (dayId: string) => {
        const newHours = { ...value.hours }
        const ranges = [...(newHours[dayId] || [])]
        ranges.push('09:00-17:00')
        newHours[dayId] = ranges
        onChange({ ...value, hours: newHours })
    }

    const removeTimeRange = (dayId: string, index: number) => {
        const newHours = { ...value.hours }
        const ranges = [...(newHours[dayId] || [])]
        ranges.splice(index, 1)

        if (ranges.length === 0) {
            delete newHours[dayId]
        } else {
            newHours[dayId] = ranges
        }
        onChange({ ...value, hours: newHours })
    }

    return (
        <div className="space-y-6">
            <div className="space-y-2">
                <Label htmlFor="duration" className="text-base font-medium flex items-center gap-2">
                    <Clock className="w-4 h-4" />
                    {t('setup.appointmentDuration')} ({t('common.minutes')})
                </Label>
                <Input
                    id="duration"
                    type="number"
                    min="15"
                    step="15"
                    value={value.duration}
                    onChange={handleDurationChange}
                    disabled={disabled}
                    placeholder="e.g. 30"
                    className="max-w-[200px]"
                />
                <p className="text-sm text-muted-foreground">
                    {t('setup.appointmentDurationHelp')}
                </p>
            </div>

            <div className="space-y-4">
                <Label className="text-base font-medium">{t('setup.businessHours')}</Label>
                <div className="grid gap-4">
                    {DAYS.map((day) => {
                        const isEnabled = !!value.hours[day.id]
                        const ranges = value.hours[day.id] || []

                        return (
                            <Card key={day.id} className={cn("transition-colors", isEnabled ? "border-primary/50 bg-primary/5" : "bg-muted/30")}>
                                <CardContent className="p-4">
                                    <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between">
                                        <div className="flex items-center gap-4 min-w-[140px]">
                                            <Switch
                                                checked={isEnabled}
                                                onCheckedChange={(checked) => handleDayToggle(day.id, checked)}
                                                disabled={disabled}
                                                id={`switch-${day.id}`}
                                            />
                                            <Label htmlFor={`switch-${day.id}`} className="font-medium cursor-pointer">
                                                {t(day.key)}
                                            </Label>
                                        </div>

                                        {isEnabled && (
                                            <div className="flex-1 w-full space-y-2">
                                                {ranges.map((range, index) => {
                                                    const [start, end] = range.split('-')
                                                    return (
                                                        <div key={index} className="flex items-center gap-2">
                                                            <Input
                                                                type="time"
                                                                value={start}
                                                                onChange={(e) => handleTimeChange(day.id, index, 'start', e.target.value)}
                                                                disabled={disabled}
                                                                className="w-[110px]"
                                                            />
                                                            <span className="text-muted-foreground">-</span>
                                                            <Input
                                                                type="time"
                                                                value={end}
                                                                onChange={(e) => handleTimeChange(day.id, index, 'end', e.target.value)}
                                                                disabled={disabled}
                                                                className="w-[110px]"
                                                            />
                                                            <Button
                                                                variant="ghost"
                                                                size="icon"
                                                                onClick={() => removeTimeRange(day.id, index)}
                                                                disabled={disabled}
                                                                className="h-9 w-9 text-muted-foreground hover:text-destructive"
                                                            >
                                                                <Trash2 className="h-4 w-4" />
                                                            </Button>
                                                        </div>
                                                    )
                                                })}
                                            </div>
                                        )}

                                        {isEnabled && (
                                            <Button
                                                variant="ghost"
                                                size="sm"
                                                onClick={() => addTimeRange(day.id)}
                                                disabled={disabled}
                                                className="mt-2 sm:mt-0"
                                            >
                                                <Plus className="h-4 w-4 mr-1" />
                                                {t('setup.addTime')}
                                            </Button>
                                        )}
                                    </div>
                                </CardContent>
                            </Card>
                        )
                    })}
                </div>
            </div>
        </div>
    )
}
