'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Image from 'next/image'
import { useAuth } from '@/lib/context/auth-context'
import { useLanguage } from '@/lib/context/language-context'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { backendService, type SubscriptionServiceInfo } from '@/lib/api/backend-service'
import { toast } from 'sonner'
import { Loader2, Mail, Calendar, ArrowRight, ArrowLeft, Settings, Plus, CheckCircle2 } from 'lucide-react'
import { ThemeLanguageSwitcher } from '@/components/theme-language-switcher'



export default function ServiceListPage() {
  const router = useRouter()
  const { isLoading: authLoading, isAuthenticated, currentSubscription, setActiveServiceId, addServiceToSubscription } = useAuth()
  const { t } = useLanguage()

  const [isMounted, setIsMounted] = useState(false)
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false)
  const [newServiceName, setNewServiceName] = useState('')
  const [isCreating, setIsCreating] = useState(false)

  useEffect(() => { setIsMounted(true) }, [])

  useEffect(() => {
    if (!authLoading && !isAuthenticated) router.push('/login')
  }, [authLoading, isAuthenticated, router])

  useEffect(() => {
    if (!authLoading && isAuthenticated && !currentSubscription) {
      router.push('/select-subscription')
    }
  }, [authLoading, isAuthenticated, currentSubscription, router])

  // Services come from the login/session response, nested inside the subscription
  const items: SubscriptionServiceInfo[] = currentSubscription?.services || []

  const normalizeConfigCompleted = (value: boolean | string | undefined | null): boolean => {
    if (typeof value === 'boolean') return value
    if (typeof value === 'string') return value.toLowerCase() === 'true'
    return false
  }

  const handleServiceClick = (service: SubscriptionServiceInfo) => {
    const isConfigured = normalizeConfigCompleted(service.config_completed)
    setActiveServiceId(service.service_id)
    if (isConfigured) {
      router.push('/dashboard')
    } else {
      router.push('/setup')
    }
  }

  const handleOpenCreateDialog = () => {
    setNewServiceName('')
    setIsCreateDialogOpen(true)
  }

  const handleCreateNewService = async () => {
    if (!currentSubscription) return
    const trimmedName = newServiceName.trim()
    if (!trimmedName) {
      toast.error(t('services.serviceNameRequired'))
      return
    }
    setIsCreating(true)
    try {
      const response = await backendService.createNewService(currentSubscription.subscription_id, trimmedName)
      toast.success(t('services.createSuccess'))
      setIsCreateDialogOpen(false)
      setNewServiceName('')

      // Use the service returned from the API to update the UI immediately
      if (response.success && response.service) {
        addServiceToSubscription(response.service)
        // We do not set active service ID here anymore so it doesn't navigate
      }

    } catch (error) {
      console.error('Failed to create service:', error)
      toast.error(t('services.createError'))
    } finally {
      setIsCreating(false)
    }
  }

  if (authLoading || !isMounted) {
    return (
      <div className="flex min-h-svh w-full items-center justify-center p-6 md:p-10">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    )
  }

  return (
    <div className="min-h-svh w-full bg-background text-foreground overflow-y-auto">
      <ThemeLanguageSwitcher />
      <div className="flex min-h-svh w-full items-start justify-center p-6 md:p-10 py-12 md:py-16">
        <div className="w-full max-w-4xl space-y-8 flex flex-col items-center">
          {/* Header */}
          <div className="flex flex-col items-center gap-4 text-center">
            <Image src="/corretto-avatar.png" alt="Corretto" width={64} height={64} className="rounded-xl shadow-lg" priority />
            <div>
              <h1 className="text-2xl font-bold text-foreground">{t('services.title')}</h1>
              <p className="text-muted-foreground">{t('services.description')}</p>
              <p className="text-sm text-muted-foreground/70 mt-1">{currentSubscription?.name}</p>
            </div>
          </div>

          {/* Back to workspaces */}
          <div className="w-full flex justify-start">
            <Button variant="ghost" size="sm" onClick={() => router.push('/select-subscription')} className="text-muted-foreground hover:text-foreground gap-2">
              <ArrowLeft className="h-4 w-4" />{t('services.backToWorkspaces')}
            </Button>
          </div>

          {items.length === 0 ? (
            <Card className="w-full max-w-md bg-card shadow-sm border-border/50">
              <CardContent className="flex flex-col items-center justify-center py-12 text-center">
                <div className="rounded-full bg-muted p-4 mb-4">
                  <Mail className="h-8 w-8 text-muted-foreground" />
                </div>
                <h3 className="font-medium text-lg">{t('services.noServices')}</h3>
                <p className="text-sm text-muted-foreground mt-1 max-w-xs">{t('services.noServicesDescription')}</p>
                <Button className="mt-6 gap-2" onClick={handleOpenCreateDialog}>
                  <Plus className="h-4 w-4" />{t('services.addNew')}
                </Button>
              </CardContent>
            </Card>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 w-full">
              {items.map((service) => {
                const isConfigured = normalizeConfigCompleted(service.config_completed)
                return (
                  <Card
                    key={service.service_id}
                    className="cursor-pointer transition-all hover:border-primary border-border/50 bg-card shadow-sm flex flex-col group"
                    onClick={() => handleServiceClick(service)}
                  >
                    <CardHeader className="pb-3">
                      <div className="flex items-center justify-between">
                        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                          <Mail className="h-5 w-5 text-primary" />
                        </div>
                        {isConfigured ? (
                          <Badge variant="outline" className="text-green-600 border-green-600">
                            <CheckCircle2 className="h-3 w-3 mr-1" />{t('services.configured')}
                          </Badge>
                        ) : (
                          <Badge variant="outline" className="text-amber-600 border-amber-600">
                            <Settings className="h-3 w-3 mr-1" />{t('services.notConfigured')}
                          </Badge>
                        )}
                      </div>
                      <CardTitle className="mt-4 truncate" title={service.name}>{service.name}</CardTitle>
                      <CardDescription>
                        {service.email || 'No email'}
                      </CardDescription>
                    </CardHeader>
                    <CardContent className="flex-1" />
                    <CardFooter className="bg-muted/50 p-4 rounded-b-lg mt-auto">
                      <div className="flex w-full items-center justify-between text-sm text-primary">
                        <span className="font-medium">{isConfigured ? t('services.openDashboard') : t('services.completeSetup')}</span>
                        <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
                      </div>
                    </CardFooter>
                  </Card>
                )
              })}

              {/* Add New Service Card */}
              <Card
                className="cursor-pointer border-dashed hover:border-primary border-muted hover:bg-muted/50 transition-all flex flex-col items-center justify-center min-h-[200px] bg-transparent"
                onClick={handleOpenCreateDialog}
              >
                <CardContent className="flex flex-col items-center gap-4 p-6">
                  <div className="h-12 w-12 rounded-full bg-muted flex items-center justify-center">
                    <Plus className="h-6 w-6 text-muted-foreground" />
                  </div>
                  <span className="font-medium text-muted-foreground">{t('services.addNew')}</span>
                  <span className="text-xs text-muted-foreground/70">{t('services.addNewDescription')}</span>
                </CardContent>
              </Card>
            </div>
          )}
        </div>
      </div>

      {/* Create New Service Dialog */}
      <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>{t('services.createDialogTitle')}</DialogTitle>
            <DialogDescription>{t('services.createDialogDescription')}</DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="service-name">{t('services.serviceNameLabel')}</Label>
              <Input
                id="service-name"
                placeholder={t('services.serviceNamePlaceholder')}
                value={newServiceName}
                onChange={(e) => setNewServiceName(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter') handleCreateNewService() }}
                autoFocus
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsCreateDialogOpen(false)} disabled={isCreating}>
              {t('common.cancel')}
            </Button>
            <Button onClick={handleCreateNewService} disabled={isCreating || !newServiceName.trim()}>
              {isCreating ? (
                <><Loader2 className="h-4 w-4 animate-spin mr-2" />{t('services.creating')}</>
              ) : (
                t('services.create')
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>

  )
}
