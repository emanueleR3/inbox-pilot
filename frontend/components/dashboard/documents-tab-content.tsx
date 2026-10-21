"use client"

import { useEffect, useState, useCallback, useMemo } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth, useSubscriptionConfig } from '@/lib/context/auth-context'
import { useLanguage } from '@/lib/context/language-context'
import { Skeleton } from '@/components/ui/skeleton'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import {
    AlertCircle,
    RefreshCw,
    FileText,
    Search,
    LayoutGrid,
    LayoutList,
    ChevronLeft,
    ChevronRight,
    ArrowUpDown,
    ArrowLeft,
    FileImage,
    FileSpreadsheet,
    FileArchive,
    File,
    HardDrive,
    Files,
    FolderOpen,
    Building2,
} from 'lucide-react'
import {
    backendService,
    type Attachment,
    type ReceiverGroup,
    type SubscriptionService,
} from '@/lib/api/backend-service'
import { AttachmentCard, formatFileSize } from '@/components/documents/attachment-card'
import { AttachmentDetail } from '@/components/documents/attachment-detail'
import { ReceiverGroupCard } from '@/components/documents/receiver-group-card'

type ViewMode = 'list' | 'grid'
type SortBy = 'date' | 'name' | 'size'
type FileFilter = 'all' | 'images' | 'pdfs' | 'spreadsheets' | 'text' | 'archives' | 'other'
type BrowseMode = 'companies' | 'company-detail' | 'all-files'

const ITEMS_PER_PAGE = 20

const FILTER_MIME_MAP: Record<FileFilter, (mime: string) => boolean> = {
    all: () => true,
    images: (m) => m.startsWith('image/'),
    pdfs: (m) => m === 'application/pdf',
    spreadsheets: (m) => m.includes('spreadsheet') || m.includes('excel') || m === 'text/csv',
    text: (m) => m.includes('word') || m.includes('document') || m === 'text/plain',
    archives: (m) => m.includes('zip') || m.includes('rar') || m.includes('tar') || m.includes('gzip'),
    other: (m) => {
        return !m.startsWith('image/') &&
            m !== 'application/pdf' &&
            !m.includes('spreadsheet') && !m.includes('excel') && m !== 'text/csv' &&
            !m.includes('word') && !m.includes('document') && m !== 'text/plain' &&
            !m.includes('zip') && !m.includes('rar') && !m.includes('tar') && !m.includes('gzip')
    }
}

const FILTER_ICONS: Record<FileFilter, typeof File> = {
    all: Files,
    images: FileImage,
    pdfs: FileText,
    spreadsheets: FileSpreadsheet,
    text: FileText,
    archives: FileArchive,
    other: File,
}

export function DocumentsTabContent() {
    const router = useRouter()
    const { isLoading: authLoading, isAuthenticated, currentSubscription, activeServiceId } = useAuth()
    const { isConfigured } = useSubscriptionConfig()
    const { t } = useLanguage()

    const [isReady, setIsReady] = useState(false)
    const [isRefreshing, setIsRefreshing] = useState(false)
    const [attachmentsLoading, setAttachmentsLoading] = useState(true)
    const [receiverGroups, setReceiverGroups] = useState<ReceiverGroup[]>([])
    const [totalCount, setTotalCount] = useState(0)
    const [totalReceivers, setTotalReceivers] = useState(0)
    const [error, setError] = useState<string | null>(null)
    const [serviceId, setServiceId] = useState<string | null>(null)

    // Browse state
    const [browseMode, setBrowseMode] = useState<BrowseMode>('companies')
    const [selectedCompany, setSelectedCompany] = useState<string | null>(null)

    // UI state
    const [searchQuery, setSearchQuery] = useState('')
    const [viewMode, setViewMode] = useState<ViewMode>('list')
    const [sortBy, setSortBy] = useState<SortBy>('date')
    const [fileFilter, setFileFilter] = useState<FileFilter>('all')
    const [currentPage, setCurrentPage] = useState(1)
    const [selectedAttachment, setSelectedAttachment] = useState<Attachment | null>(null)

    // Derive flat attachment list from receiver groups (filtered by selected company if applicable)
    const attachments = useMemo(() => {
        if (browseMode === 'company-detail' && selectedCompany) {
            const group = receiverGroups.find(g => g.receiver === selectedCompany)
            return group?.attachments || []
        }
        return receiverGroups.flatMap(g => g.attachments || [])
    }, [receiverGroups, browseMode, selectedCompany])

    // Auth checks
    useEffect(() => {
        if (!authLoading && !isAuthenticated) router.push('/login')
    }, [authLoading, isAuthenticated, router])

    useEffect(() => {
        if (!authLoading && isAuthenticated && !isConfigured) router.push('/setup')
    }, [authLoading, isAuthenticated, isConfigured, router])

    useEffect(() => {
        if (!authLoading && isAuthenticated && isConfigured) {
            const timer = setTimeout(() => setIsReady(true), 100)
            return () => clearTimeout(timer)
        }
    }, [authLoading, isAuthenticated, isConfigured])

    // Fetch service ID
    useEffect(() => {
        const fetchServiceInfo = async () => {
            if (!currentSubscription?.subscription_id) return
            try {
                const services = await backendService.getSubscriptionService(currentSubscription.subscription_id)
                if (services && services.length > 0) {
                    const service = (activeServiceId
                        ? services.find(s => s.service_id === activeServiceId)
                        : null) || services[0] as SubscriptionService
                    setServiceId(service.service_id)
                }
            } catch (err) {
                console.error('Error fetching subscription service:', err)
            }
        }
        if (isReady) fetchServiceInfo()
    }, [isReady, currentSubscription?.subscription_id])

    // Fetch attachments (grouped by receiver)
    const fetchAttachments = useCallback(async () => {
        if (!serviceId) return
        setAttachmentsLoading(true)
        setError(null)
        try {
            const response = await backendService.getAttachments(serviceId, 200, 0)
            setReceiverGroups(response.grouped_by_receiver || [])
            setTotalCount(response.total_attachments || 0)
            setTotalReceivers(response.total_receivers || 0)
        } catch (err) {
            console.error('Error fetching attachments:', err)
            setError(t('documents.errorLoading'))
            setReceiverGroups([])
        } finally {
            setAttachmentsLoading(false)
        }
    }, [serviceId, t])

    useEffect(() => {
        if (serviceId) fetchAttachments()
    }, [serviceId, fetchAttachments])

    const handleRefresh = async () => {
        setIsRefreshing(true)
        await fetchAttachments()
        setIsRefreshing(false)
    }

    // Company navigation
    const handleSelectCompany = (receiver: string) => {
        setSelectedCompany(receiver)
        setBrowseMode('company-detail')
        setSearchQuery('')
        setFileFilter('all')
        setCurrentPage(1)
        setSelectedAttachment(null)
    }

    const handleBackToCompanies = () => {
        setBrowseMode('companies')
        setSelectedCompany(null)
        setSearchQuery('')
        setFileFilter('all')
        setCurrentPage(1)
        setSelectedAttachment(null)
    }

    const handleShowAllFiles = () => {
        setBrowseMode('all-files')
        setSelectedCompany(null)
        setSearchQuery('')
        setFileFilter('all')
        setCurrentPage(1)
        setSelectedAttachment(null)
    }

    // Filtered companies for the companies view
    const processedCompanies = useMemo(() => {
        let groups = [...receiverGroups]

        if (searchQuery.trim()) {
            const query = searchQuery.toLowerCase()
            groups = groups.filter(g =>
                g.receiver.toLowerCase().includes(query)
            )
        }

        // Sort by attachment count descending
        groups.sort((a, b) => b.count - a.count)

        return groups
    }, [receiverGroups, searchQuery])

    // Filtered, searched, sorted attachments (for file views)
    const processedAttachments = useMemo(() => {
        let result = [...attachments]

        // Filter by type
        if (fileFilter !== 'all') {
            result = result.filter(a => FILTER_MIME_MAP[fileFilter](a.mime_type))
        }

        // Search
        if (searchQuery.trim()) {
            const query = searchQuery.toLowerCase()
            result = result.filter(a =>
                a.file_name.toLowerCase().includes(query) ||
                a.sender.toLowerCase().includes(query) ||
                a.receiver.toLowerCase().includes(query) ||
                a.mime_type.toLowerCase().includes(query)
            )
        }

        // Sort
        result.sort((a, b) => {
            switch (sortBy) {
                case 'name':
                    return a.file_name.localeCompare(b.file_name)
                case 'size':
                    return b.size_bytes - a.size_bytes
                case 'date':
                default:
                    return new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
            }
        })

        return result
    }, [attachments, fileFilter, searchQuery, sortBy])

    // Pagination
    const totalPages = browseMode === 'companies'
        ? Math.ceil(processedCompanies.length / ITEMS_PER_PAGE)
        : Math.ceil(processedAttachments.length / ITEMS_PER_PAGE)
    const startIndex = (currentPage - 1) * ITEMS_PER_PAGE
    const paginatedAttachments = processedAttachments.slice(startIndex, startIndex + ITEMS_PER_PAGE)
    const paginatedCompanies = processedCompanies.slice(startIndex, startIndex + ITEMS_PER_PAGE)
    const currentListLength = browseMode === 'companies' ? processedCompanies.length : processedAttachments.length

    // Reset page when filters change
    useEffect(() => {
        setCurrentPage(1)
    }, [searchQuery, fileFilter, sortBy, browseMode])

    // Stats (use all attachments across all groups for global stats)
    const allAttachments = useMemo(() =>
        receiverGroups.flatMap(g => g.attachments || [])
    , [receiverGroups])

    const stats = useMemo(() => {
        const totalSize = allAttachments.reduce((sum, a) => sum + a.size_bytes, 0)
        const uniqueTypes = new Set(allAttachments.map(a => {
            const ext = a.file_name.split('.').pop()?.toUpperCase()
            return ext || 'OTHER'
        }))
        return { totalSize, uniqueTypes: uniqueTypes.size }
    }, [allAttachments])

    // Filter counts (based on current view's attachments)
    const filterCounts = useMemo(() => {
        const counts: Record<FileFilter, number> = {
            all: attachments.length,
            images: 0, pdfs: 0, spreadsheets: 0, text: 0, archives: 0, other: 0
        }
        attachments.forEach(a => {
            for (const key of Object.keys(FILTER_MIME_MAP) as FileFilter[]) {
                if (key !== 'all' && FILTER_MIME_MAP[key](a.mime_type)) {
                    counts[key]++
                    break
                }
            }
        })
        return counts
    }, [attachments])

    const handlePreview = async (attachment: Attachment) => {
        setSelectedAttachment(attachment)
        try {
            // Only preview images and PDFs directly
            if (attachment.mime_type.startsWith('image/') || attachment.mime_type === 'application/pdf') {
                const blob = await backendService.getAttachmentPreview(attachment.attachment_id)
                const url = window.URL.createObjectURL(blob)
                window.open(url, '_blank')
                // Clean up URL after a delay to allow the new tab to load
                setTimeout(() => window.URL.revokeObjectURL(url), 1000)
            } else {
                // For other types, fallback to download
                handleDownload(attachment)
            }
        } catch (err) {
            console.error('Error previewing attachment:', err)
            // Ideally show a toast here
        }
    }

    const handleDownload = async (attachment: Attachment) => {
        try {
            const blob = await backendService.downloadAttachment(attachment.attachment_id)
            const url = window.URL.createObjectURL(blob)
            const link = document.createElement('a')
            link.href = url
            link.download = attachment.file_name
            document.body.appendChild(link)
            link.click()
            document.body.removeChild(link)
            window.URL.revokeObjectURL(url)
        } catch (err) {
            console.error('Error downloading attachment:', err)
            // Ideally show a toast here
        }
    }

    const cycleSortBy = () => {
        const order: SortBy[] = ['date', 'name', 'size']
        const nextIndex = (order.indexOf(sortBy) + 1) % order.length
        setSortBy(order[nextIndex])
    }

    const getSortLabel = () => {
        switch (sortBy) {
            case 'name': return t('documents.sortByName')
            case 'size': return t('documents.sortBySize')
            default: return t('documents.sortByDate')
        }
    }

    if (authLoading || !isReady) {
        return (
            <div className="flex items-center justify-center p-8 h-full">
                <div className="space-y-4 w-full max-w-md">
                    <Skeleton className="h-8 w-48" />
                    <Skeleton className="h-4 w-32" />
                    <div className="space-y-2 mt-8">
                        <Skeleton className="h-24 w-full" />
                        <Skeleton className="h-64 w-full" />
                    </div>
                </div>
            </div>
        )
    }

    return (
        <div className="flex flex-col gap-4 h-full animate-in fade-in duration-300">
            {/* Header */}
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                <div>
                    <h2 className="text-xl font-semibold tracking-tight">{t('documents.title')}</h2>
                    <p className="text-muted-foreground text-sm">{t('documents.subtitle')}</p>
                </div>
                <Button
                    variant="outline"
                    size="sm"
                    onClick={handleRefresh}
                    disabled={isRefreshing}
                >
                    <RefreshCw className={`h-4 w-4 mr-2 ${isRefreshing ? 'animate-spin' : ''}`} />
                    {t('documents.refresh')}
                </Button>
            </div>

            {/* Error Alert */}
            {error && (
                <Alert variant="destructive">
                    <AlertCircle className="h-4 w-4" />
                    <AlertTitle>{t('common.error')}</AlertTitle>
                    <AlertDescription>{error}</AlertDescription>
                </Alert>
            )}

            {/* Stats Row */}
            {!attachmentsLoading && allAttachments.length > 0 && (
                <div className="grid grid-cols-4 gap-3">
                    <div className="flex items-center gap-2 rounded-lg border bg-muted/20 px-3 py-2">
                        <Files className="h-4 w-4 text-blue-500" />
                        <div>
                            <p className="text-lg font-bold leading-none">{totalCount}</p>
                            <p className="text-[10px] text-muted-foreground">{t('documents.totalFiles')}</p>
                        </div>
                    </div>
                    <div className="flex items-center gap-2 rounded-lg border bg-muted/20 px-3 py-2">
                        <Building2 className="h-4 w-4 text-indigo-500" />
                        <div>
                            <p className="text-lg font-bold leading-none">{totalReceivers}</p>
                            <p className="text-[10px] text-muted-foreground">{t('documents.totalCompanies')}</p>
                        </div>
                    </div>
                    <div className="flex items-center gap-2 rounded-lg border bg-muted/20 px-3 py-2">
                        <HardDrive className="h-4 w-4 text-green-500" />
                        <div>
                            <p className="text-lg font-bold leading-none">{formatFileSize(stats.totalSize)}</p>
                            <p className="text-[10px] text-muted-foreground">{t('documents.totalSize')}</p>
                        </div>
                    </div>
                    <div className="flex items-center gap-2 rounded-lg border bg-muted/20 px-3 py-2">
                        <FolderOpen className="h-4 w-4 text-purple-500" />
                        <div>
                            <p className="text-lg font-bold leading-none">{stats.uniqueTypes}</p>
                            <p className="text-[10px] text-muted-foreground">{t('documents.fileTypes')}</p>
                        </div>
                    </div>
                </div>
            )}

            {/* Main Content */}
            <div className={`grid gap-4 h-[600px] ${selectedAttachment ? 'grid-cols-1 lg:grid-cols-2' : 'grid-cols-1'}`}>
                {/* File List */}
                <Card className="overflow-hidden flex flex-col h-full min-h-0">
                    {/* Toolbar */}
                    <div className="p-3 border-b space-y-2 shrink-0">
                        {/* Back button + Mode toggle + Search */}
                        <div className="flex gap-2 items-center">
                            {browseMode !== 'companies' && (
                                <Button
                                    variant="ghost"
                                    size="icon"
                                    className="h-9 w-9 shrink-0"
                                    onClick={handleBackToCompanies}
                                    title={t('documents.backToCompanies')}
                                >
                                    <ArrowLeft className="h-4 w-4" />
                                </Button>
                            )}
                            <div className="relative flex-1">
                                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                                <Input
                                    type="text"
                                    placeholder={browseMode === 'companies'
                                        ? (t('documents.searchPlaceholder'))
                                        : t('documents.searchPlaceholder')
                                    }
                                    value={searchQuery}
                                    onChange={(e) => setSearchQuery(e.target.value)}
                                    className="pl-9 h-9"
                                />
                            </div>
                            {browseMode !== 'companies' && (
                                <>
                                    <Button
                                        variant="outline"
                                        size="icon"
                                        className="h-9 w-9 shrink-0"
                                        onClick={cycleSortBy}
                                        title={getSortLabel()}
                                    >
                                        <ArrowUpDown className="h-4 w-4" />
                                    </Button>
                                    <Button
                                        variant={viewMode === 'list' ? 'default' : 'outline'}
                                        size="icon"
                                        className="h-9 w-9 shrink-0"
                                        onClick={() => setViewMode('list')}
                                    >
                                        <LayoutList className="h-4 w-4" />
                                    </Button>
                                    <Button
                                        variant={viewMode === 'grid' ? 'default' : 'outline'}
                                        size="icon"
                                        className="h-9 w-9 shrink-0"
                                        onClick={() => setViewMode('grid')}
                                    >
                                        <LayoutGrid className="h-4 w-4" />
                                    </Button>
                                </>
                            )}
                        </div>

                        {/* View mode tabs (companies vs all files) + file filters */}
                        {browseMode === 'companies' ? (
                            <div className="flex gap-1.5 overflow-x-auto pb-0.5">
                                <Button
                                    variant="default"
                                    size="sm"
                                    className="h-7 text-xs gap-1 shrink-0"
                                >
                                    <Building2 className="h-3 w-3" />
                                    {t('documents.companies')}
                                    <Badge variant="secondary" className="ml-0.5 h-4 px-1 text-[10px]">
                                        {receiverGroups.length}
                                    </Badge>
                                </Button>
                                <Button
                                    variant="outline"
                                    size="sm"
                                    className="h-7 text-xs gap-1 shrink-0"
                                    onClick={handleShowAllFiles}
                                >
                                    <Files className="h-3 w-3" />
                                    {t('documents.allFiles')}
                                    <Badge variant="secondary" className="ml-0.5 h-4 px-1 text-[10px]">
                                        {totalCount}
                                    </Badge>
                                </Button>
                            </div>
                        ) : (
                            <div className="flex gap-1.5 overflow-x-auto pb-0.5">
                                <Button
                                    variant="outline"
                                    size="sm"
                                    className="h-7 text-xs gap-1 shrink-0"
                                    onClick={handleBackToCompanies}
                                >
                                    <Building2 className="h-3 w-3" />
                                    {t('documents.companies')}
                                </Button>
                                {browseMode === 'all-files' && (
                                    <Button
                                        variant="default"
                                        size="sm"
                                        className="h-7 text-xs gap-1 shrink-0"
                                    >
                                        <Files className="h-3 w-3" />
                                        {t('documents.allFiles')}
                                        <Badge variant="secondary" className="ml-0.5 h-4 px-1 text-[10px]">
                                            {totalCount}
                                        </Badge>
                                    </Button>
                                )}
                                {browseMode === 'company-detail' && selectedCompany && (
                                    <Button
                                        variant="default"
                                        size="sm"
                                        className="h-7 text-xs gap-1 shrink-0"
                                    >
                                        <Building2 className="h-3 w-3" />
                                        {selectedCompany}
                                        <Badge variant="secondary" className="ml-0.5 h-4 px-1 text-[10px]">
                                            {attachments.length}
                                        </Badge>
                                    </Button>
                                )}
                                {/* File type sub-filters */}
                                <div className="w-px bg-border shrink-0 mx-0.5" />
                                {(Object.keys(FILTER_MIME_MAP) as FileFilter[]).map((filter) => {
                                    const FilterIcon = FILTER_ICONS[filter]
                                    const count = filterCounts[filter]
                                    const filterLabel = t(`documents.${filter === 'all' ? 'allTypes' : filter === 'text' ? 'textDocs' : filter}`)
                                    return (
                                        <Button
                                            key={filter}
                                            variant={fileFilter === filter ? 'default' : 'outline'}
                                            size="sm"
                                            className="h-7 text-xs gap-1 shrink-0"
                                            onClick={() => setFileFilter(filter)}
                                        >
                                            <FilterIcon className="h-3 w-3" />
                                            {filterLabel}
                                            {count > 0 && (
                                                <Badge
                                                    variant="secondary"
                                                    className="ml-0.5 h-4 px-1 text-[10px]"
                                                >
                                                    {count}
                                                </Badge>
                                            )}
                                        </Button>
                                    )
                                })}
                            </div>
                        )}
                    </div>

                    {/* Content */}
                    <ScrollArea className="flex-1 min-h-0">
                        {attachmentsLoading ? (
                            <div className="space-y-0">
                                {Array.from({ length: 5 }).map((_, i) => (
                                    <div key={i} className="p-4 border-b">
                                        <div className="flex items-center gap-4">
                                            <Skeleton className="h-10 w-10 rounded-lg" />
                                            <div className="flex-1 space-y-2">
                                                <Skeleton className="h-4 w-3/4" />
                                                <Skeleton className="h-3 w-1/2" />
                                            </div>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        ) : browseMode === 'companies' ? (
                            /* Companies list */
                            processedCompanies.length === 0 ? (
                                <div className="flex flex-col items-center justify-center h-full py-12 px-4 text-center">
                                    <div className="rounded-full bg-muted p-4 mb-4">
                                        {searchQuery ? (
                                            <Search className="h-8 w-8 text-muted-foreground" />
                                        ) : (
                                            <Building2 className="h-8 w-8 text-muted-foreground" />
                                        )}
                                    </div>
                                    <h3 className="font-medium text-lg">
                                        {searchQuery
                                            ? t('documents.noResults')
                                            : t('documents.noDocuments')
                                        }
                                    </h3>
                                    <p className="text-sm text-muted-foreground mt-1 max-w-xs">
                                        {searchQuery
                                            ? t('documents.noResultsDescription')
                                            : t('documents.noDocumentsDescription')
                                        }
                                    </p>
                                </div>
                            ) : (
                                <div className="divide-y">
                                    {paginatedCompanies.map((group) => (
                                        <ReceiverGroupCard
                                            key={group.receiver}
                                            group={group}
                                            onClick={() => handleSelectCompany(group.receiver)}
                                        />
                                    ))}
                                </div>
                            )
                        ) : (
                            /* File list (all-files or company-detail) */
                            processedAttachments.length === 0 ? (
                                <div className="flex flex-col items-center justify-center h-full py-12 px-4 text-center">
                                    <div className="rounded-full bg-muted p-4 mb-4">
                                        {searchQuery || fileFilter !== 'all' ? (
                                            <Search className="h-8 w-8 text-muted-foreground" />
                                        ) : (
                                            <FileText className="h-8 w-8 text-muted-foreground" />
                                        )}
                                    </div>
                                    <h3 className="font-medium text-lg">
                                        {searchQuery || fileFilter !== 'all'
                                            ? t('documents.noResults')
                                            : t('documents.noDocuments')
                                        }
                                    </h3>
                                    <p className="text-sm text-muted-foreground mt-1 max-w-xs">
                                        {searchQuery || fileFilter !== 'all'
                                            ? t('documents.noResultsDescription')
                                            : t('documents.noDocumentsDescription')
                                        }
                                    </p>
                                </div>
                            ) : viewMode === 'grid' ? (
                                <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 p-3">
                                    {paginatedAttachments.map((attachment) => (
                                        <AttachmentCard
                                            key={attachment.attachment_id}
                                            attachment={attachment}
                                            variant="grid"
                                            isSelected={selectedAttachment?.attachment_id === attachment.attachment_id}
                                            onClick={() => setSelectedAttachment(attachment)}
                                            onPreview={() => handlePreview(attachment)}
                                            onDownload={() => handleDownload(attachment)}
                                        />
                                    ))}
                                </div>
                            ) : (
                                <div className="divide-y">
                                    {paginatedAttachments.map((attachment) => (
                                        <AttachmentCard
                                            key={attachment.attachment_id}
                                            attachment={attachment}
                                            variant="list"
                                            isSelected={selectedAttachment?.attachment_id === attachment.attachment_id}
                                            onClick={() => setSelectedAttachment(attachment)}
                                            onPreview={() => handlePreview(attachment)}
                                            onDownload={() => handleDownload(attachment)}
                                        />
                                    ))}
                                </div>
                            )
                        )}
                    </ScrollArea>

                    {/* Pagination */}
                    {currentListLength > ITEMS_PER_PAGE && (
                        <div className="p-3 border-t shrink-0 flex items-center justify-between bg-muted/30">
                            <span className="text-xs text-muted-foreground">
                                {startIndex + 1}-{Math.min(startIndex + ITEMS_PER_PAGE, currentListLength)} {t('common.of') || 'of'} {currentListLength}
                            </span>
                            <div className="flex items-center gap-1">
                                <Button
                                    variant="outline"
                                    size="icon"
                                    className="h-7 w-7"
                                    onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                                    disabled={currentPage === 1}
                                >
                                    <ChevronLeft className="h-4 w-4" />
                                </Button>
                                <span className="text-xs text-muted-foreground px-2">
                                    {currentPage} / {totalPages}
                                </span>
                                <Button
                                    variant="outline"
                                    size="icon"
                                    className="h-7 w-7"
                                    onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                                    disabled={currentPage === totalPages}
                                >
                                    <ChevronRight className="h-4 w-4" />
                                </Button>
                            </div>
                        </div>
                    )}
                </Card>

                {/* Detail Panel */}
                {selectedAttachment && (
                    <Card className="overflow-hidden h-full min-h-0 flex flex-col">
                        <AttachmentDetail
                            attachment={selectedAttachment}
                            onBack={() => setSelectedAttachment(null)}
                            onPreview={() => handlePreview(selectedAttachment)}
                            onDownload={() => handleDownload(selectedAttachment)}
                        />
                    </Card>
                )}
            </div>
        </div>
    )
}
