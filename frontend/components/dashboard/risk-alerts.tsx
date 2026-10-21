'use client'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import { useLanguage } from '@/lib/context/language-context'
import type { TicketCritico } from '@/lib/api/backend-service'
import { AlertTriangle, Clock, ExternalLink, AlertCircle, CheckCircle2 } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface RiskAlertsProps {
  alertsCount: number
  highRiskCount: number
  ticketCritici: TicketCritico[]
  isLoading?: boolean
}

function getPriorityLabel(score: number, t: (key: string) => string): { label: string; isHigh: boolean; isCritical: boolean } {
  if (score >= 80) return { label: t('dashboard.risk.critical'), isHigh: false, isCritical: true }
  if (score >= 60) return { label: t('dashboard.risk.high'), isHigh: true, isCritical: false }
  if (score >= 40) return { label: t('dashboard.risk.medium'), isHigh: false, isCritical: false }
  return { label: t('dashboard.risk.low'), isHigh: false, isCritical: false }
}

export function RiskAlerts({ alertsCount, highRiskCount, ticketCritici, isLoading }: RiskAlertsProps) {
  const { t } = useLanguage()
  
  if (isLoading) {
    return (
      <Card className="col-span-full">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-amber-500" />
            {t('dashboard.risk.title')}
          </CardTitle>
          <CardDescription>{t('dashboard.risk.description')}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="animate-pulse h-24 bg-muted rounded-lg" />
          ))}
        </CardContent>
      </Card>
    )
  }

  const hasAlerts = alertsCount > 0 || highRiskCount > 0 || ticketCritici.length > 0

  return (
    <Card className="col-span-full">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <AlertTriangle className={`h-5 w-5 ${hasAlerts ? 'text-amber-500' : 'text-green-500'}`} />
            <div>
              <CardTitle>{t('dashboard.risk.title')}</CardTitle>
              <CardDescription>{t('dashboard.risk.description')}</CardDescription>
            </div>
          </div>
          <div className="flex gap-3">
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-amber-100 dark:bg-amber-900/30">
              <AlertCircle className="h-4 w-4 text-amber-600 dark:text-amber-400" />
              <span className="text-sm font-medium text-amber-700 dark:text-amber-300">
                {alertsCount} {t('dashboard.risk.alerts')}
              </span>
            </div>
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-red-100 dark:bg-red-900/30">
              <AlertTriangle className="h-4 w-4 text-red-600 dark:text-red-400" />
              <span className="text-sm font-medium text-red-700 dark:text-red-300">
                {highRiskCount} {t('dashboard.risk.highRisk')}
              </span>
            </div>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {ticketCritici.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <CheckCircle2 className="h-12 w-12 text-green-500 mb-4" />
            <h3 className="text-lg font-medium">{t('dashboard.risk.allClear')}</h3>
            <p className="text-sm text-muted-foreground mt-1">
              {t('dashboard.risk.noCriticalTickets')}
            </p>
          </div>
        ) : (
          <ScrollArea className="h-[350px] pr-4">
            <div className="space-y-4">
              {ticketCritici.map((ticket, index) => {
                const priority = getPriorityLabel(ticket.priority_score, t)
                return (
                  <div
                    key={index}
                    className={`p-4 rounded-lg border ${
                      priority.isCritical 
                        ? 'bg-red-50 dark:bg-red-500/20 border-red-200 dark:border-red-400'
                        : priority.isHigh
                        ? 'bg-amber-50 dark:bg-amber-500/20 border-amber-200 dark:border-amber-400'
                        : 'bg-muted/50 border-border'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-2">
                          <Badge 
                            variant={
                              priority.isCritical ? 'destructive' : 
                              priority.isHigh ? 'outline' : 'secondary'
                            }
                            className={
                              priority.isHigh 
                                ? 'border-amber-500 text-amber-700 dark:text-amber-400' 
                                : ''
                            }
                          >
                            {priority.label}
                          </Badge>
                          <span className="text-xs text-muted-foreground">
                            {t('dashboard.risk.score')}: {ticket.priority_score}
                          </span>
                        </div>
                        <p className="text-sm font-medium">
                          {t('dashboard.risk.thread')}: {ticket.thread_id.slice(0, 12)}...
                        </p>
                        <div className="flex items-center gap-2 mt-2 text-xs text-muted-foreground">
                          <Clock className="h-3 w-3" />
                          <span>{new Date(ticket.processed_at).toLocaleString()}</span>
                        </div>
                      </div>
                      <Button variant="ghost" size="sm" className="shrink-0">
                        <ExternalLink className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                )
              })}
            </div>
          </ScrollArea>
        )}
      </CardContent>
    </Card>
  )
}
