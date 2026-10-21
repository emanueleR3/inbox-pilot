'use client'

import { useState, useEffect, useCallback } from 'react'
import { useAuth } from '@/lib/context/auth-context'
import { useLanguage } from '@/lib/context/language-context'
import { backendService, type ServiceSettings, type UpdateSubscriptionPayload } from '@/lib/api/backend-service'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Skeleton } from '@/components/ui/skeleton'
import { toast } from 'sonner'
import { Clock, Phone, Mail, MessageSquare, Plus, Trash2, Loader2, Building2 } from 'lucide-react'
import { BusinessHoursConfig } from '@/components/setup/business-hours-config'

interface PhoneEntry {
    label: string
    number: string
}

export function ServiceSettingsPanel() {
    const { currentSubscription, activeServiceId } = useAuth()
    const { t } = useLanguage()

    const [isLoading, setIsLoading] = useState(true)
    const [isSaving, setIsSaving] = useState(false)

    // Form state
    const [businessHours, setBusinessHours] = useState<Record<string, string[]>>({})
    const [appointmentDuration, setAppointmentDuration] = useState(30)
    const [phoneNumbers, setPhoneNumbers] = useState<PhoneEntry[]>([])
    const [emailSignature, setEmailSignature] = useState('')
    const [toneOfVoice, setToneOfVoice] = useState('')

    // Company info state
    const [companyName, setCompanyName] = useState('')
    const [vatNumber, setVatNumber] = useState('')
    const [city, setCity] = useState('')
    const [address, setAddress] = useState('')

    // Track if there are unsaved changes
    const [hasChanges, setHasChanges] = useState(false)

    // Service email fetched from getSubscriptionService (services[0].email)
    const [serviceEmail, setServiceEmail] = useState<string | null>(null)
    const subscriptionId = currentSubscription?.subscription_id

    const loadSettings = useCallback(async () => {
        if (!subscriptionId) return

        setIsLoading(true)
        try {
            // First, fetch the service email from subscription services
            const services = await backendService.getSubscriptionService(subscriptionId)
            const service = services && services.length > 0
                ? (activeServiceId
                    ? services.find(s => s.service_id === activeServiceId)
                    : null) || services[0]
                : null

            if (!service?.email) {
                console.warn('No service found for subscription')
                setIsLoading(false)
                return
            }

            const fetchedEmail = service.email
            setServiceEmail(fetchedEmail)

            // Load service settings and company info in parallel
            const settingsPromise = backendService.getServiceSettings(fetchedEmail)
            const subscriptionPromise = backendService.getSubscriptionById(subscriptionId)

            const [settings, subscriptionData] = await Promise.all([settingsPromise, subscriptionPromise])

            // Set business hours
            if (settings.business_hours) {
                setBusinessHours(settings.business_hours)
            }

            // Set appointment duration
            if (settings.appointment_duration) {
                setAppointmentDuration(settings.appointment_duration)
            }

            // Set phone numbers - handle both array and object formats
            if (settings.phone_numbers) {
                if (Array.isArray(settings.phone_numbers)) {
                    setPhoneNumbers(settings.phone_numbers.map((num, idx) => ({
                        label: idx === 0 ? 'Primary' : `Phone ${idx + 1}`,
                        number: num
                    })))
                } else {
                    setPhoneNumbers(Object.entries(settings.phone_numbers).map(([label, number]) => ({
                        label,
                        number
                    })))
                }
            }

            // Set email signature
            if (settings.email_signature) {
                setEmailSignature(settings.email_signature)
            }

            // Set tone of voice
            if (settings.tone_of_voice) {
                setToneOfVoice(settings.tone_of_voice)
            }

            // Set company info
            if (subscriptionData) {
                setCompanyName(subscriptionData.name || '')
                setVatNumber(subscriptionData.vat_number || '')
                setCity(subscriptionData.city || '')
                setAddress(subscriptionData.address || '')
            }

            setHasChanges(false)
        } catch (error) {
            console.error('Failed to load service settings:', error)
            toast.error(t('settings.loadError'))
        } finally {
            setIsLoading(false)
        }
    }, [subscriptionId, t])

    useEffect(() => {
        loadSettings()
    }, [loadSettings])

    const handleSave = async () => {
        if (!serviceEmail) return

        setIsSaving(true)
        try {
            // Convert phone numbers back to array format for API
            const phoneNumbersArray = phoneNumbers
                .filter(p => p.number.trim())
                .map(p => p.number.trim())

            const servicePayload: Partial<ServiceSettings> = {
                business_hours: businessHours,
                appointment_duration: appointmentDuration,
                email_signature: emailSignature,
                tone_of_voice: toneOfVoice,
                phone_numbers: phoneNumbersArray
            }

            // Save service settings
            await backendService.updateServiceSettings(serviceEmail, servicePayload)

            // Save company info if we have a subscription
            if (subscriptionId) {
                const subscriptionPayload: UpdateSubscriptionPayload = {
                    name: companyName,
                    vat_number: vatNumber,
                    city: city,
                    address: address
                }
                await backendService.updateSubscription(subscriptionId, subscriptionPayload)
            }

            toast.success(t('settings.saved'))
            setHasChanges(false)
        } catch (error) {
            console.error('Failed to save service settings:', error)
            toast.error(t('settings.saveError'))
        } finally {
            setIsSaving(false)
        }
    }

    const addPhoneNumber = () => {
        setPhoneNumbers([...phoneNumbers, { label: '', number: '' }])
        setHasChanges(true)
    }

    const removePhoneNumber = (index: number) => {
        setPhoneNumbers(phoneNumbers.filter((_, i) => i !== index))
        setHasChanges(true)
    }

    const updatePhoneNumber = (index: number, field: 'label' | 'number', value: string) => {
        const updated = [...phoneNumbers]
        updated[index][field] = value
        setPhoneNumbers(updated)
        setHasChanges(true)
    }

    if (isLoading) {
        return (
            <div className="space-y-6">
                <Card>
                    <CardHeader>
                        <Skeleton className="h-6 w-40" />
                        <Skeleton className="h-4 w-64" />
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <Skeleton className="h-32 w-full" />
                    </CardContent>
                </Card>
            </div>
        )
    }

    return (
        <div className="space-y-6">
            {/* Company Information */}
            <Card>
                <CardHeader>
                    <div className="flex items-center gap-2">
                        <Building2 className="h-5 w-5 text-muted-foreground" />
                        <CardTitle>{t('settings.ai.companyInfo')}</CardTitle>
                    </div>
                </CardHeader>
                <CardContent className="space-y-4">
                    <div className="grid gap-4 sm:grid-cols-2">
                        <div className="space-y-2">
                            <Label htmlFor="companyName">{t('settings.ai.companyName')}</Label>
                            <Input
                                id="companyName"
                                value={companyName}
                                onChange={(e) => { setCompanyName(e.target.value); setHasChanges(true) }}
                            />
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="vatNumber">{t('settings.ai.vatNumber')}</Label>
                            <Input
                                id="vatNumber"
                                value={vatNumber}
                                onChange={(e) => { setVatNumber(e.target.value); setHasChanges(true) }}
                            />
                        </div>
                    </div>
                    <div className="grid gap-4 sm:grid-cols-2">
                        <div className="space-y-2">
                            <Label htmlFor="city">{t('settings.ai.city')}</Label>
                            <Input
                                id="city"
                                value={city}
                                onChange={(e) => { setCity(e.target.value); setHasChanges(true) }}
                            />
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="address">{t('settings.ai.address')}</Label>
                            <Input
                                id="address"
                                value={address}
                                onChange={(e) => { setAddress(e.target.value); setHasChanges(true) }}
                            />
                        </div>
                    </div>
                </CardContent>
            </Card>

            {/* Phone Numbers */}
            <Card>
                <CardHeader>
                    <div className="flex items-center gap-2">
                        <Phone className="h-5 w-5 text-muted-foreground" />
                        <CardTitle>{t('settings.service.phoneNumbers')}</CardTitle>
                    </div>
                    <CardDescription>{t('settings.service.phoneNumbersDesc')}</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                    {phoneNumbers.map((phone, index) => (
                        <div key={index} className="flex gap-3 items-start">
                            <div className="flex-1 grid gap-3 sm:grid-cols-2">
                                <Input
                                    placeholder={t('setup.phoneLabelPlaceholder')}
                                    value={phone.label}
                                    onChange={(e) => updatePhoneNumber(index, 'label', e.target.value)}
                                />
                                <Input
                                    placeholder={t('setup.phoneNumberPlaceholder')}
                                    value={phone.number}
                                    onChange={(e) => updatePhoneNumber(index, 'number', e.target.value)}
                                />
                            </div>
                            <Button
                                variant="ghost"
                                size="icon"
                                onClick={() => removePhoneNumber(index)}
                                className="text-destructive hover:text-destructive"
                            >
                                <Trash2 className="h-4 w-4" />
                            </Button>
                        </div>
                    ))}
                    <Button variant="outline" onClick={addPhoneNumber} className="w-full">
                        <Plus className="mr-2 h-4 w-4" />
                        {t('settings.service.addPhone')}
                    </Button>
                </CardContent>
            </Card>

            {/* Email Signature */}
            <Card>
                <CardHeader>
                    <div className="flex items-center gap-2">
                        <Mail className="h-5 w-5 text-muted-foreground" />
                        <CardTitle>{t('settings.service.emailSignature')}</CardTitle>
                    </div>
                    <CardDescription>{t('settings.service.emailSignatureDesc')}</CardDescription>
                </CardHeader>
                <CardContent>
                    <Textarea
                        placeholder={t('setup.emailSignaturePlaceholder')}
                        value={emailSignature}
                        onChange={(e) => {
                            setEmailSignature(e.target.value)
                            setHasChanges(true)
                        }}
                        className="min-h-[100px]"
                    />
                </CardContent>
            </Card>

            {/* Tone of Voice */}
            <Card>
                <CardHeader>
                    <div className="flex items-center gap-2">
                        <MessageSquare className="h-5 w-5 text-muted-foreground" />
                        <CardTitle>{t('settings.service.toneOfVoice')}</CardTitle>
                    </div>
                    <CardDescription>{t('settings.service.toneOfVoiceDesc')}</CardDescription>
                </CardHeader>
                <CardContent>
                    <Input
                        placeholder={t('settings.service.toneOfVoicePlaceholder')}
                        value={toneOfVoice}
                        onChange={(e) => {
                            setToneOfVoice(e.target.value)
                            setHasChanges(true)
                        }}
                    />
                </CardContent>
            </Card>

            {/* Business Hours */}
            <Card>
                <CardHeader>
                    <div className="flex items-center gap-2">
                        <Clock className="h-5 w-5 text-muted-foreground" />
                        <CardTitle>{t('settings.service.businessHours')}</CardTitle>
                    </div>
                    <CardDescription>{t('settings.service.businessHoursDesc')}</CardDescription>
                </CardHeader>
                <CardContent>
                    <BusinessHoursConfig
                        value={{ duration: appointmentDuration, hours: businessHours }}
                        onChange={({ duration, hours }) => {
                            setAppointmentDuration(duration)
                            setBusinessHours(hours)
                            setHasChanges(true)
                        }}
                    />
                </CardContent>
            </Card>

            {/* Save Button */}
            <div className="flex justify-end">
                <Button onClick={handleSave} disabled={isSaving || !hasChanges}>
                    {isSaving ? (
                        <>
                            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                            {t('settings.saving')}
                        </>
                    ) : (
                        t('common.saveChanges')
                    )}
                </Button>
            </div>
        </div>
    )
}
