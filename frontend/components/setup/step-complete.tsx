'use client'

import { useState, useEffect, useRef } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/lib/context/auth-context'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { CheckCircle2, Mail, Calendar, MessageSquare, ArrowRight, Loader2 } from 'lucide-react'
import confetti from 'canvas-confetti'

const COMPLETED_ITEMS = [
  {
    icon: Mail,
    title: 'Email Connected',
    description: 'Your email inbox is now linked to Corretto',
  },
  {
    icon: Calendar,
    title: 'Calendars Synced',
    description: 'Your calendars are ready for smart scheduling',
  },
  {
    icon: MessageSquare,
    title: 'Profile Created',
    description: 'Corretto understands your preferences',
  },
]

export function StepComplete() {
  const router = useRouter()
  const { currentSubscription, markSubscriptionConfigured } = useAuth()
  const [isNavigating, setIsNavigating] = useState(false)
  const [countdown, setCountdown] = useState(5) // 5 seconds countdown
  const [autoRedirect, setAutoRedirect] = useState(true)
  const [isReady, setIsReady] = useState(false)
  const hasMarkedConfigured = useRef(false)

  // Mark subscription as configured on mount (only once)
  useEffect(() => {
    if (!hasMarkedConfigured.current) {
      hasMarkedConfigured.current = true
      markSubscriptionConfigured()
    }
    // Small delay to ensure smooth render
    const timer = setTimeout(() => setIsReady(true), 100)
    return () => clearTimeout(timer)
  }, [markSubscriptionConfigured])

  // Auto-redirect countdown - only start after component is ready
  useEffect(() => {
    if (!autoRedirect || isNavigating || !isReady) return

    if (countdown <= 0) {
      setIsNavigating(true)
      // Small delay before navigation to show the "Redirecting..." state
      setTimeout(() => {
        router.push('/dashboard')
      }, 500)
      return
    }

    const timer = setTimeout(() => {
      setCountdown(prev => prev - 1)
    }, 1000)

    return () => clearTimeout(timer)
  }, [countdown, autoRedirect, isNavigating, isReady, router])

  // Trigger confetti on mount
  useEffect(() => {
    const duration = 2 * 1000
    const animationEnd = Date.now() + duration
    const defaults = { startVelocity: 30, spread: 360, ticks: 60, zIndex: 0 }

    function randomInRange(min: number, max: number) {
      return Math.random() * (max - min) + min
    }

    const interval: ReturnType<typeof setInterval> = setInterval(function () {
      const timeLeft = animationEnd - Date.now()

      if (timeLeft <= 0) {
        return clearInterval(interval)
      }

      const particleCount = 50 * (timeLeft / duration)

      confetti({
        ...defaults,
        particleCount,
        origin: { x: randomInRange(0.1, 0.3), y: Math.random() - 0.2 },
      })
      confetti({
        ...defaults,
        particleCount,
        origin: { x: randomInRange(0.7, 0.9), y: Math.random() - 0.2 },
      })
    }, 250)

    return () => clearInterval(interval)
  }, [])

  const handleGoToDashboard = async () => {
    setAutoRedirect(false)
    setIsNavigating(true)
    // Small delay before navigation for better UX
    setTimeout(() => {
      router.push('/dashboard')
    }, 500)
  }

  // Show nothing until ready to prevent flash
  if (!isReady) {
    return null
  }

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      <div className="text-center">
        <div className="inline-flex h-16 w-16 items-center justify-center rounded-full bg-green-100 mb-4">
          <CheckCircle2 className="h-8 w-8 text-green-600" />
        </div>
        <h2 className="text-2xl font-bold">You&apos;re All Set!</h2>
        <p className="text-muted-foreground mt-2">
          {currentSubscription?.name} is now configured and ready to use
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Setup Complete</CardTitle>
          <CardDescription>
            Here&apos;s what we&apos;ve configured for you
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {COMPLETED_ITEMS.map((item, index) => {
              const Icon = item.icon
              return (
                <div
                  key={index}
                  className="flex items-center gap-4 p-3 rounded-lg bg-muted/50"
                >
                  <div className="flex h-10 w-10 items-center justify-center rounded-full bg-green-100">
                    <Icon className="h-5 w-5 text-green-600" />
                  </div>
                  <div>
                    <h4 className="font-medium">{item.title}</h4>
                    <p className="text-sm text-muted-foreground">
                      {item.description}
                    </p>
                  </div>
                  <CheckCircle2 className="h-5 w-5 text-green-600 ml-auto" />
                </div>
              )
            })}
          </div>
        </CardContent>
      </Card>

      <Card className="bg-primary text-primary-foreground">
        <CardContent className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-semibold text-lg">Ready to get started?</h3>
              <p className="text-primary-foreground/80 text-sm mt-1">
                Explore your dashboard and let Corretto help you manage your emails
                and calendar.
              </p>
            </div>
            <Button
              onClick={handleGoToDashboard}
              variant="secondary"
              size="lg"
              className="gap-2"
              disabled={isNavigating}
            >
              {isNavigating ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Redirecting...
                </>
              ) : (
                <>
                  Go to Dashboard {countdown > 0 && `(${countdown})`}
                  <ArrowRight className="h-4 w-4" />
                </>
              )}
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
