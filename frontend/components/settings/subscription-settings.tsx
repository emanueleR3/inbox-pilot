'use client'

import { useState, useEffect, useCallback } from 'react'
import { useAuth } from '@/lib/context/auth-context'
import { useLanguage } from '@/lib/context/language-context'
import { backendService, type AIConfiguration, type UpdateSubscriptionPayload } from '@/lib/api/backend-service'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Label } from '@/components/ui/label'
import { Button } from '@/components/ui/button'
import { Switch } from '@/components/ui/switch'
import { Separator } from '@/components/ui/separator'
import { Skeleton } from '@/components/ui/skeleton'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { toast } from 'sonner'
import { Sliders, Loader2, FileEdit, Info } from 'lucide-react'
import { cn } from '@/lib/utils'

interface ThresholdSliderProps {
    label: string
    description: string
    hint: string
    value: number
    onChange: (value: number) => void
    disabled?: boolean
    lowLabel?: string
    highLabel?: string
}

function ThresholdSlider({ label, description, hint, value, onChange, disabled, lowLabel, highLabel }: ThresholdSliderProps) {
    const percentage = Math.round(value * 100)

    return (
        <div className="space-y-3">
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <Label className="font-medium">{label}</Label>
                    <Tooltip>
                        <TooltipTrigger asChild>
                            <button type="button" className="text-muted-foreground hover:text-foreground transition-colors">
                                <Info className="h-4 w-4" />
                            </button>
                        </TooltipTrigger>
                        <TooltipContent className="max-w-xs">
                            <p>{hint}</p>
                        </TooltipContent>
                    </Tooltip>
                </div>
                <span className="text-sm font-medium tabular-nums">{percentage}%</span>
            </div>
            <p className="text-sm text-muted-foreground">{description}</p>
            <div className="space-y-1">
                <input
                    type="range"
                    min="0"
                    max="100"
                    value={percentage}
                    onChange={(e) => onChange(parseInt(e.target.value) / 100)}
                    disabled={disabled}
                    className={cn(
                        "w-full h-2 bg-muted rounded-lg appearance-none cursor-pointer",
                        "accent-primary",
                        disabled && "opacity-50 cursor-not-allowed"
                    )}
                />
                {(lowLabel || highLabel) && (
                    <div className="flex justify-between text-xs text-muted-foreground">
                        <span>{lowLabel}</span>
                        <span>{highLabel}</span>
                    </div>
                )}
            </div>
        </div>
    )
}

export function SubscriptionSettingsPanel() {
    const { currentSubscription } = useAuth()
    const { t } = useLanguage()

    const [isLoading, setIsLoading] = useState(true)
    const [isSaving, setIsSaving] = useState(false)
    const [hasChanges, setHasChanges] = useState(false)

    // Company info state
    const [companyName, setCompanyName] = useState('')
    const [vatNumber, setVatNumber] = useState('')
    const [city, setCity] = useState('')
    const [address, setAddress] = useState('')

    // AI Configuration state
    const [confidenceResponseThreshold, setConfidenceResponseThreshold] = useState(0.8)
    const [confidenceReviewMail, setConfidenceReviewMail] = useState(0.7)
    const [priorityThreshold, setPriorityThreshold] = useState(0.5)
    const [confidenceClassificationThreshold, setConfidenceClassificationThreshold] = useState(0.75)
    const [urgentMeetingThreshold, setUrgentMeetingThreshold] = useState(0.9)
    const [isDraft, setIsDraft] = useState(false)

    const subscriptionId = currentSubscription?.subscription_id

    const loadSettings = useCallback(async () => {
        if (!subscriptionId) return

        setIsLoading(true)
        try {
            // Load subscription details and AI config in parallel
            const [subscriptionData, configData] = await Promise.all([
                backendService.getSubscriptionById(subscriptionId),
                backendService.getConfiguration(subscriptionId)
            ])

            // Set company info
            setCompanyName(subscriptionData.name || '')
            setVatNumber(subscriptionData.vat_number || '')
            setCity(subscriptionData.city || '')
            setAddress(subscriptionData.address || '')

            // Set AI config
            if (configData.status === 'ok' && configData.result) {
                setConfidenceResponseThreshold(configData.result.confidence_response_threshold)
                setConfidenceReviewMail(configData.result.confidence_review_mail)
                setPriorityThreshold(configData.result.priority_threshold)
                setConfidenceClassificationThreshold(configData.result.confidence_classification_threshold)
                setUrgentMeetingThreshold(configData.result.urgent_meeting_threshold)
                setIsDraft(configData.result.draft ?? false)
            }

            setHasChanges(false)
        } catch (error) {
            console.error('Failed to load subscription settings:', error)
            toast.error(t('settings.loadError'))
        } finally {
            setIsLoading(false)
        }
    }, [subscriptionId, t])

    useEffect(() => {
        loadSettings()
    }, [loadSettings])

    const handleSave = async () => {
        if (!subscriptionId) return

        setIsSaving(true)
        try {
            // Update subscription details
            const subscriptionPayload: UpdateSubscriptionPayload = {
                name: companyName,
                vat_number: vatNumber,
                city: city,
                address: address
            }
            await backendService.updateSubscription(subscriptionId, subscriptionPayload)

            // Update AI configuration
            const configPayload: Partial<AIConfiguration> = {
                confidence_response_threshold: confidenceResponseThreshold,
                confidence_review_mail: confidenceReviewMail,
                priority_threshold: priorityThreshold,
                confidence_classification_threshold: confidenceClassificationThreshold,
                urgent_meeting_threshold: urgentMeetingThreshold,
                draft: isDraft
            }
            await backendService.updateConfiguration(subscriptionId, configPayload)

            toast.success(t('settings.saved'))
            setHasChanges(false)
        } catch (error) {
            console.error('Failed to save subscription settings:', error)
            toast.error(t('settings.saveError'))
        } finally {
            setIsSaving(false)
        }
    }

    const markChanged = () => setHasChanges(true)

    if (isLoading) {
        return (
            <div className="space-y-6">
                <Card>
                    <CardHeader>
                        <Skeleton className="h-6 w-40" />
                        <Skeleton className="h-4 w-64" />
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <Skeleton className="h-10 w-full" />
                        <Skeleton className="h-10 w-full" />
                    </CardContent>
                </Card>
            </div>
        )
    }

    return (
        <div className="space-y-6">
            {/* Draft Mode */}
            <Card>
                <CardHeader>
                    <div className="flex items-center gap-2">
                        <FileEdit className="h-5 w-5 text-muted-foreground" />
                        <CardTitle>{t('setup.saveAsDraft')}</CardTitle>
                    </div>
                    <CardDescription>{t('setup.saveAsDraftDesc')}</CardDescription>
                </CardHeader>
                <CardContent>
                    <div className="flex items-center space-x-3">
                        <Switch
                            id="draft-mode"
                            checked={isDraft}
                            onCheckedChange={(checked) => { setIsDraft(checked); markChanged() }}
                        />
                        <Label htmlFor="draft-mode" className="cursor-pointer">
                            {isDraft ? t('setup.saveAsDraft') : t('settings.ai.autoSend')}
                        </Label>
                    </div>
                </CardContent>
            </Card>

            {/* AI Confidence Thresholds */}
            <Card>
                <CardHeader>
                    <div className="flex items-center gap-2">
                        <Sliders className="h-5 w-5 text-muted-foreground" />
                        <CardTitle>{t('settings.ai.thresholds')}</CardTitle>
                    </div>
                    <CardDescription>{t('settings.ai.thresholdsDesc')}</CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                    <ThresholdSlider
                        label={t('settings.ai.responseThreshold')}
                        description={t('settings.ai.responseThresholdDesc')}
                        hint={t('settings.ai.responseThresholdHint')}
                        value={confidenceResponseThreshold}
                        onChange={(v) => { setConfidenceResponseThreshold(v); markChanged() }}
                        lowLabel={t('settings.ai.cautious')}
                        highLabel={t('settings.ai.confident')}
                    />
                    <Separator />
                    <ThresholdSlider
                        label={t('settings.ai.reviewThreshold')}
                        description={t('settings.ai.reviewThresholdDesc')}
                        hint={t('settings.ai.reviewThresholdHint')}
                        value={confidenceReviewMail}
                        onChange={(v) => { setConfidenceReviewMail(v); markChanged() }}
                        lowLabel={t('settings.ai.lessReview')}
                        highLabel={t('settings.ai.moreReview')}
                    />
                    <Separator />
                    <ThresholdSlider
                        label={t('settings.ai.priorityThreshold')}
                        description={t('settings.ai.priorityThresholdDesc')}
                        hint={t('settings.ai.priorityThresholdHint')}
                        value={priorityThreshold}
                        onChange={(v) => { setPriorityThreshold(v); markChanged() }}
                        lowLabel={t('settings.ai.lowPriority')}
                        highLabel={t('settings.ai.highPriority')}
                    />
                    <Separator />
                    <ThresholdSlider
                        label={t('settings.ai.classificationThreshold')}
                        description={t('settings.ai.classificationThresholdDesc')}
                        hint={t('settings.ai.classificationThresholdHint')}
                        value={confidenceClassificationThreshold}
                        onChange={(v) => { setConfidenceClassificationThreshold(v); markChanged() }}
                        lowLabel={t('settings.ai.flexible')}
                        highLabel={t('settings.ai.strict')}
                    />
                    <Separator />
                    <ThresholdSlider
                        label={t('settings.ai.urgentMeetingThreshold')}
                        description={t('settings.ai.urgentMeetingThresholdDesc')}
                        hint={t('settings.ai.urgentMeetingThresholdHint')}
                        value={urgentMeetingThreshold}
                        onChange={(v) => { setUrgentMeetingThreshold(v); markChanged() }}
                        lowLabel={t('settings.ai.relaxed')}
                        highLabel={t('settings.ai.urgent')}
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
