'use client'

import { useState, useMemo, useRef, useEffect } from 'react'
import { EmailThreadSummary } from '@/lib/api/backend-service'
import { useLanguage } from '@/lib/context/language-context'
import { ThreadCard } from './thread-card'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Skeleton } from '@/components/ui/skeleton'
import { Input } from '@/components/ui/input'
import { Mail, Search, Loader2 } from 'lucide-react'

interface ThreadListProps {
    threads: EmailThreadSummary[]
    selectedThreadId?: string
    variant?: 'inbox' | 'review' | 'failed'
    isLoading?: boolean
    onSelectThread: (thread: EmailThreadSummary) => void
    onLoadMore?: () => void
    hasMore?: boolean
}

export function ThreadList({
    threads,
    selectedThreadId,
    variant = 'inbox',
    isLoading,
    onSelectThread,
    onLoadMore,
    hasMore = false
}: ThreadListProps) {
    const { t } = useLanguage()
    const [searchQuery, setSearchQuery] = useState('')
    const observerTarget = useRef<HTMLDivElement>(null)

    // Filter threads based on search query
    const filteredThreads = useMemo(() => {
        if (!searchQuery.trim()) return threads

        const query = searchQuery.toLowerCase()
        return threads.filter(thread =>
            thread.subject?.toLowerCase().includes(query) ||
            thread.last_sender_email?.toLowerCase().includes(query) ||
            thread.summary?.toLowerCase().includes(query) ||
            thread.category?.toLowerCase().includes(query) ||
            thread.subcategory?.toLowerCase().includes(query)
        )
    }, [threads, searchQuery])

    // Infinite scroll observer
    useEffect(() => {
        const observer = new IntersectionObserver(
            (entries) => {
                if (entries[0].isIntersecting && hasMore && !isLoading) {
                    onLoadMore?.()
                }
            },
            { threshold: 0.1 } // Trigger when 10% of the target is visible
        )

        if (observerTarget.current) {
            observer.observe(observerTarget.current)
        }

        return () => observer.disconnect()
    }, [hasMore, isLoading, onLoadMore])

    if (isLoading && threads.length === 0) {
        return (
            <div className="space-y-0">
                <div className="p-3 border-b">
                    <Skeleton className="h-9 w-full" />
                </div>
                {Array.from({ length: 5 }).map((_, i) => (
                    <div key={i} className="p-4 border-b">
                        <Skeleton className="h-4 w-3/4 mb-2" />
                        <Skeleton className="h-3 w-1/2 mb-2" />
                        <Skeleton className="h-3 w-full" />
                    </div>
                ))}
            </div>
        )
    }

    if (threads.length === 0) {
        return (
            <div className="flex flex-col items-center justify-center h-full py-12 px-4 text-center">
                <div className="rounded-full bg-muted p-4 mb-4">
                    <Mail className="h-8 w-8 text-muted-foreground" />
                </div>
                <h3 className="font-medium text-lg">{t('email.noThreads')}</h3>
                <p className="text-sm text-muted-foreground mt-1 max-w-xs">
                    {t('email.noThreadsDescription')}
                </p>
            </div>
        )
    }

    return (
        <div className="flex flex-col h-full">
            {/* Search bar */}
            <div className="p-3 border-b flex-shrink-0">
                <div className="relative">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                    <Input
                        type="text"
                        placeholder={t('email.searchPlaceholder') || 'Search emails...'}
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        className="pl-9 h-9"
                    />
                </div>
            </div>

            {/* Thread list */}
            <ScrollArea className="flex-1 min-h-0">
                {filteredThreads.length === 0 ? (
                    <div className="flex flex-col items-center justify-center py-12 px-4 text-center">
                        <div className="rounded-full bg-muted p-4 mb-4">
                            <Search className="h-8 w-8 text-muted-foreground" />
                        </div>
                        <h3 className="font-medium text-lg">{t('email.noResults') || 'No results found'}</h3>
                        <p className="text-sm text-muted-foreground mt-1 max-w-xs">
                            {t('email.noResultsDescription') || 'Try adjusting your search terms'}
                        </p>
                    </div>
                ) : (
                    <div className="divide-y relative">
                        {filteredThreads.map((thread) => (
                            <ThreadCard
                                key={thread.thread_id}
                                thread={thread}
                                variant={variant}
                                isSelected={selectedThreadId === thread.thread_id}
                                onClick={() => onSelectThread(thread)}
                            />
                        ))}

                        {/* Loading indicator / Sentinel for infinite scroll */}
                        {hasMore && (
                            <div ref={observerTarget} className="p-4 flex justify-center items-center">
                                <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                            </div>
                        )}
                    </div>
                )}
            </ScrollArea>
        </div>
    )
}
