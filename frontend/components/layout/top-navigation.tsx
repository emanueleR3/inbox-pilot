"use client"

import * as React from "react"
import Link from "next/link"
import { useRouter } from "next/navigation"
import {
    LogOut,
    Settings,
    User,
    Menu,
    X,
    Building,
    ChevronLeft,
    Bell
} from "lucide-react"

import { Button } from "@/components/ui/button"
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuSeparator,
    DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
    DialogDescription,
} from "@/components/ui/dialog"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { ThemeLanguageSwitcher } from "@/components/theme-language-switcher"
import { useAuth, useSubscriptionConfig } from "@/lib/context/auth-context"
import { useLanguage } from "@/lib/context/language-context"
import { backendService, AppNotification } from "@/lib/api/backend-service"

export function TopNavigation() {
    const router = useRouter()
    const { session, logout, currentSubscription, activeServiceId } = useAuth()
    const { isConfigured } = useSubscriptionConfig()
    const { t } = useLanguage()

    const [notifications, setNotifications] = React.useState<AppNotification[]>([])
    const [unreadCount, setUnreadCount] = React.useState(0)
    const [isLoadingNotifications, setIsLoadingNotifications] = React.useState(false)
    const [selectedNotification, setSelectedNotification] = React.useState<AppNotification | null>(null)

    // Helper to format text and strip bracket metadata like [image: Google]
    const formatNotificationText = (text?: string) => {
        if (!text) return "";
        return text.replace(/\[image:\s*[^\]]+\]/gi, '').trim();
    }

    // Prioritize the connected service email matching the active service
    const activeService = activeServiceId
        ? currentSubscription?.services?.find(s => s.service_id === activeServiceId)
        : null
    const userEmail = activeService?.email || currentSubscription?.services?.[0]?.email || session?.user?.email || ""

    React.useEffect(() => {
        if (!userEmail) return;

        const fetchNotifications = async () => {

            setIsLoadingNotifications(true)
            try {
                const response = await backendService.getNotifications(userEmail)


                // the api returns { notifications: [...], total: X } but if there are no notifications it might return undefined or an empty object depending on the fastAPI setup
                // sometimes the response can be just an array if the backend doesn't wrap it
                const notificationsArray = response?.notifications || (Array.isArray(response) ? response : [])

                if (notificationsArray) {
                    setNotifications(notificationsArray)
                    const unread = notificationsArray.filter((n: AppNotification) => !n.view).length
                    setUnreadCount(unread)
                }
            } catch (error) {
                console.error("🔔 [TopNavigation] Failed to load notifications", error)
            } finally {
                setIsLoadingNotifications(false)
            }
        }

        fetchNotifications()
    }, [userEmail])

    const handleNotificationClick = async (notification: AppNotification) => {
        setSelectedNotification(notification)

        if (notification.view) return;

        try {
            await backendService.markNotificationRead(notification.notification_id)
            setNotifications(prev => prev.map(n =>
                n.notification_id === notification.notification_id ? { ...n, view: true } : n
            ))
            setUnreadCount(prev => Math.max(0, prev - 1))
        } catch (error) {
            console.error("Failed to mark notification as read", error)
        }
    }

    const handleLogout = async () => {
        await logout()
        router.push("/login")
    }

    const userInitials = userEmail
        .split("@")[0]
        .slice(0, 2)
        .toUpperCase()

    const workspaceName = currentSubscription?.name || t('nav.workspaces') || "Workspace"

    return (
        <header className="sticky top-0 z-40 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
            {/* Full width container as requested */}
            <div className="w-full h-14 flex items-center justify-between px-4 sm:px-6">
                {/* Left: Back to Services + Logo */}
                <div className="flex items-center gap-1 sm:gap-3">
                    <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => router.push('/service-list')}
                        className="text-muted-foreground hover:text-foreground gap-1 px-2"
                        title={t('nav.backToServices') || 'Back to Services'}
                    >
                        <ChevronLeft className="h-4 w-4" />
                        <span className="hidden sm:inline text-xs">{t('nav.backToServices') || 'Services'}</span>
                    </Button>

                    <div className="hidden sm:block h-5 w-px bg-border mx-1" />
                    <Link href="/dashboard" className="flex items-center gap-2 font-bold text-xl">
                        <span className="text-primary">Corretto</span>
                    </Link>
                </div>

                {/* Right: Actions */}
                <div className="flex items-center gap-1 sm:gap-2 shrink-0 z-50">
                    {/* Notifications */}
                    <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                            <Button variant="ghost" size="icon" className="relative h-9 w-9 shrink-0">
                                <Bell className="h-5 w-5 text-muted-foreground" />
                                {unreadCount > 0 && (
                                    <span className="absolute top-1.5 right-1.5 flex h-4 w-4 items-center justify-center rounded-full bg-red-500 text-[10px] font-bold text-white shadow-sm ring-2 ring-background">
                                        {unreadCount > 99 ? '99+' : unreadCount}
                                    </span>
                                )}
                            </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent className="w-80 sm:w-96" align="end" forceMount>
                            <div className="flex items-center justify-between p-4 pb-2">
                                <h4 className="font-semibold">{t('nav.notifications') || "Notifications"}</h4>
                                {unreadCount > 0 && (
                                    <span className="text-xs text-muted-foreground">{unreadCount} {t('nav.unread') || "unread"}</span>
                                )}
                            </div>
                            <DropdownMenuSeparator />
                            <div className="max-h-[350px] overflow-y-auto overflow-x-hidden">
                                {isLoadingNotifications ? (
                                    <div className="p-4 text-center text-sm text-muted-foreground">
                                        {t('nav.loading') || "Loading..."}
                                    </div>
                                ) : notifications.length === 0 ? (
                                    <div className="p-4 text-center text-sm text-muted-foreground">
                                        {t('nav.noNotifications') || "No notifications"}
                                    </div>
                                ) : (
                                    <div className="flex flex-col">
                                        {notifications.map((notif) => (
                                            <DropdownMenuItem
                                                key={notif.notification_id}
                                                className={`flex flex-col items-start gap-1.5 cursor-pointer p-3.5 border-b border-border/50 last:border-0 ${!notif.view ? 'bg-primary/5 dark:bg-primary/10' : ''}`}
                                                onSelect={(e) => {
                                                    e.preventDefault();
                                                    handleNotificationClick(notif);
                                                }}
                                            >
                                                <div className="flex w-full items-start justify-between gap-3">
                                                    <span className={`text-sm font-semibold leading-tight line-clamp-2 flex-1 text-left ${!notif.view ? 'text-foreground' : 'text-muted-foreground'}`}>
                                                        {formatNotificationText(notif.text)}
                                                    </span>
                                                    <span className="text-[10px] text-muted-foreground mt-0.5 whitespace-nowrap">
                                                        {notif.email_datetime ? new Date(notif.email_datetime).toLocaleDateString([], { hour: '2-digit', minute: '2-digit' }) : ''}
                                                    </span>
                                                    {!notif.view && (
                                                        <span className="flex h-2 w-2 rounded-full bg-primary flex-shrink-0 mt-1" />
                                                    )}
                                                </div>
                                                {notif.email_body && (
                                                    <span className="line-clamp-2 text-xs text-muted-foreground mt-0.5 break-words text-left w-full">
                                                        {formatNotificationText(notif.email_body)}
                                                    </span>
                                                )}
                                            </DropdownMenuItem>
                                        ))}
                                    </div>
                                )}
                            </div>
                        </DropdownMenuContent>
                    </DropdownMenu>

                    {/* Theme & Language Base Switchers */}
                    <ThemeLanguageSwitcher fixed={false} />

                    {/* Account Dropdown */}
                    <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                            <Button variant="ghost" className="relative h-9 w-9 rounded-full sm:h-10 sm:w-auto sm:rounded-md sm:px-2 sm:gap-2">
                                <Avatar className="h-8 w-8">
                                    <AvatarFallback className="bg-primary/10 text-primary text-xs">
                                        {userInitials}
                                    </AvatarFallback>
                                </Avatar>
                                <div className="hidden sm:flex flex-col items-start text-sm text-left">
                                    <span className="font-medium text-xs leading-none mb-1">
                                        {workspaceName}
                                    </span>
                                    <span className="text-[10px] text-muted-foreground leading-none">
                                        {userEmail}
                                    </span>
                                </div>
                            </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent className="w-56" align="end" forceMount>
                            <DropdownMenuItem asChild>
                                <div className="flex items-center justify-between p-2 mb-1 bg-muted/30 rounded-md">
                                    <div className="flex flex-col space-y-1">
                                        <p className="text-xs font-medium leading-none text-muted-foreground">{t('nav.workspaces')}</p>
                                        <p className="text-sm font-medium">{workspaceName}</p>
                                    </div>
                                </div>
                            </DropdownMenuItem>
                            <DropdownMenuSeparator />
                            <DropdownMenuItem asChild>
                                <Link href="/dashboard/profile" className="cursor-pointer w-full flex items-center">
                                    <User className="mr-2 h-4 w-4" />
                                    <span>{t('nav.account') || "Account"}</span>
                                </Link>
                            </DropdownMenuItem>
                            <DropdownMenuItem asChild>
                                <Link href="/dashboard/settings" className="cursor-pointer w-full flex items-center">
                                    <Settings className="mr-2 h-4 w-4" />
                                    <span>{t('nav.settings') || "Settings"}</span>
                                </Link>
                            </DropdownMenuItem>
                            <DropdownMenuSeparator />
                            <DropdownMenuItem
                                onClick={handleLogout}
                                className="text-red-600 focus:text-red-600 focus:bg-red-100 dark:focus:bg-red-900/20 cursor-pointer"
                            >
                                <LogOut className="mr-2 h-4 w-4" />
                                <span>{t('nav.logout') || "Log out"}</span>
                            </DropdownMenuItem>
                        </DropdownMenuContent>
                    </DropdownMenu>
                </div>
            </div>

            {/* Notification Detail Dialog */}
            <Dialog open={!!selectedNotification} onOpenChange={(open) => !open && setSelectedNotification(null)}>
                <DialogContent className="sm:max-w-md w-11/12 max-w-[90vw] overflow-y-auto overflow-x-hidden max-h-[85vh] p-4 sm:p-6 flex flex-col">
                    <DialogHeader className="shrink-0">
                        <DialogTitle className="leading-relaxed break-words whitespace-normal text-left text-base sm:text-lg pr-4">
                            {selectedNotification ? formatNotificationText(selectedNotification.text) : ''}
                        </DialogTitle>
                        <DialogDescription className="text-left flex items-center gap-2 mt-2">
                            <span>{selectedNotification?.email_datetime ? new Date(selectedNotification.email_datetime).toLocaleString() : ''}</span>
                        </DialogDescription>
                    </DialogHeader>
                    <div className="py-2 flex flex-col gap-3 flex-1 overflow-hidden">
                        {selectedNotification?.email_body ? (
                            <div className="text-sm rounded-md bg-muted/50 p-3 sm:p-4 whitespace-pre-wrap break-words overflow-y-auto overflow-x-hidden text-left h-full border border-border/50">
                                {formatNotificationText(selectedNotification.email_body)}
                            </div>
                        ) : null}
                    </div>
                </DialogContent>
            </Dialog>
        </header>
    )
}
