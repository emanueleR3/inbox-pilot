'use client'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { ChartWrapper } from './chart-wrapper'
import { CustomTooltip } from './custom-tooltip'
import { useLanguage } from '@/lib/context/language-context'
import {
  PieChart,
  Pie,
  Cell,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  BarChart,
  Bar
} from 'recharts'
import type { AIvsHuman, DeflectionTrend, DeflectionByCategory } from '@/lib/api/backend-service'

const COLORS = {
  ai: 'var(--chart-2)',      // Green for AI
  human: 'var(--chart-1)',   // Blue for Human
  categories: [
    'var(--chart-2)',
    'var(--chart-1)',
    'var(--chart-4)',
    'var(--chart-3)',
    'var(--chart-5)',
    'var(--chart-4)',
  ]
}

interface AIvsHumanChartProps {
  data: AIvsHuman[]
  isLoading?: boolean
}

export function AIvsHumanChart({ data, isLoading }: AIvsHumanChartProps) {
  const { t, language } = useLanguage()

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>{t('chart.aiVsHuman')}</CardTitle>
          <CardDescription>{t('chart.ticketResolution')}</CardDescription>
        </CardHeader>
        <CardContent className="h-[300px] flex items-center justify-center">
          <div className="animate-pulse h-48 w-48 rounded-full bg-muted" />
        </CardContent>
      </Card>
    )
  }

  const aiLabel = language === 'it' ? 'AI' : 'AI'
  const humanLabel = language === 'it' ? 'Umano' : 'Human'

  const chartData = data.map(item => ({
    name: item.human_response ? humanLabel : aiLabel,
    value: item.count,
    fill: item.human_response ? COLORS.human : COLORS.ai
  }))

  const total = chartData.reduce((sum, item) => sum + item.value, 0)

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t('chart.aiVsHuman')}</CardTitle>
        <CardDescription>{t('chart.ticketResolution')}</CardDescription>
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
              label={({ name, percent }) => `${name} ${((percent || 0) * 100).toFixed(0)}%`}
            >
              {chartData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.fill} />
              ))}
            </Pie>
            <Tooltip
              content={<CustomTooltip formatter={(value: number) => [`${value} (${((value / total) * 100).toFixed(1)}%)`, t('chart.count')]} />}
            />
          </PieChart>
        </ChartWrapper>
        <div className="flex justify-center gap-6 mt-4">
          <div className="flex items-center gap-2">
            <div className="h-3 w-3 rounded-full" style={{ backgroundColor: COLORS.ai }} />
            <span className="text-sm text-muted-foreground">{t('chart.aiCreated')}</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="h-3 w-3 rounded-full" style={{ backgroundColor: COLORS.human }} />
            <span className="text-sm text-muted-foreground">{t('chart.humanCreated')}</span>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

interface DeflectionTrendChartProps {
  data: DeflectionTrend[]
  isLoading?: boolean
}

export function DeflectionTrendChart({ data, isLoading }: DeflectionTrendChartProps) {
  const { t, language } = useLanguage()

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>{t('chart.deflectionTrend')}</CardTitle>
          <CardDescription>{t('chart.dailyDeflectionRate')}</CardDescription>
        </CardHeader>
        <CardContent className="h-[300px] flex items-center justify-center">
          <div className="animate-pulse h-full w-full bg-muted rounded" />
        </CardContent>
      </Card>
    )
  }

  const chartData = data.map(item => ({
    day: new Date(item.day).toLocaleDateString(language === 'it' ? 'it-IT' : 'en-US', { month: 'short', day: 'numeric' }),
    deflection: item.deflection_pct
  }))

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t('chart.deflectionTrend')}</CardTitle>
        <CardDescription>{t('chart.dailyDeflectionRate')}</CardDescription>
      </CardHeader>
      <CardContent>
        <ChartWrapper height={280}>
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
            <XAxis
              dataKey="day"
              tick={{ fontSize: 12 }}
              tickLine={false}
              axisLine={false}
            />
            <YAxis
              tick={{ fontSize: 12 }}
              tickLine={false}
              axisLine={false}
              tickFormatter={(value) => `${value}%`}
              domain={[0, 100]}
            />
            <Tooltip
              content={<CustomTooltip formatter={(value: number) => [`${value.toFixed(1)}%`, t('kpi.deflectionRate')]} />}
            />
            <Line
              type="monotone"
              dataKey="deflection"
              stroke="var(--primary)"
              strokeWidth={2}
              dot={{ fill: 'var(--primary)', strokeWidth: 2 }}
              activeDot={{ r: 6 }}
            />
          </LineChart>
        </ChartWrapper>
      </CardContent>
    </Card>
  )
}

interface DeflectionByCategoryChartProps {
  data: DeflectionByCategory[]
  isLoading?: boolean
}

export function DeflectionByCategoryChart({ data, isLoading }: DeflectionByCategoryChartProps) {
  const { t } = useLanguage()

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>{t('chart.deflectionByCategory')}</CardTitle>
          <CardDescription>{t('chart.deflectionRatePerCategory')}</CardDescription>
        </CardHeader>
        <CardContent className="h-[300px] flex items-center justify-center">
          <div className="animate-pulse h-full w-full bg-muted rounded" />
        </CardContent>
      </Card>
    )
  }

  const chartData = data.map((item, index) => ({
    category: item.category.replace(/_/g, ' '),
    deflection: item.deflection_pct,
    fill: COLORS.categories[index % COLORS.categories.length]
  }))

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t('chart.deflectionByCategory')}</CardTitle>
        <CardDescription>{t('chart.deflectionRatePerCategory')}</CardDescription>
      </CardHeader>
      <CardContent>
        <ChartWrapper height={280}>
          <BarChart data={chartData} layout="vertical">
            <CartesianGrid strokeDasharray="3 3" className="stroke-muted" horizontal={true} vertical={false} />
            <XAxis
              type="number"
              tick={{ fontSize: 12 }}
              tickLine={false}
              axisLine={false}
              tickFormatter={(value) => `${value}%`}
              domain={[0, 100]}
            />
            <YAxis
              type="category"
              dataKey="category"
              tick={{ fontSize: 11 }}
              tickLine={false}
              axisLine={false}
              width={100}
            />
            <Tooltip
              content={<CustomTooltip formatter={(value: number) => [`${value.toFixed(1)}%`, t('kpi.deflectionRate')]} />}
            />
            <Bar
              dataKey="deflection"
              radius={[0, 4, 4, 0]}
            >
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
