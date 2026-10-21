'use client'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { ChartWrapper } from './chart-wrapper'
import { CustomTooltip } from './custom-tooltip'
import { useLanguage } from '@/lib/context/language-context'
import {
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip
} from 'recharts'
import type { OutcomeDistribution, AvgScoreByOutcome } from '@/lib/api/backend-service'
import { CheckCircle2, XCircle } from 'lucide-react'

const OUTCOME_COLORS: Record<string, string> = {
  'SENT': 'var(--chart-2)',      // Green
  'DRAFT': 'var(--chart-1)',     // Blue
  'PENDING': 'var(--chart-3)',   // Amber
  'FAILED': 'var(--chart-5)',    // Red/Pink
  'REVIEW': 'var(--chart-4)',    // Purple
}

interface OutcomeDistributionChartProps {
  data: OutcomeDistribution[]
  isLoading?: boolean
}

export function OutcomeDistributionChart({ data, isLoading }: OutcomeDistributionChartProps) {
  const { t } = useLanguage()

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>{t('chart.outcomeDistribution')}</CardTitle>
          <CardDescription>{t('chart.aiResponseOutcomes')}</CardDescription>
        </CardHeader>
        <CardContent className="h-[300px] flex items-center justify-center">
          <div className="animate-pulse h-48 w-48 rounded-full bg-muted" />
        </CardContent>
      </Card>
    )
  }

  const chartData = data.map(item => ({
    name: item.outcome,
    value: item.count,
    fill: OUTCOME_COLORS[item.outcome] || 'hsl(var(--muted-foreground))'
  }))

  const total = chartData.reduce((sum, item) => sum + item.value, 0)

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t('chart.outcomeDistribution')}</CardTitle>
        <CardDescription>{t('chart.aiResponseOutcomes')}</CardDescription>
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
        <div className="flex flex-wrap justify-center gap-4 mt-4">
          {chartData.map((item, index) => (
            <div key={index} className="flex items-center gap-2">
              <div className="h-3 w-3 rounded-full" style={{ backgroundColor: item.fill }} />
              <span className="text-xs text-muted-foreground">{item.name}</span>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}

interface QualityKPIsProps {
  successRate: number
  negativeFeadbackPct: number
  isLoading?: boolean
}

export function QualityKPIs({ successRate, negativeFeadbackPct, isLoading }: QualityKPIsProps) {
  const { t } = useLanguage()

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>{t('chart.aiQualityMetrics')}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="animate-pulse h-16 bg-muted rounded" />
          <div className="animate-pulse h-16 bg-muted rounded" />
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t('chart.aiQualityMetrics')}</CardTitle>
        <CardDescription>{t('chart.keyQualityIndicators')}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="flex items-center justify-between p-4 rounded-lg bg-green-50 dark:bg-green-950/30 border border-green-200 dark:border-green-800">
          <div className="flex items-center gap-3">
            <CheckCircle2 className="h-8 w-8 text-green-500" />
            <div>
              <p className="text-sm font-medium">{t('chart.successRate')}</p>
              <p className="text-xs text-muted-foreground">{t('chart.successfulAIResponses')}</p>
            </div>
          </div>
          <span className="text-3xl font-bold text-green-600 dark:text-green-400">
            {successRate.toFixed(1)}%
          </span>
        </div>

        <div className={`flex items-center justify-between p-4 rounded-lg border ${negativeFeadbackPct > 10
            ? 'bg-red-50 dark:bg-red-950/30 border-red-200 dark:border-red-800'
            : 'bg-muted/50 border-border'
          }`}>
          <div className="flex items-center gap-3">
            <XCircle className={`h-8 w-8 ${negativeFeadbackPct > 10 ? 'text-red-500' : 'text-muted-foreground'}`} />
            <div>
              <p className="text-sm font-medium">{t('chart.negativeFeedback')}</p>
              <p className="text-xs text-muted-foreground">{t('chart.userDissatisfaction')}</p>
            </div>
          </div>
          <span className={`text-3xl font-bold ${negativeFeadbackPct > 10 ? 'text-red-600 dark:text-red-400' : 'text-foreground'
            }`}>
            {negativeFeadbackPct.toFixed(1)}%
          </span>
        </div>
      </CardContent>
    </Card>
  )
}

interface ScoreByOutcomeChartProps {
  data: AvgScoreByOutcome[]
  isLoading?: boolean
}

export function ScoreByOutcomeChart({ data, isLoading }: ScoreByOutcomeChartProps) {
  const { t } = useLanguage()

  if (isLoading || data.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>{t('chart.avgScoreByOutcome')}</CardTitle>
          <CardDescription>{t('chart.performanceScoresPerOutcome')}</CardDescription>
        </CardHeader>
        <CardContent className="h-[200px] flex items-center justify-center">
          {isLoading ? (
            <div className="animate-pulse h-full w-full bg-muted rounded" />
          ) : (
            <p className="text-muted-foreground text-sm">{t('chart.noDataAvailable')}</p>
          )}
        </CardContent>
      </Card>
    )
  }

  const chartData = data.map(item => ({
    outcome: item.outcome,
    score: item.avg_score * 100,
    fill: OUTCOME_COLORS[item.outcome] || 'hsl(var(--primary))'
  }))

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t('chart.avgScoreByOutcome')}</CardTitle>
        <CardDescription>{t('chart.performanceScoresPerOutcome')}</CardDescription>
      </CardHeader>
      <CardContent>
        <ChartWrapper height={200}>
          <BarChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-muted" vertical={false} />
            <XAxis
              dataKey="outcome"
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
              content={<CustomTooltip formatter={(value: number) => [`${value.toFixed(1)}%`, t('chart.score')]} />}
            />
            <Bar
              dataKey="score"
              radius={[4, 4, 0, 0]}
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
