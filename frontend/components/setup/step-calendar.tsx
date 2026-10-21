'use client'

import { useState, useCallback, useEffect } from 'react'
import { useSetup } from '@/lib/context/setup-context'
import { useAuth } from '@/lib/context/auth-context'
import { useLanguage } from '@/lib/context/language-context'
import { backendService } from '@/lib/api/backend-service'
import { Button } from '@/components/ui/button'
import {

} from '@/components/ui/card'
import { toast } from 'sonner'
import { Loader2, Calendar, CheckCircle2, ChevronRight, ChevronLeft } from 'lucide-react'
import { cn } from '@/lib/utils'

type CalendarProvider = 'google' | 'microsoft'

const CALENDAR_PROVIDERS = [
  {
    id: 'google' as CalendarProvider,
    nameKey: 'setup.provider.googleCalendar',
    descKey: 'setup.provider.googleCalendarDesc',
    icon: '📅',
    color: 'text-red-500',
    bgColor: 'bg-red-50 dark:bg-red-950/30',
  },
  {
    id: 'microsoft' as CalendarProvider,
    nameKey: 'setup.provider.outlookCalendar',
    descKey: 'setup.provider.outlookCalendarDesc',
    icon: '📆',
    color: 'text-blue-500',
    bgColor: 'bg-blue-50 dark:bg-blue-950/30',
  },
]

// OAuth popup message type
interface OAuthMessage {
  success: boolean
  message?: string
  user?: {
    email: string
    provider: string
    subscription_id: string
  }
}

export function StepCalendar() {
  const { setCalendarProvider, calendarProvider, goToNextStep, goToPreviousStep, markStepComplete, connectedEmail, serviceId: contextServiceId, isStepComplete } = useSetup()
  const { currentSubscription } = useAuth()
  const { t } = useLanguage()

  const [selectedProvider, setSelectedProvider] = useState<CalendarProvider | null>(null)
  const [isLoading, setIsLoading] = useState(false)

  // Derived state
  const isConnected = !!calendarProvider
  const isCompleted = isStepComplete('calendar')
  const displayedProvider = selectedProvider || (calendarProvider as CalendarProvider)

  // Handle OAuth popup message
  const handleOAuthMessage = useCallback((event: MessageEvent) => {
    const data = event.data as OAuthMessage

    if (data && typeof data.success === 'boolean') {
      if (data.success) {
        if (selectedProvider) {
          setCalendarProvider(selectedProvider)
        }
        markStepComplete('calendar')
        toast.success(data.message || t('setup.calendarConnectedSuccess'))
        setIsLoading(false)
      } else {
        toast.error(data.message || t('setup.connectionFailed'))
        setIsLoading(false)
      }
    }
  }, [selectedProvider, setCalendarProvider, markStepComplete])

  // Listen for OAuth popup messages
  useEffect(() => {
    window.addEventListener('message', handleOAuthMessage)
    return () => {
      window.removeEventListener('message', handleOAuthMessage)
    }
  }, [handleOAuthMessage])

  const handleProviderClick = async (provider: CalendarProvider) => {
    if (isConnected) return

    if (!currentSubscription) {
      toast.error(t('setup.noSubscriptionSelected'))
      return
    }

    setSelectedProvider(provider)
    setIsLoading(true)

    try {
      // Resolve service_id: context first, then subscription state, then API
      let resolvedServiceId = contextServiceId || currentSubscription.services?.[0]?.service_id || null
      console.log('[SETUP DEBUG] step-calendar → resolving service_id, initial:', resolvedServiceId)
      if (!resolvedServiceId) {
        try {
          console.log('[SETUP DEBUG] step-calendar → fetching service_id from API, subscription_id:', currentSubscription.subscription_id)
          const services = await backendService.getSubscriptionService(currentSubscription.subscription_id)
          console.log('[SETUP DEBUG] step-calendar → GET /get_subscription_service RESPONSE', services)
          if (services && services.length > 0 && services[0].service_id) {
            resolvedServiceId = services[0].service_id
          }
        } catch (err) {
          console.log('[SETUP DEBUG] step-calendar → service_id fetch error:', err)
        }
      }
      if (!resolvedServiceId) {
        throw new Error('No service found. Please complete the email step first.')
      }

      const calendarPayload = {
        provider,
        subscription_id: currentSubscription.subscription_id,
        services: 'calendar',
        email: connectedEmail,
        service_id: resolvedServiceId
      }
      console.log('[SETUP DEBUG] step-calendar → POST /auth/oauth/login/' + provider, calendarPayload)

      // Direct OAuth login for calendar
      const response = await backendService.oauthLogin(
        provider,
        currentSubscription.subscription_id,
        'calendar',
        connectedEmail,
        resolvedServiceId
      )
      console.log('[SETUP DEBUG] step-calendar → POST /auth/oauth/login/' + provider + ' RESPONSE', response)

      if (response.success && response.url) {
        const width = 600
        const height = 700
        const left = window.screenX + (window.outerWidth - width) / 2
        const top = window.screenY + (window.outerHeight - height) / 2

        const popup = window.open(
          response.url,
          `${provider}_calendar_oauth`,
          `width=${width},height=${height},left=${left},top=${top},scrollbars=yes,resizable=yes`
        )

        if (!popup) {
          toast.info(t('setup.popupBlocked'))
          window.location.href = response.url
          return
        }

        const popupChecker = setInterval(() => {
          if (popup.closed) {
            clearInterval(popupChecker)
            if (!isConnected) {
              setIsLoading(false)
            }
          }
        }, 500)
      } else {
        throw new Error(response.message || t('setup.startCalendarFailed'))
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : t('setup.connectionFailed')
      toast.error(message)
      setIsLoading(false)
    }
  }

  return (
    <div className="w-full flex flex-col relative space-y-2">
      <div className="text-center pb-1 w-full max-w-md mx-auto">
        <h3 className="text-xl font-semibold tracking-tight">{t('setup.connectCalendar')}</h3>
        <p className="text-xs text-muted-foreground mt-1">
          {isConnected
            ? t('setup.calendarConnectedSuccess')
            : t('setup.selectCalendarProvider')}
        </p>
      </div>
      <div className="space-y-3 flex flex-col pt-2 w-full">
        {/* Success state */}
        {isConnected && displayedProvider && (
          <div className="p-4 rounded-lg border border-green-200 bg-green-50 dark:border-green-800 dark:bg-green-950/30">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-green-100 dark:bg-green-900">
                <CheckCircle2 className="h-5 w-5 text-green-600 dark:text-green-400" />
              </div>
              <div className="flex-1">
                <p className="font-medium text-green-800 dark:text-green-200">
                  {displayedProvider === 'google' ? t('setup.provider.googleCalendar') : t('setup.provider.outlookCalendar')} {t('setup.connected')}
                </p>
                <p className="text-sm text-green-600 dark:text-green-400">
                  {t('setup.calendarLinked')}
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Provider selection */}
        {!isConnected && (
          <div className="space-y-2">
            {CALENDAR_PROVIDERS.map((provider) => {
              const isSelected = selectedProvider === provider.id
              const isCurrentlyLoading = isLoading && isSelected

              return (
                <button
                  key={provider.id}
                  onClick={() => handleProviderClick(provider.id)}
                  disabled={isLoading}
                  className={cn(
                    'w-full flex items-center gap-3 p-3 rounded-lg border transition-all text-left',
                    'hover:border-primary/50 hover:bg-muted/50',
                    isSelected && 'border-primary bg-primary/5 ring-1 ring-primary/20',
                    isLoading && !isCurrentlyLoading && 'opacity-50 cursor-not-allowed'
                  )}
                >
                  <div className={cn(
                    'flex h-10 w-10 items-center justify-center rounded-lg text-xl',
                    provider.bgColor
                  )}>
                    {provider.icon}
                  </div>
                  <div className="flex-1">
                    <p className="font-medium">{t(provider.nameKey)}</p>
                    <p className="text-sm text-muted-foreground">{t(provider.descKey)}</p>
                  </div>
                  {isCurrentlyLoading ? (
                    <Loader2 className="h-5 w-5 animate-spin text-primary" />
                  ) : (
                    <ChevronRight className="h-5 w-5 text-muted-foreground" />
                  )}
                </button>
              )
            })}
          </div>
        )}

        {/* Navigation buttons */}
        <div className="flex gap-2 pt-1">
          <Button
            variant="outline"
            onClick={goToPreviousStep}
            disabled={isLoading}
            className="flex-1"
          >
            <ChevronLeft className="mr-2 h-4 w-4" />
            {t('setup.back')}
          </Button>

          {isConnected || isCompleted ? (
            <Button onClick={() => goToNextStep()} className="flex-1">
              {t('setup.continue')}
              <ChevronRight className="ml-2 h-4 w-4" />
            </Button>
          ) : (
            <Button
              variant="ghost"
              onClick={() => {
                markStepComplete('calendar')
                goToNextStep()
              }}
              className="flex-1 text-muted-foreground hover:text-foreground"
            >
              {t('setup.skip')}
              <ChevronRight className="ml-2 h-4 w-4" />
            </Button>
          )}
        </div>
      </div>
    </div>
  )
}
