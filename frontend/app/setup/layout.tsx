'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/lib/context/auth-context'
import { SetupProvider } from '@/lib/context/setup-context'
import { Skeleton } from '@/components/ui/skeleton'

export default function SetupLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const router = useRouter()
  const { isLoading, isAuthenticated, currentSubscription, activeServiceId } = useAuth()

  // Redirect to login if not authenticated
  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push('/login')
    }
  }, [isLoading, isAuthenticated, router])

  // Redirect to dashboard only if ALL services are configured,
  // or if the active service is specifically configured.
  // This allows users to configure new/incomplete services even when
  // other services under the same subscription are already configured.
  useEffect(() => {
    if (!isLoading && isAuthenticated && currentSubscription) {
      const services = currentSubscription.services || []

      // If there's an active service, check if IT is configured
      if (activeServiceId) {
        const activeService = services.find(s => s.service_id === activeServiceId)
        if (activeService) {
          const isActiveConfigured = !!activeService.config_completed
          if (isActiveConfigured) {
            router.push('/dashboard')
          }
          return // Active service found — don't fall through
        }
        // Active service not in local session (brand new) — stay on setup
        return
      }

      // No active service — fall back to subscription-level check
      const allConfigured = services.length > 0 && services.every(s => !!s.config_completed)
      if (allConfigured) {
        router.push('/dashboard')
      }
    }
  }, [isLoading, isAuthenticated, currentSubscription, activeServiceId, router])

  if (isLoading) {
    return (
      <div className="flex min-h-svh w-full items-center justify-center p-6 md:p-10">
        <div className="w-full max-w-md space-y-8">
          <div className="flex justify-center">
            <Skeleton className="h-16 w-16 rounded-xl" />
          </div>
          <div className="text-center space-y-2">
            <Skeleton className="h-6 w-32 mx-auto" />
            <Skeleton className="h-4 w-48 mx-auto" />
          </div>
          <Skeleton className="h-[400px] w-full rounded-xl" />
        </div>
      </div>
    )
  }

  return (
    <SetupProvider>
      <div className="min-h-svh bg-background">
        {children}
      </div>
    </SetupProvider>
  )
}
