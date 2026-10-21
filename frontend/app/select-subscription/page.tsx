'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Image from 'next/image'
import { useAuth } from '@/lib/context/auth-context'
import { useLanguage } from '@/lib/context/language-context'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { ThemeLanguageSwitcher } from '@/components/theme-language-switcher'
import { Building2, CheckCircle2, Settings, Loader2, ArrowRight, LogOut } from 'lucide-react'


function normalizeIsConfigured(value: boolean | string | undefined): boolean {
  if (typeof value === 'boolean') return value
  if (typeof value === 'string') return value.toLowerCase() === 'true'
  return false
}

export default function SelectSubscriptionPage() {
  const router = useRouter()
  const { isLoading, isAuthenticated, session, selectSubscription, logout } = useAuth()
  const { t } = useLanguage()

  useEffect(() => {
    if (!isLoading && !isAuthenticated) router.push('/login')
  }, [isLoading, isAuthenticated, router])

  const handleSelect = (id: string) => {
    selectSubscription(id)
    router.push('/service-list')
  }

  const handleLogout = async () => {
    await logout()
    router.push('/login')
  }

  if (isLoading) {
    return (
      <div className="flex min-h-svh w-full items-center justify-center p-6 md:p-10">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    )
  }

  const subscriptions = session?.subscriptions || []

  return (
    <div className="min-h-svh w-full bg-background text-foreground overflow-y-auto">
      <ThemeLanguageSwitcher />
      <div className="flex min-h-svh w-full items-start justify-center p-6 md:p-10 py-12 md:py-16">
        <div className="w-full max-w-2xl">
          {/* Logo */}
          <div className="flex justify-center mb-6">
            <Image src="/corretto-avatar.png" alt="Corretto" width={64} height={64} className="rounded-xl shadow-lg" priority />
          </div>

          <div className="text-center mb-8">
            <h1 className="text-3xl font-bold mb-2 text-foreground">{t('workspace.selectTitle')}</h1>
            <p className="text-muted-foreground">{t('workspace.selectDescription')}</p>
          </div>

          <div className="grid gap-4">
            {subscriptions.map((subscription) => {
              const isConfigured = normalizeIsConfigured(subscription.is_configurated)
              return (
                <Card
                  key={subscription.subscription_id}
                  className="cursor-pointer transition-all hover:border-primary border-border/50 bg-card shadow-sm group"
                  onClick={() => handleSelect(subscription.subscription_id)}
                >
                  <CardHeader className="pb-3">
                    <div className="flex items-start justify-between">
                      <div className="flex items-center gap-3">
                        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                          <Building2 className="h-5 w-5 text-primary" />
                        </div>
                        <div>
                          <CardTitle className="text-lg">{subscription.name}</CardTitle>
                          <CardDescription>{subscription.city}, {subscription.address}</CardDescription>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        {subscription.plan && (
                          <Badge variant="secondary" className="capitalize">{subscription.plan}</Badge>
                        )}
                        {isConfigured ? (
                          <Badge variant="outline" className="text-green-600 border-green-600">
                            <CheckCircle2 className="h-3 w-3 mr-1" />{t('workspace.ready')}
                          </Badge>
                        ) : (
                          <Badge variant="outline" className="text-amber-600 border-amber-600">
                            <Settings className="h-3 w-3 mr-1" />{t('workspace.setupRequired')}
                          </Badge>
                        )}
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className="flex items-center justify-between text-sm text-muted-foreground">
                      <span>
                        {subscription.active ? t('workspace.active') : t('workspace.inactive')}{' \u2022 '}
                        {subscription.vat_number || t('workspace.noVat')}
                      </span>
                      <div className="flex items-center gap-1 text-primary font-medium">
                        <span>{t('services.openDashboard')}</span>
                        <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
                      </div>
                    </div>
                  </CardContent>
                </Card>
              )
            })}

          </div>

          {/* Logout */}
          <div className="flex justify-center mt-6">
            <Button variant="ghost" size="sm" onClick={handleLogout} className="text-muted-foreground hover:text-red-500 gap-2">
              <LogOut className="h-4 w-4" />{t('nav.logout')}
            </Button>
          </div>
        </div>
      </div>
    </div>

  )
}
