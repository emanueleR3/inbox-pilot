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
  Cell,
  PieChart,
  Pie
} from 'recharts'
import type { EventsPerType, EventsTrend } from '@/lib/api/backend-service'
import { Calendar, Users, Bot } from 'lucide-react'

interface AIvsHumanEventsChartProps {
  aiEvents: number
  humanEvents: number
  isLoading?: boolean
}

export function AIvsHumanEventsChart({ aiEvents, humanEvents, isLoading }: AIvsHumanEventsChartProps) {
  const { t } = useLanguage()

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>{t('chart.aiVsHumanCalendar')}</CardTitle>
          <CardDescription>{t('chart.eventCreatorsDistribution')}</CardDescription>
        </CardHeader>
        <CardContent className="h-[300px] flex items-center justify-center">
          <div className="animate-pulse h-48 w-48 rounded-full bg-muted" />
        </CardContent>
      </Card>
    )
  }

  const chartData = [
    { name: t('chart.aiCreated'), value: aiEvents, fill: 'var(--chart-2)' },
    { name: t('chart.humanCreated'), value: humanEvents, fill: 'var(--chart-1)' }
  ]

  const total = aiEvents + humanEvents

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Calendar className="h-5 w-5" />
          {t('chart.aiVsHumanCalendar')}
        </CardTitle>
        <CardDescription>{t('chart.eventCreatorsDistribution')}</CardDescription>
      </CardHeader>
      <CardContent>
        <ChartWrapper height={280}>
          <PieChart>
            <Pie
              data={chartData}
              cx="50%"
              cy="50%"
              innerRadius={60}
              outerRadius={100}
              paddingAngle={2}
              dataKey="value"
              label={({ percent }) => `${((percent || 0) * 100).toFixed(0)}%`}
            >
              {chartData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.fill} />
              ))}
            </Pie>
            <Tooltip
              content={<CustomTooltip formatter={(value: number) => [`${value} (${((value / total) * 100).toFixed(1)}%)`, t('chart.events')]} />}
            />
          </PieChart>
        </ChartWrapper>
        <div className="flex justify-center gap-6 mt-4">
          <div className="flex items-center gap-2">
            <Bot className="h-4 w-4 text-green-500" />
            <span className="text-sm">{t('chart.ai')}: {aiEvents}</span>
          </div>
          <div className="flex items-center gap-2">
            <Users className="h-4 w-4 text-blue-500" />
            <span className="text-sm">{t('chart.human')}: {humanEvents}</span>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

interface EventTrendChartProps {
  data: EventsTrend[]
  isLoading?: boolean
}

export function EventTrendChart({ data, isLoading }: EventTrendChartProps) {
  const { t } = useLanguage()

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>{t('chart.eventsTrend')}</CardTitle>
          <CardDescription>{t('chart.dailyEventCreation')}</CardDescription>
        </CardHeader>
        <CardContent className="h-[250px] flex items-center justify-center">
          <div className="animate-pulse h-full w-full bg-muted rounded" />
        </CardContent>
      </Card>
    )
  }

  const chartData = data.map(item => ({
    date: new Date(item.day).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
    events: item.count
  }))

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t('chart.eventsTrend')}</CardTitle>
        <CardDescription>{t('chart.dailyEventCreation')}</CardDescription>
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
            <Tooltip
              content={<CustomTooltip />}
            />
            <Line
              type="monotone"
              dataKey="events"
              stroke="var(--chart-4)"
              strokeWidth={2}
              dot={{ fill: 'var(--chart-4)', strokeWidth: 0, r: 3 }}
              activeDot={{ r: 5 }}
            />
          </LineChart>
        </ChartWrapper>
      </CardContent>
    </Card>
  )
}

interface EventByTypeChartProps {
  data: EventsPerType[]
  isLoading?: boolean
}

export function EventByTypeChart({ data, isLoading }: EventByTypeChartProps) {
  const { t } = useLanguage()

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>{t('chart.eventsByType')}</CardTitle>
          <CardDescription>{t('chart.distributionByCategory')}</CardDescription>
        </CardHeader>
        <CardContent className="h-[250px] flex items-center justify-center">
          <div className="animate-pulse h-full w-full bg-muted rounded" />
        </CardContent>
      </Card>
    )
  }

  const colors = [
    'var(--chart-4)',
    'var(--chart-2)',
    'var(--chart-1)',
    'var(--chart-3)',
    'var(--chart-5)',
  ]

  const chartData = data.map((item, index) => ({
    type: item.event_type,
    count: item.count,
    fill: colors[index % colors.length]
  }))

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t('chart.eventsByType')}</CardTitle>
        <CardDescription>{t('chart.distributionByCategory')}</CardDescription>
      </CardHeader>
      <CardContent>
        <ChartWrapper height={220}>
          <BarChart data={chartData} layout="vertical">
            <CartesianGrid strokeDasharray="3 3" className="stroke-muted" horizontal={false} />
            <XAxis type="number" tick={{ fontSize: 12 }} tickLine={false} axisLine={false} />
            <YAxis
              type="category"
              dataKey="type"
              tick={{ fontSize: 11 }}
              tickLine={false}
              axisLine={false}
              width={80}
            />
            <Tooltip
              content={<CustomTooltip />}
            />
            <Bar dataKey="count" radius={[0, 4, 4, 0]}>
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
