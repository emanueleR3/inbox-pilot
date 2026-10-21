'use client'

import { useState } from 'react'
import { useAuth } from '@/lib/context/auth-context'
import { useLanguage } from '@/lib/context/language-context'
import { backendService } from '@/lib/api/backend-service'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import { PasswordInput } from '@/components/ui/password-input'
import { Button } from '@/components/ui/button'
import { Separator } from '@/components/ui/separator'
import { toast } from 'sonner'
import { User, Lock, Building2, Loader2 } from 'lucide-react'

export function ProfileSettings() {
    const { session, currentSubscription } = useAuth()
    const { t } = useLanguage()

    const [currentPassword, setCurrentPassword] = useState('')
    const [newPassword, setNewPassword] = useState('')
    const [confirmPassword, setConfirmPassword] = useState('')
    const [isUpdating, setIsUpdating] = useState(false)

    const handlePasswordChange = async (e: React.FormEvent) => {
        e.preventDefault()

        if (newPassword !== confirmPassword) {
            toast.error(t('settings.profile.passwordMismatch'))
            return
        }

        if (newPassword.length < 8) {
            toast.error(t('auth.passwordMinLength'))
            return
        }

        setIsUpdating(true)
        try {
            await backendService.updatePassword({
                old_password: currentPassword,
                new_password: newPassword,
                access_token: session?.access_token || ''
            })
            toast.success(t('settings.profile.passwordSuccess'))
            setCurrentPassword('')
            setNewPassword('')
            setConfirmPassword('')
        } catch (error) {
            console.error('Password update failed:', error)
            toast.error(t('settings.profile.passwordError'))
        } finally {
            setIsUpdating(false)
        }
    }

    const userEmail = session?.user?.email || ''

    return (
        <div className="space-y-6">
            {/* Account Information */}
            <Card>
                <CardHeader>
                    <div className="flex items-center gap-2">
                        <User className="h-5 w-5 text-muted-foreground" />
                        <CardTitle>{t('settings.profile.title')}</CardTitle>
                    </div>
                    <CardDescription>{t('settings.profile.description')}</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                    <div className="grid gap-4 sm:grid-cols-2">
                        <div className="space-y-2">
                            <Label>{t('settings.profile.email')}</Label>
                            <Input value={userEmail} disabled className="bg-muted" />
                        </div>
                        <div className="space-y-2">
                            <Label>{t('settings.profile.subscription')}</Label>
                            <Input value={currentSubscription?.name || '-'} disabled className="bg-muted" />
                        </div>
                    </div>
                    {currentSubscription?.plan && (
                        <div className="flex items-center gap-2 pt-2">
                            <Building2 className="h-4 w-4 text-muted-foreground" />
                            <span className="text-sm text-muted-foreground">{t('settings.profile.plan')}:</span>
                            <span className="text-sm font-medium capitalize">{currentSubscription.plan}</span>
                        </div>
                    )}
                </CardContent>
            </Card>

            {/* Change Password */}
            <Card>
                <CardHeader>
                    <div className="flex items-center gap-2">
                        <Lock className="h-5 w-5 text-muted-foreground" />
                        <CardTitle>{t('settings.profile.changePassword')}</CardTitle>
                    </div>
                </CardHeader>
                <CardContent>
                    <form onSubmit={handlePasswordChange} className="space-y-4">
                        <div className="space-y-2">
                            <Label htmlFor="currentPassword">{t('settings.profile.currentPassword')}</Label>
                            <PasswordInput
                                id="currentPassword"
                                value={currentPassword}
                                onChange={(e) => setCurrentPassword(e.target.value)}
                                required
                            />
                        </div>
                        <Separator />
                        <div className="grid gap-4 sm:grid-cols-2">
                            <div className="space-y-2">
                                <Label htmlFor="newPassword">{t('settings.profile.newPassword')}</Label>
                                <PasswordInput
                                    id="newPassword"
                                    value={newPassword}
                                    onChange={(e) => setNewPassword(e.target.value)}
                                    required
                                />
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="confirmPassword">{t('settings.profile.confirmPassword')}</Label>
                                <PasswordInput
                                    id="confirmPassword"
                                    value={confirmPassword}
                                    onChange={(e) => setConfirmPassword(e.target.value)}
                                    required
                                />
                            </div>
                        </div>
                        <Button type="submit" disabled={isUpdating}>
                            {isUpdating ? (
                                <>
                                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                    {t('settings.saving')}
                                </>
                            ) : (
                                t('settings.profile.updatePassword')
                            )}
                        </Button>
                    </form>
                </CardContent>
            </Card>
        </div>
    )
}
