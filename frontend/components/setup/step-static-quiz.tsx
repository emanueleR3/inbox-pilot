'use client'

import { useState, useEffect } from 'react'
import { useSetup } from '@/lib/context/setup-context'
import { useAuth } from '@/lib/context/auth-context'
import { useLanguage } from '@/lib/context/language-context'
import { backendService, CalendarBusinessHours } from '@/lib/api/backend-service'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { toast } from 'sonner'
import { Loader2, Plus, Trash2 } from 'lucide-react'
import confetti from 'canvas-confetti'

// Default Business Hours: Mon-Fri 09:00-17:00
const DEFAULT_BUSINESS_HOURS: CalendarBusinessHours = {
    '0': ['09:00-17:00'], // Mon
    '1': ['09:00-17:00'], // Tue
    '2': ['09:00-17:00'], // Wed
    '3': ['09:00-17:00'], // Thu
    '4': ['09:00-17:00'], // Fri
}

const APPOINTMENT_DURATIONS = [15, 30, 45, 60, 90, 120]

const DAYS = ['common.monday', 'common.tuesday', 'common.wednesday', 'common.thursday', 'common.friday', 'common.saturday', 'common.sunday']

export function StepStaticQuiz() {
    const { markStepComplete, goToPreviousStep, connectedEmail, calendarProvider, serviceId } = useSetup()
    const { currentSubscription, markSubscriptionConfigured, updateServiceInSubscription, activeServiceId } = useAuth()
    const { t } = useLanguage()

    const [isLoading, setIsLoading] = useState(true)
    const [isSaving, setIsSaving] = useState(false)
    const [businessHours, setBusinessHours] = useState<CalendarBusinessHours>(DEFAULT_BUSINESS_HOURS)
    const [appointmentDuration, setAppointmentDuration] = useState<string>('30')
    const [emailSignature, setEmailSignature] = useState('')
    const [toneOfVoice, setToneOfVoice] = useState('')
    // phoneNumbers is a list of { name, number } to support dynamic keys
    const [phoneNumbers, setPhoneNumbers] = useState<{ name: string, number: string }[]>([])
    const [isDraft, setIsDraft] = useState(false)

    useEffect(() => {
        const fetchCalendarInfo = async () => {
            try {
                // Attempt to fetch existing config
                try {
                    console.log('[SETUP DEBUG] step-static-quiz → GET /get-calendar-information')
                    const response = await backendService.getCalendarInformation()
                    console.log('[SETUP DEBUG] step-static-quiz → GET /get-calendar-information RESPONSE', response)
                    if (response && response.result) {
                        const data = response.result
                        if (typeof data === 'string') {
                            try {
                                const parsed = JSON.parse(data)
                                if (parsed && typeof parsed === 'object') {
                                    if (parsed.business_hours) setBusinessHours(parsed.business_hours)
                                    if (parsed.appointment_duration) setAppointmentDuration(parsed.appointment_duration.toString())
                                    if (parsed.email_signature) setEmailSignature(parsed.email_signature)
                                    if (parsed.tone_of_voice) setToneOfVoice(parsed.tone_of_voice)
                                    if (parsed.tone_of_voice) setToneOfVoice(parsed.tone_of_voice)
                                    if (parsed.phone_numbers) {
                                        const phones: { name: string, number: string }[] = []
                                        if (typeof parsed.phone_numbers === 'object' && !Array.isArray(parsed.phone_numbers)) {
                                            Object.entries(parsed.phone_numbers).forEach(([key, val]) => {
                                                if (typeof val === 'string') phones.push({ name: key, number: val })
                                            })
                                        }
                                        setPhoneNumbers(phones)
                                    }
                                }
                            } catch (e) {
                                console.warn('Failed to parse calendar info result string', e)
                            }
                        } else {
                            if (data.business_hours) setBusinessHours(data.business_hours)
                            if (data.appointment_duration) setAppointmentDuration(data.appointment_duration.toString())
                            if (data.email_signature) setEmailSignature(data.email_signature)
                            if (data.tone_of_voice) setToneOfVoice(data.tone_of_voice)
                            if (data.phone_numbers) {
                                const phones: { name: string, number: string }[] = []
                                if (typeof data.phone_numbers === 'object' && !Array.isArray(data.phone_numbers)) {
                                    Object.entries(data.phone_numbers).forEach(([key, val]) => {
                                        if (typeof val === 'string') phones.push({ name: key, number: val })
                                    })
                                }
                                setPhoneNumbers(phones)
                            }
                        }
                    }
                } catch (err) {
                    // Ignore 404/empty state if it's first time
                }
            } catch (error) {
                console.error('Failed to init calendar step:', error)
            } finally {
                setIsLoading(false)
            }
        }

        fetchCalendarInfo()
    }, [])

    const handleDayToggle = (dayIndex: number) => {
        setBusinessHours(prev => {
            const idxStr = dayIndex.toString()
            const newHours = { ...prev }
            if (newHours[idxStr]) {
                delete newHours[idxStr]
            } else {
                newHours[idxStr] = ['09:00-17:00']
            }
            return newHours
        })
    }

    const handleAddSlot = (dayIndex: number) => {
        setBusinessHours(prev => {
            const idxStr = dayIndex.toString()
            const currentSlots = prev[idxStr] || []
            return {
                ...prev,
                [idxStr]: [...currentSlots, '09:00-17:00']
            }
        })
    }

    const handleRemoveSlot = (dayIndex: number, slotIndex: number) => {
        setBusinessHours(prev => {
            const idxStr = dayIndex.toString()
            const currentSlots = prev[idxStr] || []
            const newSlots = currentSlots.filter((_, i) => i !== slotIndex)

            // If no slots left, remove the day entirely
            if (newSlots.length === 0) {
                const newHours = { ...prev }
                delete newHours[idxStr]
                return newHours
            }

            return {
                ...prev,
                [idxStr]: newSlots
            }
        })
    }

    const handleAddPhoneNumber = () => {
        setPhoneNumbers(prev => [...prev, { name: '', number: '' }])
    }

    const handleRemovePhoneNumber = (index: number) => {
        setPhoneNumbers(prev => prev.filter((_, i) => i !== index))
    }

    const handlePhoneChange = (index: number, field: 'name' | 'number', value: string) => {
        setPhoneNumbers(prev => {
            const newPhones = [...prev]
            newPhones[index] = { ...newPhones[index], [field]: value }
            return newPhones
        })
    }

    const handleTimeChange = (dayIndex: number, slotIndex: number, type: 'start' | 'end', value: string) => {
        setBusinessHours(prev => {
            const idxStr = dayIndex.toString()
            const currentSlots = prev[idxStr] || []
            const currentRange = currentSlots[slotIndex] || '09:00-17:00'
            const [start, end] = currentRange.split('-')
            let newRange = ''

            if (type === 'start') {
                newRange = `${value}-${end}`
            } else {
                newRange = `${start}-${value}`
            }

            const newSlots = [...currentSlots]
            newSlots[slotIndex] = newRange

            return {
                ...prev,
                [idxStr]: newSlots
            }
        })
    }

    const handleSave = async () => {
        setIsSaving(true)
        try {
            let targetEmail = connectedEmail

            if (!targetEmail) {
                console.warn('No connected email in context. Falling back to getSubscriptionService logic.')
                try {
                    console.log('[SETUP DEBUG] step-static-quiz → GET /get_subscription_service (email fallback)', { subscription_id: currentSubscription?.subscription_id })
                    const serviceData = await backendService.getSubscriptionService(currentSubscription?.subscription_id || '')
                    console.log('[SETUP DEBUG] step-static-quiz → GET /get_subscription_service RESPONSE', serviceData)
                    const service = Array.isArray(serviceData) ? serviceData[0] : serviceData
                    if (service?.email) {
                        targetEmail = service.email
                    }
                } catch (e) {
                    console.warn('Fallback fetch of subscription service failed:', e)
                }
            }

            if (!targetEmail) {
                toast.error(t('setup.verifyEmailFailed'))
                throw new Error(t('setup.verifyEmailFailed'))
            }

            // Convert array back to object
            const phoneNumbersObj: Record<string, string> = {}
            phoneNumbers.forEach(p => {
                const key = p.name.trim() || 'Phone'
                if (key && p.number) {
                    phoneNumbersObj[key] = p.number
                }
            })

            const payload = {
                email: targetEmail,
                business_hours: businessHours,
                appointment_duration: parseInt(appointmentDuration),
                email_signature: emailSignature,
                tone_of_voice: toneOfVoice,
                phone_numbers: phoneNumbersObj,
                draft: isDraft
            }

            console.log('[SETUP DEBUG] step-static-quiz → POST /static-quiz', payload)
            await backendService.updateStaticQuiz(payload)
            console.log('[SETUP DEBUG] step-static-quiz → POST /static-quiz DONE')

            markStepComplete('static-quiz')

            // Mark subscription as configured in local state/cookie so dashboard doesn't redirect back
            markSubscriptionConfigured()

            // Update the individual service's config_completed and email in the session
            const targetServiceId = serviceId || activeServiceId
            if (targetServiceId) {
                updateServiceInSubscription(targetServiceId, {
                    config_completed: true,
                    email: targetEmail || undefined,
                })
            }

            confetti({
                particleCount: 100,
                spread: 70,
                origin: { y: 0.6 }
            })

            toast.success(t('setup.calendarPreferencesSaved'))

            // Redirect to dashboard as this is the final step
            setTimeout(() => {
                window.location.href = '/dashboard'
            }, 1500)
        } catch (error) {
            console.error('Failed to save calendar info:', error)
            toast.error(t('setup.calendarPreferencesFailed'))
        } finally {
            setIsSaving(false)
        }
    }

    if (isLoading) {
        return (
            <div className="flex items-center justify-center min-h-[400px]">
                <Loader2 className="h-8 w-8 animate-spin text-primary" />
            </div>
        )
    }

    return (
        <div className="max-w-2xl mx-auto space-y-6">
            <div className="text-center space-y-2">
                <h2 className="text-2xl font-semibold">{t('setup.calendarPreferencesTitle')}</h2>
                <p className="text-muted-foreground text-sm">
                    {t('setup.calendarPreferencesSubtitle')}
                </p>
            </div>

            <div className="w-full flex flex-col relative space-y-2">
                <div className="text-center pb-1 w-full max-w-md mx-auto">
                    <h3 className="text-xl font-semibold tracking-tight">{t('setup.availabilityTitle')}</h3>
                    <p className="text-xs text-muted-foreground mt-1">
                        {t('setup.availabilityDescription')}
                    </p>
                </div>
                <div className="space-y-4 flex flex-col pt-2 w-full">

                    {calendarProvider && (
                        <>
                            <div className="space-y-2">
                                <Label className="text-xs">{t('setup.businessHours')}</Label>
                                <div className="space-y-1">
                                    {DAYS.map((dayKey, index) => {
                                        const isActive = !!businessHours[index.toString()]

                                        return (
                                            <div key={dayKey} className="flex items-start gap-2 py-1.5 border-b last:border-0 border-border/50">
                                                <div className="w-28 pt-1.5 flex items-center gap-2 shrink-0">
                                                    <input
                                                        type="checkbox"
                                                        checked={isActive}
                                                        onChange={() => handleDayToggle(index)}
                                                        className="rounded border-gray-300 h-3.5 w-3.5"
                                                    />
                                                    <span className={isActive ? 'font-medium text-sm' : 'text-muted-foreground text-sm'}>{t(dayKey)}</span>
                                                </div>
                                                <div className="flex-1 space-y-1">
                                                    {isActive ? (
                                                        <>
                                                            {(businessHours[index.toString()] || []).map((slot, slotIndex) => {
                                                                const [start, end] = slot.split('-')
                                                                return (
                                                                    <div key={slotIndex} className="flex items-center gap-2">
                                                                        <input
                                                                            type="time"
                                                                            value={start}
                                                                            onChange={(e) => handleTimeChange(index, slotIndex, 'start', e.target.value)}
                                                                            className="border rounded p-1 text-sm bg-background"
                                                                        />
                                                                        <span className="text-muted-foreground text-xs">{t('common.to')}</span>
                                                                        <input
                                                                            type="time"
                                                                            value={end}
                                                                            onChange={(e) => handleTimeChange(index, slotIndex, 'end', e.target.value)}
                                                                            className="border rounded p-1 text-sm bg-background"
                                                                        />
                                                                        <Button
                                                                            variant="ghost"
                                                                            size="icon"
                                                                            className="h-7 w-7 text-muted-foreground hover:text-destructive"
                                                                            onClick={() => handleRemoveSlot(index, slotIndex)}
                                                                        >
                                                                            <Trash2 className="h-3.5 w-3.5" />
                                                                        </Button>
                                                                    </div>
                                                                )
                                                            })}
                                                            <Button
                                                                variant="ghost"
                                                                size="sm"
                                                                onClick={() => handleAddSlot(index)}
                                                                className="h-7 text-xs text-primary hover:text-primary/80 px-2"
                                                            >
                                                                <Plus className="h-3 w-3 mr-1" />
                                                                {t('setup.addTimeSlot') || 'Add Slot'}
                                                            </Button>
                                                        </>
                                                    ) : (
                                                        <span className="text-sm text-muted-foreground py-2 block">{t('setup.closed')}</span>
                                                    )}
                                                </div>
                                            </div>
                                        )
                                    })}
                                </div>
                            </div>

                            <div className="space-y-1.5 pt-2">
                                <Label htmlFor="duration" className="text-xs">{t('setup.defaultDuration')}</Label>
                                <Select value={appointmentDuration} onValueChange={setAppointmentDuration}>
                                    <SelectTrigger id="duration" className="h-8 text-sm">
                                        <SelectValue placeholder={t('setup.selectDuration')} />
                                    </SelectTrigger>
                                    <SelectContent>
                                        {APPOINTMENT_DURATIONS.map((dur) => (
                                            <SelectItem key={dur} value={dur.toString()} className="text-sm">{dur} {t('common.minutes')}</SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                            </div>
                        </>
                    )}

                    <div className="space-y-2 pt-2">
                        <div className="flex items-center justify-between">
                            <Label className="text-xs">{t('setup.phoneNumbers') || 'Phone Numbers'}</Label>
                            <Button variant="outline" size="sm" onClick={handleAddPhoneNumber} className="h-7 text-xs px-2">
                                <Plus className="h-3 w-3 mr-1" />
                                {t('setup.addPhone') || 'Add Phone'}
                            </Button>
                        </div>

                        {phoneNumbers.length === 0 && (
                            <p className="text-sm text-muted-foreground italic">
                                {t('setup.noPhoneNumbers') || 'No phone numbers added yet.'}
                            </p>
                        )}

                        <div className="space-y-2">
                            {phoneNumbers.map((phone, index) => (
                                <div key={index} className="flex gap-2 items-start">
                                    <div className="w-1/3">
                                        <Input
                                            placeholder={t('setup.phoneLabelPlaceholder') || "Label (e.g. Office)"}
                                            value={phone.name}
                                            onChange={(e) => handlePhoneChange(index, 'name', e.target.value)}
                                            className="h-8 text-sm"
                                        />
                                    </div>
                                    <div className="flex-1">
                                        <Input
                                            placeholder={t('setup.phoneNumberPlaceholder') || "+39 ..."}
                                            value={phone.number}
                                            onChange={(e) => handlePhoneChange(index, 'number', e.target.value)}
                                            className="h-8 text-sm"
                                        />
                                    </div>
                                    <Button
                                        variant="ghost"
                                        size="icon"
                                        onClick={() => handleRemovePhoneNumber(index)}
                                        className="h-8 w-8 text-destructive hover:text-destructive/90 hover:bg-destructive/10"
                                    >
                                        <Trash2 className="h-3.5 w-3.5" />
                                    </Button>
                                </div>
                            ))}
                        </div>
                    </div>

                    <div className="space-y-1.5 pt-2">
                        <Label htmlFor="toneOfVoice" className="text-xs">{t('setup.toneOfVoice') || 'Tone of Voice'}</Label>
                        <Input
                            id="toneOfVoice"
                            value={toneOfVoice}
                            onChange={(e) => setToneOfVoice(e.target.value)}
                            placeholder={t('setup.toneOfVoicePlaceholder') || 'Professional, Friendly, Formal...'}
                            className="h-8 text-sm"
                        />
                    </div>

                    <div className="space-y-1.5 pt-2">
                        <Label htmlFor="emailSignature" className="text-xs">{t('setup.emailSignature') || 'Email Signature'}</Label>
                        <Textarea
                            id="emailSignature"
                            value={emailSignature}
                            onChange={(e) => setEmailSignature(e.target.value)}
                            placeholder={t('setup.emailSignaturePlaceholder') || 'Best regards,\nThe Team'}
                            className="min-h-[60px] text-sm resize-none"
                        />
                    </div>

                    <div className="flex items-center space-x-2">
                        <Switch id="draft-mode" checked={isDraft} onCheckedChange={setIsDraft} />
                        <Label htmlFor="draft-mode">{t('setup.saveAsDraft')}</Label>
                    </div>

                    <div className="pt-4 flex justify-between">
                        <Button variant="outline" onClick={goToPreviousStep} disabled={isSaving}>
                            {t('setup.back')}
                        </Button>
                        <Button onClick={handleSave} disabled={isSaving}>
                            {isSaving ? (
                                <>
                                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                    {t('setup.saving')}
                                </>
                            ) : (
                                t('setup.continue')
                            )}
                        </Button>
                    </div>

                </div>
            </div>
        </div>
    )
}
