'use client'

import { useState, useEffect, useRef } from 'react'
import { useSetup } from '@/lib/context/setup-context'
import { useAuth } from '@/lib/context/auth-context'
import { useLanguage } from '@/lib/context/language-context'
import { backendService, type ScrapingStatusResponse } from '@/lib/api/backend-service'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Field, FieldLabel } from '@/components/ui/field'
import { toast } from 'sonner'
import { Loader2, Globe, CheckCircle2, XCircle, Sparkles, AlertTriangle } from 'lucide-react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { EmailCatcherGame } from '@/components/setup/email-catcher-game'
import gsap from 'gsap'

type ScrapingState = 'idle' | 'discovery' | 'scraping' | 'processing' | 'cleaning' | 'embedding' | 'completed' | 'error'

export function StepWebsite() {
  const { setWebsiteUrl, markStepComplete, goToNextStep, connectedEmail } = useSetup()
  const { currentSubscription } = useAuth()
  const { t } = useLanguage()

  const [url, setUrl] = useState('')
  const [state, setState] = useState<ScrapingState>('idle')
  const [progress, setProgress] = useState<ScrapingStatusResponse['progress']>()
  const [showLegalModal, setShowLegalModal] = useState(false)

  // Refs for animations
  const cardRef = useRef<HTMLDivElement>(null)
  const globeRef = useRef<SVGSVGElement>(null)
  const sparklesRef = useRef<HTMLDivElement>(null)
  const progressBarRef = useRef<HTMLDivElement>(null)

  /* New State */
  const [discoveredUrls, setDiscoveredUrls] = useState<string[]>([])
  const [selectedUrls, setSelectedUrls] = useState<Set<string>>(new Set())
  const [isDiscovering, setIsDiscovering] = useState(false)

  // GSAP animations
  useEffect(() => {
    if (cardRef.current) {
      gsap.fromTo(
        cardRef.current,
        { opacity: 0, y: 20 },
        { opacity: 1, y: 0, duration: 0.5, ease: 'power2.out' }
      )
    }
  }, [])

  // Globe animation when scraping or discovering
  useEffect(() => {
    if ((state === 'scraping' || isDiscovering) && globeRef.current) {
      gsap.to(globeRef.current, {
        rotation: 360,
        duration: 2,
        repeat: -1,
        ease: 'none'
      })
    }
  }, [state, isDiscovering])

  // Sparkles animation when completed
  useEffect(() => {
    if (state === 'completed' && sparklesRef.current) {
      const sparkles = sparklesRef.current.children
      gsap.fromTo(
        sparkles,
        {
          opacity: 0,
          scale: 0,
          y: 20
        },
        {
          opacity: 1,
          scale: 1,
          y: 0,
          duration: 0.6,
          stagger: 0.1,
          ease: 'back.out(1.7)'
        }
      )
    }
  }, [state])

  // Progress bar animation
  useEffect(() => {
    if (progressBarRef.current && progress) {
      const total = 5 // Total steps: scraping, chunking, cleaning, embedding, uploading
      let completed = 0

      if (progress.pages_scraped && progress.pages_scraped > 0) completed++
      if (progress.chunks_created && progress.chunks_created > 0) completed++
      if (progress.chunks_cleaned && progress.chunks_cleaned > 0) completed++
      if (progress.chunks_embedded && progress.chunks_embedded > 0) completed++
      if (progress.chunks_uploaded && progress.chunks_uploaded > 0) completed++

      const percentage = (completed / total) * 100

      gsap.to(progressBarRef.current, {
        width: `${percentage}%`,
        duration: 0.5,
        ease: 'power2.out'
      })
    }
  }, [progress])

  const validateUrl = (urlString: string): boolean => {
    try {
      const urlObj = new URL(urlString)
      return urlObj.protocol === 'http:' || urlObj.protocol === 'https:'
    } catch {
      return false
    }
  }

  const pollStatus = async (email: string) => {
    const maxAttempts = 60 // 5 minutes max (60 * 5 seconds)
    let attempts = 0

    const poll = async () => {
      try {
        const status = await backendService.getScrapingStatus(email)
        console.log('[SETUP DEBUG] step-website → GET /scraper/status RESPONSE', { email, status })

        setProgress(status.progress)

        // Update state based on status
        if (status.status === 'completed') {
          setState('completed')
          toast.success(t('setup.websiteSuccess'))

          // Animate completion
          setTimeout(() => {
            markStepComplete('website')
            setWebsiteUrl(url)
            goToNextStep()
          }, 2000)

          return
        }

        if (status.status === 'failed') {
          setState('error')
          toast.error(status.error || t('setup.websiteError'))
          return
        }

        // Update state based on current step in progress
        if (status.progress?.step) {
          const step = status.progress.step.toLowerCase()
          if (step.includes('scraping') || step.includes('initializing')) {
            setState('scraping')
          } else if (step.includes('chunking')) {
            setState('processing')
          } else if (step.includes('cleaning')) {
            setState('cleaning')
          } else if (step.includes('embedding') || step.includes('uploading') || step.includes('updating')) {
            setState('embedding')
          }
        }

        // Continue polling
        attempts++
        if (attempts < maxAttempts) {
          setTimeout(poll, 5000) // Poll every 5 seconds
        } else {
          setState('error')
          toast.error(t('setup.websiteTimeout'))
        }
      } catch (error) {
        console.error('[StepWebsite] Poll error:', error)
        setState('error')
        toast.error(t('setup.websiteError'))
      }
    }

    poll()
  }

  const handleAnalyzeClick = async () => {
    if (!url) {
      toast.error(t('setup.websiteInvalidUrl'))
      return
    }

    if (!validateUrl(url)) {
      toast.error(t('setup.websiteInvalidUrl'))
      return
    }

    setIsDiscovering(true)
    try {
      console.log('[SETUP DEBUG] step-website → POST /scraper/research', { website_url: url, max_urls: 200 })
      const response = await backendService.discoverUrls(url)
      console.log('[SETUP DEBUG] step-website → POST /scraper/research RESPONSE', response)
      setDiscoveredUrls(response.urls)
      // Default select all
      setSelectedUrls(new Set(response.urls))
      setState('discovery')
    } catch (error) {
      console.error('[StepWebsite] Discovery Error:', error)
      toast.error(t('setup.websiteDiscoverFailed'))
    } finally {
      setIsDiscovering(false)
    }
  }

  const handleUrlToggle = (pageUrl: string) => {
    const newSelected = new Set(selectedUrls)
    if (newSelected.has(pageUrl)) {
      newSelected.delete(pageUrl)
    } else {
      newSelected.add(pageUrl)
    }
    setSelectedUrls(newSelected)
  }

  const handleSelectAll = (select: boolean) => {
    if (select) {
      setSelectedUrls(new Set(discoveredUrls))
    } else {
      setSelectedUrls(new Set())
    }
  }

  const handleStartScrapingClick = () => {
    if (selectedUrls.size === 0) {
      toast.error(t('setup.websiteSelectOneUrl'))
      return
    }

    if (!currentSubscription?.subscription_id) {
      toast.error(t('setup.websiteNoSubscription'))
      return
    }

    setShowLegalModal(true)
  }

  const handleConfirmScraping = async () => {
    setShowLegalModal(false)
    setState('scraping')

    try {
      // Get subscription service to find the connected email
      console.log('[SETUP DEBUG] step-website → GET /get_subscription_service', { subscription_id: currentSubscription!.subscription_id })
      const serviceData = await backendService.getSubscriptionService(currentSubscription!.subscription_id)
      console.log('[SETUP DEBUG] step-website → GET /get_subscription_service RESPONSE', serviceData)
      const services = Array.isArray(serviceData) ? serviceData : (serviceData ? [serviceData] : [])

      // Find the service that matches the connected email from the setup context
      // Fall back to the first service with a valid email if no match
      const service = services.find(s => s?.email === connectedEmail)
        || services.find(s => s?.email && typeof s.email === 'string' && s.email.length > 0)
        || null

      if (!service || !service.email || typeof service.email !== 'string') {
        throw new Error(t('setup.websiteNoEmailService'))
      }

      const scrapingPayload = {
        email: service.email,
        website_url: url,
        urls: Array.from(selectedUrls),
      }
      console.log('[SETUP DEBUG] step-website → POST /scraper/start', scrapingPayload)

      await backendService.startScraping(scrapingPayload)
      console.log('[SETUP DEBUG] step-website → POST /scraper/start DONE')

      // Start polling for status using email
      pollStatus(service.email)
    } catch (error) {
      console.error('[StepWebsite] Error:', error)
      setState('error')
      toast.error(error instanceof Error ? error.message : t('setup.websiteError'))
    }
  }

  const handleSkip = () => {
    markStepComplete('website')
    goToNextStep()
  }

  const getStateMessage = (): string => {
    switch (state) {
      case 'discovery':
        return t('setup.websiteSelectPages')
      case 'scraping':
        return t('setup.websiteScraping')
      case 'processing':
        return t('setup.websiteProcessing')
      case 'cleaning':
        return t('setup.websiteCleaning')
      case 'embedding':
        return t('setup.websiteEmbedding')
      case 'completed':
        return t('setup.websiteCompleted')
      case 'error':
        return t('setup.websiteError')
      default:
        return ''
    }
  }

  const isProcessing = ['scraping', 'processing', 'cleaning', 'embedding'].includes(state) || isDiscovering

  return (
    <div ref={cardRef} className="w-full flex flex-col relative space-y-2">
      <div className="text-center pb-1 w-full max-w-md mx-auto">
        <h3 className="text-xl font-semibold tracking-tight">{t('setup.websiteTitle')}</h3>
        <p className="text-xs text-muted-foreground mt-1">{t('setup.websiteDescription')}</p>
      </div>
      <div className="space-y-4 flex flex-col pt-2 w-full">
        {/* URL Input */}
        {(state === 'idle' || state === 'discovery') && !isProcessing && (
          <Field>
            <FieldLabel htmlFor="website-url">{t('setup.websiteUrlLabel')}</FieldLabel>
            <Input
              id="website-url"
              type="url"
              placeholder={t('setup.websiteUrlPlaceholder')}
              value={url}
              onChange={(e) => {
                setUrl(e.target.value)
                if (state === 'discovery') setState('idle') // Reset if changed
              }}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  handleAnalyzeClick()
                }
              }}
              disabled={state === 'discovery'}
            />
          </Field>
        )}

        {/* Discovery UI */}
        {state === 'discovery' && !isProcessing && (
          <div className="space-y-2">
            <div className="flex justify-between items-center mb-1">
              <h4 className="text-xs font-medium">{t('setup.websiteDiscoveredPages')} ({discoveredUrls.length})</h4>
              <div className="space-x-2">
                <Button variant="ghost" size="sm" onClick={() => handleSelectAll(true)} className="text-xs h-6 px-2">{t('setup.websiteSelectAll')}</Button>
                <Button variant="ghost" size="sm" onClick={() => handleSelectAll(false)} className="text-xs h-6 px-2">{t('setup.websiteSelectNone')}</Button>
              </div>
            </div>
            <div className="border rounded-md max-h-[180px] overflow-y-auto p-1.5 space-y-0.5 bg-muted/30">
              {discoveredUrls.map((pageUrl, i) => (
                <div key={i} className="flex items-start space-x-2 p-1.5 hover:bg-muted rounded-md cursor-pointer" onClick={() => handleUrlToggle(pageUrl)}>
                  <div className={`mt-0.5 w-3.5 h-3.5 rounded border flex items-center justify-center transition-colors ${selectedUrls.has(pageUrl) ? 'bg-primary border-primary text-primary-foreground' : 'border-muted-foreground'}`}>
                    {selectedUrls.has(pageUrl) && <CheckCircle2 className="w-2.5 h-2.5" />}
                  </div>
                  <span className="text-xs break-all leading-tight">{pageUrl}</span>
                </div>
              ))}
            </div>
            <div className="flex justify-between items-center text-[10px] text-muted-foreground">
              <span>{selectedUrls.size} {t('setup.websitePagesSelected')}</span>
            </div>
          </div>
        )}


        {/* Processing State */}
        {isProcessing && (
          <div className="space-y-4">
            {/* Email Catcher Minigame */}
            {!isDiscovering && (
              <EmailCatcherGame />
            )}

            {/* Discovering loader (keep globe for quick discovery phase) */}
            {isDiscovering && (
              <div className="flex justify-center py-4">
                <div className="relative">
                  <Globe
                    ref={globeRef}
                    className="h-16 w-16 text-primary"
                    strokeWidth={1.5}
                  />
                  <div className="absolute inset-0 flex items-center justify-center">
                    <div className="h-20 w-20 animate-spin-slow">
                      <div className="absolute top-0 left-1/2 h-1.5 w-1.5 -translate-x-1/2 rounded-full bg-primary/60" />
                      <div className="absolute bottom-0 left-1/2 h-1.5 w-1.5 -translate-x-1/2 rounded-full bg-primary/60" />
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Progress Message */}
            <div className="text-center">
              <p className="text-sm font-medium">{isDiscovering ? t('setup.websiteScanning') : getStateMessage()}</p>
              {progress && (
                <div className="mt-2 space-y-1 text-xs text-muted-foreground">
                  {progress.pages_scraped !== undefined && (
                    <p>{t('setup.websitePagesScraped')} {progress.pages_scraped}</p>
                  )}
                  {progress.chunks_created !== undefined && (
                    <p>{t('setup.websiteChunksCreated')} {progress.chunks_created}</p>
                  )}
                  {progress.chunks_cleaned !== undefined && (
                    <p>{t('setup.websiteChunksCleaned')} {progress.chunks_cleaned}</p>
                  )}
                  {progress.chunks_embedded !== undefined && (
                    <p>{t('setup.websiteChunksEmbedded')} {progress.chunks_embedded}</p>
                  )}
                </div>
              )}
            </div>

            {/* Progress Bar */}
            {!isDiscovering && (
              <div className="relative h-2 overflow-hidden rounded-full bg-secondary">
                <div
                  ref={progressBarRef}
                  className="h-full bg-gradient-to-r from-primary to-primary/60"
                  style={{ width: '0%' }}
                />
              </div>
            )}
          </div>
        )}

        {/* Completed State */}
        {state === 'completed' && (
          <div className="space-y-3 py-4">
            <div className="flex justify-center">
              <div ref={sparklesRef} className="relative flex items-center justify-center">
                <CheckCircle2 className="h-16 w-16 text-green-500" />
                <Sparkles className="absolute -top-3 -right-3 h-6 w-6 text-yellow-500" />
                <Sparkles className="absolute -bottom-3 -left-3 h-4 w-4 text-yellow-500" />
                <Sparkles className="absolute top-0 left-0 h-4 w-4 text-yellow-500" />
              </div>
            </div>
            <p className="text-center text-sm font-medium text-green-600 dark:text-green-400">
              {getStateMessage()}
            </p>
          </div>
        )}

        {/* Error State */}
        {state === 'error' && (
          <div className="space-y-3 py-4">
            <div className="flex justify-center">
              <XCircle className="h-16 w-16 text-destructive" />
            </div>
            <p className="text-center text-sm font-medium text-destructive">
              {getStateMessage()}
            </p>
            <Button
              onClick={() => {
                setState('idle')
                setProgress(undefined)
              }}
              variant="outline"
              className="w-full"
            >
              {t('setup.websiteTryAgain')}
            </Button>
          </div>
        )}

        {/* Action Buttons */}
        {(state === 'idle' || state === 'discovery') && !isProcessing && (
          <div className="flex gap-3">
            <Button
              onClick={handleSkip}
              variant="outline"
              className="flex-1"
              disabled={isDiscovering}
            >
              {t('setup.websiteSkip')}
            </Button>
            <Button
              onClick={state === 'discovery' ? handleStartScrapingClick : handleAnalyzeClick}
              disabled={!url || isProcessing || (state === 'discovery' && selectedUrls.size === 0)}
              className="flex-1"
            >
              {isProcessing && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              {state === 'discovery' ? t('setup.websiteStartScraping') : t('setup.websiteAnalyze')}
            </Button>
          </div>
        )}
      </div>

      <Dialog open={showLegalModal} onOpenChange={setShowLegalModal}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-yellow-500" />
              {t('setup.websiteLegalTitle')}
            </DialogTitle>
            <DialogDescription>
              {t('setup.websiteLegalDescription')}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowLegalModal(false)}>
              {t('setup.websiteLegalCancel')}
            </Button>
            <Button onClick={handleConfirmScraping}>
              {t('setup.websiteLegalConfirm')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
