'use client'

import { useMemo, useState, useEffect } from 'react'
import Image from 'next/image'
import { useRouter } from 'next/navigation'
import { useSetup, type SetupStep } from '@/lib/context/setup-context'
import { useAuth } from '@/lib/context/auth-context'
import { useLanguage } from '@/lib/context/language-context'
import { Progress } from '@/components/ui/progress'
import { Skeleton } from '@/components/ui/skeleton'
import { Button } from '@/components/ui/button'
import { motion, AnimatePresence } from "motion/react"
import { TextGenerateEffect } from "@/components/ui/text-generate-effect"
import { TextAnimate } from "@/components/ui/text-animate"
import { WaveGridBackground } from "@/components/ui/wave-grid-background"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { cn } from '@/lib/utils'
import { Mail, Calendar, Globe, MessageSquare, CheckCircle2, LogOut, ChevronDown, User } from 'lucide-react'
import { StepEmail } from '@/components/setup/step-email'
import { StepCalendar } from '@/components/setup/step-calendar'
import { StepWebsite } from '@/components/setup/step-website'
import { StepQuiz } from '@/components/setup/step-quiz'
import { StepStaticQuiz } from '@/components/setup/step-static-quiz'
import { ThemeLanguageSwitcher } from '@/components/theme-language-switcher'

const STEP_CONFIG: { id: SetupStep; labelKey: string; icon: React.ElementType }[] = [
  { id: 'email', labelKey: 'setup.email', icon: Mail },
  { id: 'calendar', labelKey: 'setup.calendar', icon: Calendar },
  { id: 'website', labelKey: 'setup.website', icon: Globe },
  { id: 'quiz', labelKey: 'setup.quiz', icon: MessageSquare },
  { id: 'static-quiz', labelKey: 'setup.calendar_prefs', icon: Calendar },
]

export default function SetupPage() {
  const router = useRouter()
  const { currentStep, isLoading: setupLoading, isStepComplete, getVisibleSteps, canGoToStep, goToStep } = useSetup()
  const { currentSubscription, isLoading, isAuthenticated, logout, session } = useAuth()
  const { t } = useLanguage()
  const [isReady, setIsReady] = useState(false)

  // Set ready state after auth loads
  useEffect(() => {
    if (!isLoading && isAuthenticated) {
      const timer = setTimeout(() => setIsReady(true), 100)
      return () => clearTimeout(timer)
    }
  }, [isLoading, isAuthenticated])

  useEffect(() => {
    if (!setupLoading && currentStep === 'complete') {
      router.push('/dashboard')
    }
  }, [setupLoading, currentStep, router])

  const visibleSteps = useMemo(() => {
    const steps = getVisibleSteps()
    return STEP_CONFIG.filter(step => steps.includes(step.id))
  }, [getVisibleSteps])

  const currentStepIndex = visibleSteps.findIndex((s) => s.id === currentStep)

  const handleLogout = async () => {
    await logout()
    router.push('/login')
  }

  const handleStepClick = (stepId: SetupStep) => {
    if (canGoToStep(stepId)) {
      goToStep(stepId)
    }
  }

  const getStepDescription = (stepId: SetupStep) => {
    switch (stepId) {
      case 'email': return t('setup.email_desc') || "Collega la tua casella per importare e gestire i messaggi in modo sicuro."
      case 'calendar': return t('setup.calendar_desc') || "Sincronizza i tuoi appuntamenti per organizzare al meglio il tempo."
      case 'static-quiz': return t('setup.calendar_prefs_desc') || "Definisci i tuoi orari lavorativi e le regole di prenotazione."
      case 'website': return t('setup.website_desc') || "Condividi il tuo sito e documenti per istruire la AI sul tuo business."
      case 'quiz': return t('setup.quiz_desc') || "Rispondi a poche domande per finalizzare le configurazioni."
      default: return "Inizia il tuo viaggio con Corretto."
    }
  }

  if (isLoading || !isReady) {
    return (
      <div className="flex min-h-svh w-full items-center justify-center p-6 md:p-10">
        <div className="w-full max-w-md space-y-8">
          <div className="flex justify-center">
            <Skeleton className="h-16 w-16 rounded-xl" />
          </div>
          <div className="space-y-4">
            <Skeleton className="h-4 w-full" />
            <div className="flex justify-between">
              {[1, 2, 3].map((i) => (
                <Skeleton key={i} className="h-12 w-20 rounded-lg" />
              ))}
            </div>
          </div>
          <Skeleton className="h-[400px] w-full rounded-xl" />
        </div>
      </div>
    )
  }

  return (
    <div className="relative min-h-svh w-full bg-background overflow-hidden flex flex-col items-center animate-in fade-in duration-500">
      {/* Immersive Animated Background */}
      <div className="absolute inset-0 z-0">
        <WaveGridBackground color="hsl(var(--primary) / 0.15)" waveSpeed={0.8} />
      </div>
      <div className="absolute inset-0 z-0 bg-background/40 backdrop-blur-[2px] pointer-events-none" />

      {/* Absolute positioned UI elements */}
      <div className="absolute left-4 top-4 z-50 flex items-center">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" className="text-muted-foreground text-sm flex items-center bg-background/60 backdrop-blur-md hover:bg-background/80 transition-all rounded-full px-4">
              <User className="h-4 w-4 mr-2" />
              <span className="hidden sm:inline-block truncate max-w-[150px]">{session?.user?.email}</span>
              <ChevronDown className="h-4 w-4 ml-1 sm:ml-2" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="start" className="rounded-xl">
            <DropdownMenuItem disabled className="text-xs text-muted-foreground">
              {currentSubscription?.name || 'Workspace'}
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={handleLogout} className="text-destructive">
              <LogOut className="h-4 w-4 mr-2" />
              {t('nav.logout')}
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      <div className="absolute right-4 top-4 z-50 flex items-center">
        <ThemeLanguageSwitcher fixed={false} />
      </div>

      {/* Main Centered Wizard Container */}
      <div className="relative z-10 w-full flex-1 flex flex-col items-center justify-start p-4 sm:p-4 md:p-6 lg:p-8 pt-24 sm:pt-28 md:pt-32">

        <div className="w-full max-w-4xl flex flex-col gap-4 sm:gap-6">

          {/* Dynamic Header */}
          <div className="flex flex-col items-center text-center w-full max-w-2xl mx-auto mb-2">
            <motion.div
              initial={{ opacity: 0, y: -20, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              transition={{ duration: 0.5, type: 'spring' }}
              className="mb-2 flex justify-center"
            >
              <div className="p-2 sm:p-3">
                <Image src="/corretto-avatar.png" alt="Corretto" width={48} height={48} className="object-contain drop-shadow-sm" priority />
              </div>
            </motion.div>

            <AnimatePresence mode="wait">
              <motion.div
                key={`header-${currentStep}`}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                transition={{ duration: 0.4 }}
                className="w-full"
              >
                <h2 className="text-xl sm:text-2xl lg:text-3xl font-heading font-bold tracking-tight text-foreground mb-1 drop-shadow-sm">
                  <TextGenerateEffect words={t(visibleSteps.find(s => s.id === currentStep)?.labelKey || 'Configurazione') as string} duration={0.8} />
                </h2>
                <div className="text-sm sm:text-base text-muted-foreground font-light tracking-wide max-w-lg mx-auto">
                  <TextAnimate animation="fadeIn" by="character" once delay={0.1} duration={0.4}>
                    {getStepDescription(currentStep as SetupStep)}
                  </TextAnimate>
                </div>
              </motion.div>
            </AnimatePresence>
          </div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.2 }}
            className="w-full bg-background/70 backdrop-blur-2xl border border-white/10 dark:border-white/5 shadow-2xl rounded-3xl p-4 sm:p-6 md:p-8 flex flex-col gap-6 relative overflow-hidden glassmorphism-styles"
          >
            {/* Subtle inner top highlight */}
            <div className="absolute top-0 inset-x-0 h-px bg-gradient-to-r from-transparent via-primary/30 to-transparent" />

            {/* Stepper Progress Indicator */}
            <div className="w-full mx-auto relative z-20">
              <div className="flex justify-between gap-1 sm:gap-2">
                {visibleSteps.map((step, index) => {
                  const Icon = step.icon
                  const isComplete = isStepComplete(step.id)
                  const isActive = step.id === currentStep
                  const isPast = index < currentStepIndex
                  const canClick = canGoToStep(step.id)

                  let progress = 0
                  if (isComplete || isPast) progress = 100
                  else if (isActive) progress = 50

                  return (
                    <div key={step.id} className="flex-1 flex flex-col gap-3">
                      <div className="w-full px-1">
                        <Progress
                          value={progress}
                          className={cn(
                            "h-1.5 transition-all duration-700 bg-muted/80 backdrop-blur-sm",
                            (isComplete || isPast) && "[&>div]:bg-green-500",
                            isActive && !isComplete && !isPast && "[&>div]:bg-primary shadow-[0_0_10px_rgba(var(--primary),0.5)]"
                          )}
                        />
                      </div>

                      <button
                        onClick={() => handleStepClick(step.id)}
                        disabled={!canClick}
                        className={cn(
                          'flex flex-col items-center gap-2 transition-all w-full group mt-1',
                          canClick && 'cursor-pointer hover:opacity-80',
                          !canClick && 'cursor-not-allowed opacity-50'
                        )}
                      >
                        <div
                          className={cn(
                            'flex h-8 w-8 sm:h-10 sm:w-10 items-center justify-center rounded-full border border-border/50 transition-all duration-500 backdrop-blur-md',
                            (isComplete || isPast) && 'border-green-500/50 bg-green-500 text-white shadow-lg shadow-green-500/30',
                            isActive && !isComplete && !isPast && 'border-primary bg-primary text-primary-foreground shadow-lg shadow-primary/40 scale-110',
                            !isActive && !isComplete && !isPast && 'bg-muted/50 text-muted-foreground group-hover:bg-muted group-hover:border-border'
                          )}
                        >
                          {(isComplete || isPast) ? (
                            <CheckCircle2 className="h-4 w-4 sm:h-5 sm:w-5" />
                          ) : (
                            <Icon className={cn("h-3.5 w-3.5 sm:h-4 sm:w-4 transition-all duration-300", isActive && "h-4 w-4 sm:h-5 sm:w-5")} />
                          )}
                        </div>
                        <span className={cn(
                          'hidden sm:block text-[11px] font-medium text-center transition-colors px-1 max-w-full truncate',
                          (isComplete || isPast) && 'text-green-600 dark:text-green-400',
                          isActive && !isComplete && !isPast && 'text-foreground font-semibold',
                          !isActive && !isComplete && !isPast && 'text-muted-foreground/70'
                        )}>
                          {t(step.labelKey)}
                        </span>
                      </button>
                    </div>
                  )
                })}
              </div>
            </div>

            {/* Setup Form Step Content */}
            <div className="w-full relative z-20">
              <AnimatePresence mode="wait">
                <motion.div
                  key={currentStep}
                  initial={{ opacity: 0, scale: 0.98, y: 10 }}
                  animate={{ opacity: 1, scale: 1, y: 0 }}
                  exit={{ opacity: 0, scale: 0.98, y: -10 }}
                  transition={{ duration: 0.4, ease: "easeOut" }}
                  className="w-full"
                >
                  {/* Inner components should not have bulky cards anymore to blend smoothly */}
                  {currentStep === 'email' && <StepEmail />}
                  {currentStep === 'website' && <StepWebsite />}
                  {currentStep === 'quiz' && <StepQuiz />}
                  {currentStep === 'calendar' && <StepCalendar />}
                  {currentStep === 'static-quiz' && <StepStaticQuiz />}
                </motion.div>
              </AnimatePresence>
            </div>

          </motion.div>
        </div>
      </div>
    </div>
  )
}
