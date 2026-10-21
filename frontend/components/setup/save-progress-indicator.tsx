'use client'

import { useState, useEffect, useCallback } from 'react'
import { backendService } from '@/lib/api/backend-service'
import { Loader2, CheckCircle2, XCircle, Save } from 'lucide-react'
import { cn } from '@/lib/utils'

interface SaveProgressIndicatorProps {
    sessionId: string
    email: string
    onComplete?: () => void
    onError?: (error: string) => void
}

export function SaveProgressIndicator({
    sessionId,
    email,
    onComplete,
    onError
}: SaveProgressIndicatorProps) {
    const [status, setStatus] = useState<'pending' | 'processing' | 'completed' | 'failed'>('pending')
    const [step, setStep] = useState<string>('Initializing...')
    const [progress, setProgress] = useState(0)
    const [error, setError] = useState<string | null>(null)
    const [isVisible, setIsVisible] = useState(true)

    const pollStatus = useCallback(async () => {
        try {
            const response = await backendService.getQuizSaveStatus(sessionId, email)

            // Map API response to component state
            const mappedStatus = response.is_completed ? 'completed'
                : response.is_failed ? 'failed'
                    : response.is_running ? 'processing'
                        : 'pending'

            setStatus(mappedStatus)
            if (response.phase) setStep(response.phase)

            // Calculate progress percentage
            if (response.total_steps > 0) {
                const progressPct = (response.actual_step / response.total_steps) * 100
                setProgress(progressPct)
            }

            if (response.error) setError(response.error)

            if (response.is_completed) {
                onComplete?.()
                // Hide after a delay
                setTimeout(() => setIsVisible(false), 3000)
            } else if (response.is_failed) {
                onError?.(response.error || 'Save failed')
                setTimeout(() => setIsVisible(false), 5000)
            }

            return mappedStatus
        } catch (err) {
            console.error('[SaveProgress] Poll error:', err)
            return 'processing' // Continue polling on error
        }
    }, [sessionId, email, onComplete, onError])

    useEffect(() => {
        let intervalId: NodeJS.Timeout | null = null

        const startPolling = async () => {
            // Initial poll
            const initialStatus = await pollStatus()

            // Continue polling if not complete/failed
            if (initialStatus !== 'completed' && initialStatus !== 'failed') {
                intervalId = setInterval(async () => {
                    const currentStatus = await pollStatus()
                    if (currentStatus === 'completed' || currentStatus === 'failed') {
                        if (intervalId) clearInterval(intervalId)
                    }
                }, 2000) // Poll every 2 seconds
            }
        }

        startPolling()

        return () => {
            if (intervalId) clearInterval(intervalId)
        }
    }, [pollStatus])

    if (!isVisible) return null

    return (
        <div className="fixed top-4 left-4 z-50 animate-in slide-in-from-left-4 fade-in duration-300">
            <div className={cn(
                "flex items-center gap-3 px-4 py-3 rounded-xl shadow-lg border backdrop-blur-sm",
                "bg-background/95",
                status === 'completed' && "border-green-500/50",
                status === 'failed' && "border-red-500/50",
                (status === 'pending' || status === 'processing') && "border-primary/30"
            )}>
                {/* Icon */}
                <div className="shrink-0">
                    {status === 'completed' ? (
                        <CheckCircle2 className="w-5 h-5 text-green-500" />
                    ) : status === 'failed' ? (
                        <XCircle className="w-5 h-5 text-red-500" />
                    ) : (
                        <div className="relative">
                            <Save className="w-5 h-5 text-primary/30" />
                            <Loader2 className="w-5 h-5 text-primary absolute inset-0 animate-spin" />
                        </div>
                    )}
                </div>

                {/* Content */}
                <div className="min-w-[180px]">
                    <div className="flex items-center justify-between mb-1">
                        <span className="text-sm font-medium">
                            {status === 'completed' ? 'Saved!' :
                                status === 'failed' ? 'Save Failed' :
                                    'Saving profile...'}
                        </span>
                        {progress > 0 && status !== 'completed' && status !== 'failed' && (
                            <span className="text-xs text-muted-foreground">{Math.round(progress)}%</span>
                        )}
                    </div>

                    {/* Progress bar */}
                    {(status === 'pending' || status === 'processing') && (
                        <div className="h-1.5 bg-muted rounded-full overflow-hidden">
                            <div
                                className="h-full bg-primary transition-all duration-500 ease-out"
                                style={{ width: `${progress || 10}%` }}
                            />
                        </div>
                    )}

                    {/* Step label */}
                    {step && status !== 'completed' && status !== 'failed' && (
                        <p className="text-xs text-muted-foreground mt-1 truncate">{step}</p>
                    )}

                    {/* Error message */}
                    {error && status === 'failed' && (
                        <p className="text-xs text-red-500 mt-1 truncate">{error}</p>
                    )}
                </div>
            </div>
        </div>
    )
}
