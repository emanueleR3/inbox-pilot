'use client'

import { useState, useEffect, useCallback } from 'react'
import { useSearchParams, useRouter } from 'next/navigation'
import { useSetup } from '@/lib/context/setup-context'
import { useAuth } from '@/lib/context/auth-context'
import { useLanguage } from '@/lib/context/language-context'
import { backendService } from '@/lib/api/backend-service'
import { Button } from '@/components/ui/button'
import {

} from '@/components/ui/card'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { PasswordInput } from '@/components/ui/password-input'
import { Label } from '@/components/ui/label'
import { toast } from 'sonner'
import { Loader2, Mail, Building, Server, CheckCircle2, ChevronRight, Calendar, Layers } from 'lucide-react'
import { cn } from '@/lib/utils'


type Provider = 'google' | 'microsoft' | 'custom'

const PROVIDERS = [
  {
    id: 'google' as Provider,
    name: 'Google',
    description: 'Gmail & Google Workspace',
    icon: Mail,
    color: 'text-red-500',
    bgColor: 'bg-red-50 dark:bg-red-950/30',
  },
  {
    id: 'microsoft' as Provider,
    name: 'Microsoft',
    description: 'Outlook & Microsoft 365',
    icon: Building,
    color: 'text-blue-500',
    bgColor: 'bg-blue-50 dark:bg-blue-950/30',
  },
  {
    id: 'custom' as Provider,
    name: 'Custom IMAP',
    description: 'Other mail servers',
    icon: Server,
    color: 'text-gray-500',
    bgColor: 'bg-gray-50 dark:bg-gray-950/30',
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

export function StepEmail() {
  const {
    setEmailProvider,
    goToNextStep,
    markStepComplete,
    setCustomEmail,
    setConnectedEmail,
    connectedEmail,
    serviceId,
    isStepComplete,
    isLoading: isContextLoading
  } = useSetup()
  const { currentSubscription, session } = useAuth()
  const { t } = useLanguage()
  const searchParams = useSearchParams()
  const router = useRouter()

  const [selectedProvider, setSelectedProvider] = useState<Provider | null>(null)
  const [localLoading, setLocalLoading] = useState(false)
  const [showCustomForm, setShowCustomForm] = useState(false)
  const [showServiceModal, setShowServiceModal] = useState(false)
  const [pendingProvider, setPendingProvider] = useState<Provider | null>(null)

  // Derived state from context
  const isCompleted = isStepComplete('email')
  const [oauthSuccess, setOauthSuccess] = useState(isCompleted)
  const [connectedProvider, setConnectedProvider] = useState<string | null>(null)

  // Sync local success state with context
  useEffect(() => {
    setOauthSuccess(isCompleted)
    if (isCompleted) {
      // Optimistically set provider if we can infer or if context has it (we'll assume context guides us to next step or we show generic success)
      // If we want to show specific provider name, we might need to expose it from context or just say "Connected"
    }
  }, [isCompleted])

  const isLoading = isContextLoading || localLoading

  // Handle OAuth popup message
  const handleOAuthMessage = useCallback((event: MessageEvent) => {
    const data = event.data as OAuthMessage

    if (data && typeof data.success === 'boolean') {
      if (data.success) {
        const providerName = data.user?.provider || selectedProvider || 'email'
        setOauthSuccess(true)
        setConnectedProvider(providerName)

        if (data.user?.email) {
          setConnectedEmail(data.user.email)
        }

        if (providerName === 'google' || providerName === 'microsoft') {
          setEmailProvider(providerName as Provider)
        }
        markStepComplete('email')
        toast.success(data.message || `Successfully connected to ${providerName}!`)
        setLocalLoading(false)
      } else {
        toast.error(data.message || t('setup.oauthFailed'))
        setLocalLoading(false)
      }
    }
  }, [selectedProvider, setEmailProvider, markStepComplete, setConnectedEmail])

  // Listen for OAuth popup messages
  useEffect(() => {
    window.addEventListener('message', handleOAuthMessage)
    return () => {
      window.removeEventListener('message', handleOAuthMessage)
    }
  }, [handleOAuthMessage])

  // Handle OAuth callback results from URL params
  useEffect(() => {
    const oauthSuccessParam = searchParams.get('oauth_success')
    const provider = searchParams.get('provider')
    const emailParam = searchParams.get('email')
    const error = searchParams.get('error')
    const errorDescription = searchParams.get('error_description')

    if (oauthSuccessParam === 'true' && provider) {
      setOauthSuccess(true)
      setConnectedProvider(provider)
      setSelectedProvider(provider as Provider)
      setEmailProvider(provider as Provider)
      if (emailParam) {
        setConnectedEmail(emailParam)
      }
      markStepComplete('email')
      toast.success(`Successfully connected to ${provider === 'google' ? 'Google' : 'Microsoft'}!`)

      const url = new URL(window.location.href)
      url.searchParams.delete('oauth_success')
      url.searchParams.delete('provider')
      url.searchParams.delete('email')
      url.searchParams.delete('session_updated')
      router.replace(url.pathname)
    } else if (error) {
      toast.error(errorDescription || `${t('setup.oauthFailed')}: ${error}`)

      const url = new URL(window.location.href)
      url.searchParams.delete('error')
      url.searchParams.delete('error_description')
      router.replace(url.pathname)
    }
  }, [searchParams, router, setEmailProvider, markStepComplete, setConnectedEmail])

  // Custom IMAP/SMTP form state
  const [customEmailValue, setCustomEmailValue] = useState('')
  const [customPassword, setCustomPassword] = useState('')
  const [imapServer, setImapServer] = useState('')
  const [imapPort, setImapPort] = useState('993')
  const [smtpServer, setSmtpServer] = useState('')
  const [smtpPort, setSmtpPort] = useState('587')

  const handleProviderClick = (provider: Provider) => {
    if (oauthSuccess) return // Don't allow changes if already connected

    if (provider === 'custom') {
      setSelectedProvider(provider)
      setShowCustomForm(true)
    } else {
      setPendingProvider(provider)
      setSelectedProvider(provider)
      setShowServiceModal(true)
    }
  }

  const handleServiceSelection = (services: 'all' | 'calendar' | 'mail') => {
    if (pendingProvider && (pendingProvider === 'google' || pendingProvider === 'microsoft')) {
      setShowServiceModal(false)
      setShowCustomForm(false)
      handleOAuthConnect(pendingProvider, services)
    }
  }

  /**
   * Resolve the service_id for the current subscription.
   * 1. Try from setup context (populated by refreshSetupState)
   * 2. Try from local subscription state (login response)
   * 3. Fetch from API (getSubscriptionService)
   */
  const resolveServiceId = async (subscriptionId: string): Promise<string> => {
    // 1. Try from setup context
    if (serviceId) {
      console.log('[SETUP DEBUG] resolveServiceId → from context:', serviceId)
      return serviceId
    }

    // 2. Try from local subscription state (login response)
    const localServiceId = currentSubscription?.services?.[0]?.service_id
    if (localServiceId) {
      console.log('[SETUP DEBUG] resolveServiceId → from login response:', localServiceId)
      return localServiceId
    }

    // 3. Fetch from API
    console.log('[SETUP DEBUG] resolveServiceId → fetching from API, subscription_id:', subscriptionId)
    const services = await backendService.getSubscriptionService(subscriptionId)
    console.log('[SETUP DEBUG] resolveServiceId → API response:', services)
    if (services && services.length > 0 && services[0].service_id) {
      console.log('[SETUP DEBUG] resolveServiceId → resolved from API:', services[0].service_id)
      return services[0].service_id
    }

    console.error('[SETUP DEBUG] resolveServiceId → FAILED: no service_id found anywhere')
    throw new Error('No service found for this subscription. Please contact support.')
  }

  const handleOAuthConnect = async (provider: 'google' | 'microsoft', services: 'all' | 'calendar' | 'mail') => {
    if (!currentSubscription) {
      toast.error(t('setup.noSubscriptionSelected'))
      return
    }

    setLocalLoading(true)

    try {
      // Resolve service_id (from context, local state, or API)
      const resolvedServiceId = await resolveServiceId(currentSubscription.subscription_id)

      const oauthPayload = {
        provider,
        subscription_id: currentSubscription.subscription_id,
        services,
        email: connectedEmail || null,
        service_id: resolvedServiceId
      }
      console.log('[SETUP DEBUG] step-email → POST /auth/oauth/login/' + provider, oauthPayload)

      const response = await backendService.oauthLogin(
        provider,
        currentSubscription.subscription_id,
        services,
        connectedEmail || null,
        resolvedServiceId
      )
      console.log('[SETUP DEBUG] step-email → POST /auth/oauth/login/' + provider + ' RESPONSE', response)

      if (response.success && response.url) {
        const width = 600
        const height = 700
        const left = window.screenX + (window.outerWidth - width) / 2
        const top = window.screenY + (window.outerHeight - height) / 2

        const popup = window.open(
          response.url,
          `${provider}_oauth`,
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
            if (!oauthSuccess) {
              setLocalLoading(false)
            }
          }
        }, 500)
      } else {
        throw new Error(response.message || t('setup.oauthFailed'))
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : t('setup.connectionFailed')
      toast.error(message)
      setLocalLoading(false)
    }
  }

  const handleCustomConnect = async () => {
    if (!currentSubscription) {
      toast.error(t('setup.noSubscriptionSelected'))
      return
    }

    if (!customEmailValue || !customPassword || !imapServer || !smtpServer) {
      toast.error(t('setup.fillAllFields'))
      return
    }

    setLocalLoading(true)

    try {
      // Resolve service_id (from context, local state, or API)
      const resolvedServiceId = await resolveServiceId(currentSubscription.subscription_id)

      const customPayload = {
        email: customEmailValue,
        password: '***REDACTED***',
        server_imap: imapServer,
        imap_port: parseInt(imapPort),
        server_smtp: smtpServer,
        smtp_port: parseInt(smtpPort),
        subscription_id: currentSubscription.subscription_id,
        calendar_provider: 'null',
        service_id: resolvedServiceId,
      }
      console.log('[SETUP DEBUG] step-email → POST /auth/custom-provider/login', customPayload)

      const response = await backendService.customProviderLogin({
        email: customEmailValue,
        password: customPassword,
        server_imap: imapServer,
        imap_port: parseInt(imapPort),
        server_smtp: smtpServer,
        smtp_port: parseInt(smtpPort),
        subscription_id: currentSubscription.subscription_id,
        calendar_provider: 'null',
        service_id: resolvedServiceId,
      })
      console.log('[SETUP DEBUG] step-email → POST /auth/custom-provider/login RESPONSE', response)

      if (response.status === 'success') {
        toast.success('Email connected successfully!')
        setEmailProvider('custom')
        setCustomEmail(customEmailValue)
        setConnectedEmail(customEmailValue)
        markStepComplete('email')
        setOauthSuccess(true)
        setConnectedProvider('custom')
        goToNextStep()
      } else {
        throw new Error(response.message || t('setup.connectionFailed'))
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : t('setup.connectionFailed')
      toast.error(message)
    } finally {
      setLocalLoading(false)
    }
  }

  return (
    <div className="w-full flex flex-col relative space-y-2">
      {isLoading && (
        <div className="absolute inset-0 z-50 flex items-center justify-center bg-background/50 backdrop-blur-sm rounded-lg">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      )}
      <div className="text-center pb-1 w-full max-w-md mx-auto">
        <h3 className="text-xl font-semibold tracking-tight">{t('setup.connectEmail')}</h3>
        <p className="text-xs text-muted-foreground mt-1">
          {oauthSuccess
            ? t('setup.emailConnectedSuccess')
            : t('setup.selectEmailProvider')}
        </p>
      </div>
      <div className="space-y-3 flex flex-col pt-2 w-full">
        {/* Success state */}
        {oauthSuccess && connectedProvider && (
          <div className="p-4 rounded-lg border border-green-200 bg-green-50 dark:border-green-800 dark:bg-green-950/30">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-green-100 dark:bg-green-900">
                <CheckCircle2 className="h-5 w-5 text-green-600 dark:text-green-400" />
              </div>
              <div className="flex-1">
                <p className="font-medium text-green-800 dark:text-green-200">
                  {connectedProvider === 'google' ? 'Google' : connectedProvider === 'microsoft' ? 'Microsoft' : 'Email'} {t('setup.connected')}
                </p>
                <p className="text-sm text-green-600 dark:text-green-400">
                  {t('setup.emailCalendarLinked')}
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Provider selection */}
        {!oauthSuccess && !showCustomForm && (
          <div className="space-y-4">
            <div className="space-y-2">
              {PROVIDERS.map((provider) => {
                const Icon = provider.icon
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
                      'flex h-10 w-10 items-center justify-center rounded-lg',
                      provider.bgColor
                    )}>
                      <Icon className={cn('h-5 w-5', provider.color)} />
                    </div>
                    <div className="flex-1">
                      <p className="font-medium">{provider.name}</p>
                      <p className="text-sm text-muted-foreground">{provider.description}</p>
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

            {/* Calendar Connection Option - REMOVED */}
          </div>
        )}

        {/* Custom IMAP Form */}
        {showCustomForm && !oauthSuccess && (
          <div className="space-y-3">
            <button
              onClick={() => setShowCustomForm(false)}
              className="text-xs text-muted-foreground hover:text-foreground flex items-center gap-1"
            >
              ← {t('setup.backToProviders')}
            </button>

            <div className="space-y-2">
              <div className="space-y-1.5">
                <Label htmlFor="custom-email" className="text-xs">{t('setup.emailAddress')}</Label>
                <Input
                  id="custom-email"
                  type="email"
                  placeholder="you@example.com"
                  className="h-8 text-sm"
                  value={customEmailValue}
                  onChange={(e) => setCustomEmailValue(e.target.value)}
                  disabled={isLoading}
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="custom-password" className="text-xs">{t('setup.password')}</Label>
                <PasswordInput
                  id="custom-password"
                  value={customPassword}
                  onChange={(e) => setCustomPassword(e.target.value)}
                  disabled={isLoading}
                  className="h-8 text-sm"
                />
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div className="space-y-1.5">
                  <Label htmlFor="imap-server" className="text-xs">{t('setup.imapServer')}</Label>
                  <Input
                    id="imap-server"
                    placeholder="imap.example.com"
                    value={imapServer}
                    onChange={(e) => setImapServer(e.target.value)}
                    disabled={isLoading}
                    className="h-8 text-sm"
                  />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="imap-port" className="text-xs">{t('setup.port')}</Label>
                  <Input
                    id="imap-port"
                    type="text"
                    inputMode="numeric"
                    pattern="[0-9]*"
                    placeholder="993"
                    value={imapPort}
                    onChange={(e) => setImapPort(e.target.value)}
                    disabled={isLoading}
                    className="h-8 text-sm"
                  />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div className="space-y-1.5">
                  <Label htmlFor="smtp-server" className="text-xs">{t('setup.smtpServer')}</Label>
                  <Input
                    id="smtp-server"
                    placeholder="smtp.example.com"
                    value={smtpServer}
                    onChange={(e) => setSmtpServer(e.target.value)}
                    disabled={isLoading}
                    className="h-8 text-sm"
                  />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="smtp-port" className="text-xs">{t('setup.port')}</Label>
                  <Input
                    id="smtp-port"
                    type="text"
                    inputMode="numeric"
                    pattern="[0-9]*"
                    placeholder="587"
                    value={smtpPort}
                    onChange={(e) => setSmtpPort(e.target.value)}
                    disabled={isLoading}
                    className="h-8 text-sm"
                  />
                </div>
              </div>
            </div>

            <Button
              onClick={handleCustomConnect}
              disabled={isLoading || !customEmailValue || !customPassword || !imapServer || !smtpServer}
              className="w-full"
            >
              {isLoading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  {t('setup.connecting')}
                </>
              ) : (
                t('setup.connectEmail')
              )}
            </Button>
          </div>
        )}

        {/* Continue button when connected */}
        {oauthSuccess && (
          <Button onClick={() => goToNextStep()} className="w-full">
            {t('setup.continue')}
            <ChevronRight className="ml-2 h-4 w-4" />
          </Button>
        )}
      </div>

      {/* Service Selection Modal */}
      <Dialog open={showServiceModal} onOpenChange={setShowServiceModal}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>{t('setup.selectServices') || 'Select Services'}</DialogTitle>
            <DialogDescription>
              {t('setup.selectServicesDescription') || 'Choose which services to connect with your account.'}
            </DialogDescription>
          </DialogHeader>
          <div className="flex flex-col gap-3 py-4">
            <button
              onClick={() => handleServiceSelection('all')}
              className="flex items-center gap-3 p-4 rounded-lg border hover:border-primary/50 hover:bg-muted/50 transition-all text-left"
            >
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                <Layers className="h-5 w-5 text-primary" />
              </div>
              <div className="flex-1">
                <p className="font-medium">{t('setup.allServices') || 'Email & Calendar'}</p>
                <p className="text-sm text-muted-foreground">{t('setup.allServicesDesc') || 'Connect both email and calendar'}</p>
              </div>
              <ChevronRight className="h-5 w-5 text-muted-foreground" />
            </button>
            <button
              onClick={() => handleServiceSelection('mail')}
              className="flex items-center gap-3 p-4 rounded-lg border hover:border-primary/50 hover:bg-muted/50 transition-all text-left"
            >
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                <Mail className="h-5 w-5 text-primary" />
              </div>
              <div className="flex-1">
                <p className="font-medium">{t('setup.mailOnly') || 'Email Only'}</p>
                <p className="text-sm text-muted-foreground">{t('setup.mailOnlyDesc') || 'Connect only your email inbox'}</p>
              </div>
              <ChevronRight className="h-5 w-5 text-muted-foreground" />
            </button>
            <button
              onClick={() => handleServiceSelection('calendar')}
              className="flex items-center gap-3 p-4 rounded-lg border hover:border-primary/50 hover:bg-muted/50 transition-all text-left"
            >
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                <Calendar className="h-5 w-5 text-primary" />
              </div>
              <div className="flex-1">
                <p className="font-medium">{t('setup.calendarOnly') || 'Calendar Only'}</p>
                <p className="text-sm text-muted-foreground">{t('setup.calendarOnlyDesc') || 'Connect only your calendar'}</p>
              </div>
              <ChevronRight className="h-5 w-5 text-muted-foreground" />
            </button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}
