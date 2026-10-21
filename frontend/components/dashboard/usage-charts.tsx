'use client'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { ChartWrapper } from './chart-wrapper'
import { CustomTooltip } from './custom-tooltip'
import { useLanguage } from '@/lib/context/language-context'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  LineChart,
  Line,
  Cell
} from 'recharts'
import type { EmailPerDay, ThreadsPerCategory } from '@/lib/api/backend-service'
import { Mail, MessageSquare } from 'lucide-react'

interface EmailPerDayChartProps {
  data: EmailPerDay[]
  isLoading?: boolean
}

export function EmailPerDayChart({ data, isLoading }: EmailPerDayChartProps) {
  const { t } = useLanguage()

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Mail className="h-5 w-5" />
            {t('chart.emailsPerDay')}
          </CardTitle>
          <CardDescription>{t('chart.dailyEmailVolume')}</CardDescription>
        </CardHeader>
        <CardContent className="h-[250px] flex items-center justify-center">
          <div className="animate-pulse h-full w-full bg-muted rounded" />
        </CardContent>
      </Card>
    )
  }

  const chartData = data.map(item => ({
    date: new Date(item.day).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
    emails: item.count
  }))

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Mail className="h-5 w-5" />
          {t('chart.emailsPerDay')}
        </CardTitle>
        <CardDescription>{t('chart.dailyEmailVolume')}</CardDescription>
      </CardHeader>
      <CardContent>
        <ChartWrapper height={220}>
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-muted" vertical={false} />
            <XAxis
              dataKey="date"
              tick={{ fontSize: 11 }}
              tickLine={false}
              axisLine={false}
            />
            <YAxis
              tick={{ fontSize: 12 }}
              tickLine={false}
              axisLine={false}
            />
            <Tooltip content={<CustomTooltip />} />
            <Line
              type="monotone"
              dataKey="emails"
              stroke="var(--chart-1)"
              strokeWidth={2}
              dot={{ fill: 'var(--chart-1)', strokeWidth: 0, r: 3 }}
              activeDot={{ r: 5 }}
            />
          </LineChart>
        </ChartWrapper>
      </CardContent>
    </Card>
  )
}

interface ThreadsByCategoryChartProps {
  data: ThreadsPerCategory[]
  isLoading?: boolean
}

export function ThreadsByCategoryChart({ data, isLoading }: ThreadsByCategoryChartProps) {
  const { t } = useLanguage()

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <MessageSquare className="h-5 w-5" />
            {t('chart.threadsByCategory')}
          </CardTitle>
          <CardDescription>{t('chart.emailThreadsDistribution')}</CardDescription>
        </CardHeader>
        <CardContent className="h-[250px] flex items-center justify-center">
          <div className="animate-pulse h-full w-full bg-muted rounded" />
        </CardContent>
      </Card>
    )
  }

  const colors = [
    'var(--chart-1)',
    'var(--chart-2)',
    'var(--chart-3)',
    'var(--chart-4)',
    'var(--chart-5)',
  ]

  const chartData = data.map((item, index) => ({
    category: item.category.length > 15 ? item.category.slice(0, 15) + '...' : item.category,
    fullCategory: item.category,
    threads: item.count,
    fill: colors[index % colors.length]
  }))

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <MessageSquare className="h-5 w-5" />
          {t('chart.threadsByCategory')}
        </CardTitle>
        <CardDescription>{t('chart.emailThreadsDistribution')}</CardDescription>
      </CardHeader>
      <CardContent>
        <ChartWrapper height={220}>
          <BarChart data={chartData} layout="vertical">
            <CartesianGrid strokeDasharray="3 3" className="stroke-muted" horizontal={false} />
            <XAxis type="number" tick={{ fontSize: 12 }} tickLine={false} axisLine={false} />
            <YAxis
              type="category"
              dataKey="category"
              tick={{ fontSize: 11 }}
              tickLine={false}
              axisLine={false}
              width={100}
            />
            <Tooltip
              content={<CustomTooltip formatter={(value: number) => [value.toString(), t('chart.threads')]} />}
            />
            <Bar dataKey="threads" radius={[0, 4, 4, 0]}>
              {chartData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.fill} />
              ))}
            </Bar>
          </BarChart>
        </ChartWrapper>
      </CardContent>
    </Card>
  )
}
