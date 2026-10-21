'use client'

import { createContext, useContext, useState, useCallback, useEffect } from 'react'
import { useAuth } from '@/lib/context/auth-context'
import { backendService } from '@/lib/api/backend-service'

export type SetupStep = 'email' | 'calendar' | 'website' | 'quiz' | 'static-quiz' | 'complete'

interface SetupContextType {
  isLoading: boolean
  currentStep: SetupStep
  emailProvider: 'google' | 'microsoft' | 'custom' | null
  calendarProvider: 'google' | 'microsoft' | null
  customEmail: string | null  // Email from custom IMAP setup
  connectedEmail: string | null // Email from any provider (saved from OAuth)
  serviceId: string | null // service_id of the current subscription service
  websiteUrl: string | null  // Company website URL
  setCurrentStep: (step: SetupStep) => void
  setEmailProvider: (provider: 'google' | 'microsoft' | 'custom') => void
  setCalendarProvider: (provider: 'google' | 'microsoft') => void
  setCustomEmail: (email: string) => void
  setConnectedEmail: (email: string) => void
  setWebsiteUrl: (url: string) => void
  goToNextStep: () => void
  goToPreviousStep: () => void
  goToStep: (step: SetupStep) => void
  canGoToStep: (step: SetupStep) => boolean
  isStepComplete: (step: SetupStep) => boolean
  markStepComplete: (step: SetupStep) => void
  markStepIncomplete: (step: SetupStep) => void
  needsCalendarStep: () => boolean
  getVisibleSteps: () => SetupStep[]
}

const SetupContext = createContext<SetupContextType | undefined>(undefined)

const STEPS_ORDER: SetupStep[] = ['email', 'calendar', 'website', 'quiz', 'static-quiz', 'complete']

export function SetupProvider({ children }: { children: React.ReactNode }) {
  const { currentSubscription, activeServiceId } = useAuth()
  const [isLoading, setIsLoading] = useState(true)

  // State (In-memory only, no localStorage)
  const [currentStep, setCurrentStep] = useState<SetupStep>('email')
  const [emailProvider, setEmailProviderState] = useState<'google' | 'microsoft' | 'custom' | null>(null)
  const [calendarProvider, setCalendarProviderState] = useState<'google' | 'microsoft' | null>(null)
  const [customEmail, setCustomEmailState] = useState<string | null>(null)
  const [connectedEmail, setConnectedEmailState] = useState<string | null>(null)
  const [serviceId, setServiceId] = useState<string | null>(null)
  const [websiteUrl, setWebsiteUrlState] = useState<string | null>(null)
  const [completedSteps, setCompletedSteps] = useState<Set<SetupStep>>(new Set())

  // Refresh setup state from backend
  const refreshSetupState = useCallback(async () => {
    if (!currentSubscription) {
      setIsLoading(false)
      return
    }

    setIsLoading(true)

    // Reset all state immediately to avoid showing stale data from a previous service
    setCurrentStep('email')
    setEmailProviderState(null)
    setCalendarProviderState(null)
    setCustomEmailState(null)
    setConnectedEmailState(null)
    setServiceId(null)
    setWebsiteUrlState(null)
    setCompletedSteps(new Set())

    try {
      // 1. Fetch Subscription Services (Email/Calendar status)
      console.log('[SETUP DEBUG] refreshSetupState → GET /get_subscription_service', { subscription_id: currentSubscription.subscription_id })
      const services = await backendService.getSubscriptionService(currentSubscription.subscription_id)
      console.log('[SETUP DEBUG] refreshSetupState → GET /get_subscription_service RESPONSE', services)

      // Find the correct service to configure:
      // 1. Use activeServiceId if set (from service-list navigation)
      // 2. Fall back to first non-configured service
      // 3. Fall back to first service
      let service = null
      if (activeServiceId) {
        service = services.find((s: any) => s.service_id === activeServiceId) || null
        if (!service) {
          // activeServiceId is set but not found in backend response — this is a brand new service.
          // Use activeServiceId directly and start from the beginning.
          setServiceId(activeServiceId)
          setIsLoading(false)
          return
        }
      }
      if (!service) {
        // Try to find first non-configured service
        service = services.find((s: any) => !s.config_completed) || null
      }
      if (!service) {
        // Fall back to first service
        service = services[0] || null
      }

      if (!service) {
        // No service configured yet, stay on email step
        // But try to get service_id from local subscription state
        const localServiceId = activeServiceId || currentSubscription.services?.[0]?.service_id || null
        if (localServiceId) {
          setServiceId(localServiceId)
        }
        setIsLoading(false)
        return
      }

      // Store the service_id
      setServiceId(service.service_id)

      // Note: We do NOT early-return based on service.config_completed alone,
      // because the backend may set this flag globally for all services under
      // a subscription when any one of them completes configuration.
      // Instead, we verify each step individually and use config_completed
      // only as a signal that quiz/static-quiz steps are done.
      const backendSaysConfigured = !!service.config_completed

      let foundEmailProvider: 'google' | 'microsoft' | 'custom' | null = null
      let foundEmail: string | null = null
      let foundCalendarProvider: 'google' | 'microsoft' | null = null

      if (['google', 'microsoft', 'imap'].includes(service.email_provider)) {
        foundEmail = service.email
        const rawProvider = service.email_provider
        foundEmailProvider = rawProvider === 'imap' ? 'custom' : rawProvider
      }

      // 2. Fetch Collection Status (Website status)
      // We need a valid email string to check collection status.
      // If the service exists but has email: null, skip collection check.
      let websiteCompleted = false
      if (foundEmail && typeof foundEmail === 'string' && foundEmail.length > 0) {
        try {
          console.log('[SETUP DEBUG] refreshSetupState → GET /scraper/collection', { email: foundEmail })
          const collectionStatus = await backendService.getCollectionStatus(foundEmail)
          console.log('[SETUP DEBUG] refreshSetupState → GET /scraper/collection RESPONSE', collectionStatus)
          if (collectionStatus.exists) {
            websiteCompleted = true
          }
        } catch (err) {
          console.log('[SETUP DEBUG] refreshSetupState → GET /scraper/collection ERROR (expected if not scraped)', err)
          // Collection not found or service not yet scraped — this is expected
        }
      }

      // 3. Quiz Status — trust config_completed only if email is also verified
      // This prevents a service with config_completed=true but no email from
      // being treated as fully configured.

      // Update State
      const newCompletedSteps = new Set<SetupStep>()

      if (foundEmailProvider) {
        newCompletedSteps.add('email')

        // Check if calendar is explicitly configured in the service
        if ('calendar_provider' in service && ['google', 'microsoft'].includes(service.calendar_provider)) {
          newCompletedSteps.add('calendar')
          foundCalendarProvider = service.calendar_provider as 'google' | 'microsoft'
        }
      }

      if (websiteCompleted) {
        newCompletedSteps.add('website')
      }

      // Only mark quiz/static-quiz as complete if this specific service
      // actually has email configured AND the backend says it's configured
      if (backendSaysConfigured && foundEmailProvider && websiteCompleted) {
        newCompletedSteps.add('quiz')
        newCompletedSteps.add('static-quiz')
      }

      setEmailProviderState(foundEmailProvider)
      setConnectedEmailState(foundEmail)
      setCustomEmailState(foundEmailProvider === 'custom' ? foundEmail : null)
      setCalendarProviderState(foundCalendarProvider)
      setCompletedSteps(newCompletedSteps)

      // Calculate Next Logical Step
      let nextStep: SetupStep = 'email'
      const visibleSteps = ['email', 'calendar', 'website', 'quiz', 'static-quiz', 'complete'] as SetupStep[]

      for (const step of visibleSteps) {
        // "complete" is the final state, so if we reach it, that's the step
        if (step === 'complete') {
          nextStep = 'complete'
          break
        }
        if (!newCompletedSteps.has(step as SetupStep)) {
          nextStep = step as SetupStep
          break
        }
      }

      // If everything is done (including quiz which we can't easily verify yet), default to quiz or complete?
      // Since we can't verify quiz easily, it will likely stop at 'quiz'. 
      // If the user manually navigates, we honor it? No, user said "always backend".
      // So we set it to nextStep.
      setCurrentStep(nextStep)

    } catch (error) {
      console.error('Failed to refresh setup state:', error)
    } finally {
      setIsLoading(false)
    }
  }, [currentSubscription, activeServiceId])

  // Initial load and subscription change
  useEffect(() => {
    refreshSetupState()
  }, [refreshSetupState])


  // Setters (Memory only)
  const setCurrentStepWithNative = (step: SetupStep) => setCurrentStep(step)
  const setCustomEmail = useCallback((email: string) => setCustomEmailState(email), [])
  const setConnectedEmail = useCallback((email: string) => setConnectedEmailState(email), [])
  const setWebsiteUrl = useCallback((url: string) => setWebsiteUrlState(url), [])
  const setCalendarProvider = useCallback((provider: 'google' | 'microsoft' | null) => setCalendarProviderState(provider), [])

  const setEmailProvider = useCallback((provider: 'google' | 'microsoft' | 'custom') => {
    setEmailProviderState(provider)
    if (provider === 'google' || provider === 'microsoft') {
      setCalendarProvider(provider)
    } else {
      setCalendarProvider(null)
    }
  }, [setCalendarProvider])

  const needsCalendarStep = useCallback(() => {
    return true
  }, [])

  const markStepComplete = useCallback((step: SetupStep) => {
    setCompletedSteps(prev => new Set(prev).add(step))
  }, [])

  const markStepIncomplete = useCallback((step: SetupStep) => {
    setCompletedSteps(prev => {
      const next = new Set(prev)
      next.delete(step)
      return next
    })
  }, [])

  // Helper to compute visible steps for a given provider (used in refreshSetupState where emailProvider state isn't set yet)
  const getVisibleStepsForProvider = useCallback((provider: 'google' | 'microsoft' | 'custom' | null): SetupStep[] => {
    return ['email', 'calendar', 'website', 'quiz', 'static-quiz', 'complete']
  }, [])

  // Get the visible steps (depends on email provider — custom IMAP needs calendar step)
  const getVisibleSteps = useCallback((): SetupStep[] => {
    return getVisibleStepsForProvider(emailProvider)
  }, [emailProvider, getVisibleStepsForProvider])

  const goToNextStep = useCallback(() => {
    const visibleSteps = getVisibleSteps()
    const currentIndex = visibleSteps.indexOf(currentStep)
    if (currentIndex >= 0 && currentIndex < visibleSteps.length - 1) {
      setCurrentStepWithNative(visibleSteps[currentIndex + 1])
    }
  }, [currentStep, getVisibleSteps])

  const goToPreviousStep = useCallback(() => {
    const visibleSteps = getVisibleSteps()
    const currentIndex = visibleSteps.indexOf(currentStep)
    if (currentIndex > 0) {
      setCurrentStepWithNative(visibleSteps[currentIndex - 1])
    }
  }, [currentStep, getVisibleSteps])

  const isStepComplete = useCallback((step: SetupStep) => {
    return completedSteps.has(step)
  }, [completedSteps])

  // Check if user can navigate to a specific step
  const canGoToStep = useCallback((step: SetupStep): boolean => {
    const visibleSteps = getVisibleSteps()
    const stepIndex = visibleSteps.indexOf(step)

    // Can always go to first step
    if (stepIndex === 0) return true

    // Can go to a step if all previous steps are complete
    for (let i = 0; i < stepIndex; i++) {
      if (!completedSteps.has(visibleSteps[i])) {
        return false
      }
    }
    return true
  }, [completedSteps, getVisibleSteps])

  // Navigate directly to a step
  const goToStep = useCallback((step: SetupStep) => {
    const visibleSteps = getVisibleSteps()
    if (visibleSteps.includes(step) && canGoToStep(step)) {
      setCurrentStepWithNative(step)
    }
  }, [canGoToStep, getVisibleSteps])

  return (
    <SetupContext.Provider
      value={{
        isLoading,
        currentStep,
        emailProvider,
        calendarProvider,
        customEmail,
        websiteUrl,
        connectedEmail,
        serviceId,
        setCurrentStep: setCurrentStepWithNative,
        setEmailProvider,
        setCalendarProvider,
        setCustomEmail,
        setWebsiteUrl,
        setConnectedEmail,
        goToNextStep,
        goToPreviousStep,
        goToStep,
        canGoToStep,
        isStepComplete,
        markStepComplete,
        markStepIncomplete,
        needsCalendarStep,
        getVisibleSteps,
      }}
    >
      {children}
    </SetupContext.Provider>
  )
}

export function useSetup() {
  const context = useContext(SetupContext)
  if (!context) {
    throw new Error('useSetup must be used within a SetupProvider')
  }
  return context
}
