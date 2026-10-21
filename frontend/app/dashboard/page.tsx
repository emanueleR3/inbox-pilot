'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth, useSubscriptionConfig } from "@/lib/context/auth-context"
import { Skeleton } from "@/components/ui/skeleton"
import { DashboardTabs } from "@/components/dashboard/dashboard-tabs"

export default function DashboardPage() {
  const router = useRouter()
  const { isLoading, isAuthenticated } = useAuth()
  const { isConfigured } = useSubscriptionConfig()
  const [isReady, setIsReady] = useState(false)

  // Redirect to login if not authenticated
  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push('/login')
    }
  }, [isLoading, isAuthenticated, router])

  // Redirect to setup if not configured
  useEffect(() => {
    if (!isLoading && isAuthenticated && !isConfigured) {
      router.push('/setup')
    }
  }, [isLoading, isAuthenticated, isConfigured, router])

  // Set ready state after auth checks pass
  useEffect(() => {
    if (!isLoading && isAuthenticated && isConfigured) {
      // Small delay to ensure contexts are fully synced
      const timer = setTimeout(() => setIsReady(true), 100)
      return () => clearTimeout(timer)
    }
  }, [isLoading, isAuthenticated, isConfigured])

  if (isLoading || !isReady) {
    return (
      <div className="flex min-h-[calc(100vh-4rem)] items-center justify-center">
        <div className="space-y-4 w-full max-w-md p-8">
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-4 w-full" />
          <div className="space-y-2 mt-8">
            <Skeleton className="h-64 w-full" />
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="animate-in fade-in duration-300">
      <DashboardTabs />
    </div>
  )
}
