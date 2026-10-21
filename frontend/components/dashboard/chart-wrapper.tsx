'use client'

import { ResponsiveContainer } from 'recharts'

interface ChartWrapperProps {
  children: React.ReactElement
  height?: number
}

export function ChartWrapper({ children, height = 300 }: ChartWrapperProps) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      {children}
    </ResponsiveContainer>
  )
}
