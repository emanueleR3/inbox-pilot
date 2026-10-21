'use client'

import { Card } from '@/components/ui/card'

interface TooltipPayload {
    name?: string
    dataKey?: string
    value?: number | string | Array<number | string>
    fill?: string
    color?: string
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    payload?: any
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    [key: string]: any
}

interface CustomTooltipProps {
    active?: boolean
    payload?: TooltipPayload[]
    label?: string
    formatter?: (value: number, name: string) => [string, string] | [string]
}

export function CustomTooltip({ active, payload, label, formatter }: CustomTooltipProps) {
    if (active && payload && payload.length) {
        return (
            <Card className="bg-popover text-popover-foreground border-border shadow-lg p-3 text-sm rounded-lg">
                {label && <p className="font-medium mb-2">{label}</p>}
                <div className="flex flex-col gap-1">
                    {payload.map((item: TooltipPayload, index: number) => {
                        const label = item.name || item.dataKey || ''
                        const value = formatter
                            ? formatter(item.value as number, label)
                            : item.value

                        return (
                            <div key={index} className="flex items-center gap-2">
                                <div
                                    className="w-2 h-2 rounded-full"
                                    style={{ backgroundColor: item.fill || item.color }}
                                />
                                <span className="text-muted-foreground">
                                    {Array.isArray(value) ? value[1] || label : label}:
                                </span>
                                <span className="font-medium">
                                    {Array.isArray(value) ? value[0] : value}
                                </span>
                            </div>
                        )
                    })}
                </div>
            </Card>
        )
    }

    return null
}
