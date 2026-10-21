'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { cn } from '@/lib/utils'
import { useLanguage } from '@/lib/context/language-context'
import {
  Mail,
  Bot,
  TrendingUp,
  Clock,
  AlertTriangle,
  LucideIcon
} from 'lucide-react'

interface KPICardProps {
  title: string
  value: string | number
  subtitle?: string
  icon: LucideIcon
  trend?: {
    value: number
    isPositive: boolean
  }
  variant?: 'default' | 'success' | 'warning' | 'danger'
}

const variantStyles = {
  default: 'text-primary',
  success: 'text-green-500',
  warning: 'text-yellow-500',
  danger: 'text-red-500',
}

export function KPICard({ title, value, subtitle, icon: Icon, trend, variant = 'default' }: KPICardProps) {
  return (
    <Card className="relative overflow-hidden py-4 gap-3">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-1 px-4">
        <CardTitle className="text-sm font-medium text-muted-foreground">
          {title}
        </CardTitle>
        <Icon className="h-4 w-4 text-emerald-500" />
      </CardHeader>
      <CardContent className="px-4">
        <div className="text-2xl font-bold">{value}</div>
        {subtitle && (
          <p className="text-xs text-muted-foreground mt-1">{subtitle}</p>
        )}
        {trend && (
          <div className={cn(
            'flex items-center text-xs mt-2',
            trend.isPositive ? 'text-emerald-500' : 'text-red-500'
          )}>
            <TrendingUp className={cn('h-3 w-3 mr-1', !trend.isPositive && 'rotate-180')} />
            {trend.value}%
          </div>
        )}
      </CardContent>
    </Card>
  )
}

interface OverviewKPIsProps {
  ticketTotal: number
  ticketAutomatizzati: number
  deflectionRate: number
  avgResponseTime: number
  alertAttivi: number
  isLoading?: boolean
}

export function OverviewKPIs({
  ticketTotal,
  ticketAutomatizzati,
  deflectionRate,
  avgResponseTime,
  alertAttivi,
  isLoading
}: OverviewKPIsProps) {
  const { t } = useLanguage()

  if (isLoading) {
    return (
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
        {[...Array(5)].map((_, i) => (
          <Card key={i} className="animate-pulse">
            <CardHeader className="pb-2">
              <div className="h-4 w-24 bg-muted rounded" />
            </CardHeader>
            <CardContent>
              <div className="h-8 w-16 bg-muted rounded" />
            </CardContent>
          </Card>
        ))}
      </div>
    )
  }

  const formatTime = (seconds: number) => {
    if (seconds < 60) return `${seconds.toFixed(1)}s`
    const minutes = Math.floor(seconds / 60)
    const remainingSeconds = seconds % 60
    return `${minutes}m ${remainingSeconds.toFixed(0)}s`
  }

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
      <KPICard
        title={t('kpi.totalTickets')}
        value={ticketTotal}
        subtitle={t('kpi.totalProcessed')}
        icon={Mail}
        variant="default"
      />
      <KPICard
        title={t('kpi.aiAutomated')}
        value={ticketAutomatizzati}
        subtitle={t('kpi.handledByAI')}
        icon={Bot}
        variant="success"
      />
      <KPICard
        title={t('kpi.deflectionRate')}
        value={`${deflectionRate.toFixed(1)}%`}
        subtitle={t('kpi.noHumanIntervention')}
        icon={TrendingUp}
        variant={deflectionRate > 70 ? 'success' : deflectionRate > 50 ? 'warning' : 'danger'}
      />
      <KPICard
        title={t('kpi.avgResponseTime')}
        value={formatTime(avgResponseTime)}
        subtitle={t('kpi.aiResponseTime')}
        icon={Clock}
        variant="default"
      />
      <KPICard
        title={t('kpi.activeAlerts')}
        value={alertAttivi}
        subtitle={t('kpi.highPriority')}
        icon={AlertTriangle}
        variant={alertAttivi > 0 ? 'danger' : 'success'}
      />
    </div>
  )
}
