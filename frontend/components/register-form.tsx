"use client"

import { useState } from "react"
import { useLanguage } from "@/lib/context/language-context"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Loader2, ArrowLeft, Calendar } from "lucide-react"
import { toast } from "sonner"
import { PasswordInput } from "@/components/ui/password-input"
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog"

export function RegisterForm({
    className,
    ...props
}: React.ComponentProps<"form">) {
    const { t } = useLanguage()

    // Form state
    const [step, setStep] = useState<"account" | "subscription">("account")
    const [isLoading, setIsLoading] = useState(false)
    const [showPreviewModal, setShowPreviewModal] = useState(false)

    // Account fields
    const [email, setEmail] = useState("")
    const [password, setPassword] = useState("")
    const [confirmPassword, setConfirmPassword] = useState("")

    // Subscription fields
    const [companyName, setCompanyName] = useState("")
    const [industry, setIndustry] = useState("")
    const [vatNumber, setVatNumber] = useState("")
    const [city, setCity] = useState("")
    const [address, setAddress] = useState("")

    const handleAccountNext = (e: React.FormEvent) => {
        e.preventDefault()

        if (!email || !password || !confirmPassword) {
            toast.error(t('auth.fillAllFields'))
            return
        }

        if (password !== confirmPassword) {
            toast.error(t('auth.passwordsDoNotMatch'))
            return
        }

        if (password.length < 8) {
            toast.error(t('auth.passwordMinLength'))
            return
        }

        setStep("subscription")
    }

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()

        if (!companyName || !city || !address) {
            toast.error(t('auth.fillRequired'))
            return
        }

        setIsLoading(true)

        try {
            // Simulate checking before showing modal
            await new Promise(resolve => setTimeout(resolve, 1000))

            // Disabled API call and redirect for Preview Mode
            // Show Preview modal instead
            setShowPreviewModal(true)
        } catch (error) {
            const message = error instanceof Error ? error.message : t('auth.registrationFailed')
            toast.error(message)
        } finally {
            setIsLoading(false)
        }
    }

    if (step === "account") {
        return (
            <form
                onSubmit={handleAccountNext}
                className={cn("flex flex-col gap-6", className)}
                {...props}
            >
                <div className="flex flex-col items-center gap-2 text-center">
                    <h1 className="text-2xl font-bold">{t('auth.createAccount')}</h1>
                    <p className="text-muted-foreground text-sm text-balance">
                        {t('auth.getStarted')}
                    </p>
                </div>

                <div className="grid gap-4">
                    <div className="grid gap-2">
                        <Label htmlFor="reg-email">{t('auth.email')}</Label>
                        <Input
                            id="reg-email"
                            type="email"
                            placeholder={t('auth.emailPlaceholder')}
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            required
                        />
                    </div>

                    <div className="grid gap-2">
                        <Label htmlFor="reg-password">{t('auth.password')}</Label>
                        <PasswordInput
                            id="reg-password"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            required
                        />
                        <p className="text-[12px] text-muted-foreground">{t('auth.passwordMinLength')}</p>
                    </div>

                    <div className="grid gap-2">
                        <Label htmlFor="reg-confirm-password">{t('auth.confirmPassword')}</Label>
                        <PasswordInput
                            id="reg-confirm-password"
                            value={confirmPassword}
                            onChange={(e) => setConfirmPassword(e.target.value)}
                            required
                        />
                    </div>

                    <Button type="submit" className="w-full">
                        {t('auth.continue')}
                    </Button>
                </div>

                {/* Preview Modal */}
                <Dialog open={showPreviewModal} onOpenChange={setShowPreviewModal}>
                    <DialogContent className="sm:max-w-md">
                        <DialogHeader>
                            <DialogTitle>{t('previewModal.title')}</DialogTitle>
                            <DialogDescription className="pt-2 text-base">
                                {t('previewModal.description')}
                            </DialogDescription>
                        </DialogHeader>
                        <DialogFooter className="sm:justify-start pt-4">
                            <Button asChild className="w-full">
                                <a href="https://calendar.app.google/rcKEaY9XqM4Yih57A" target="_blank" rel="noopener noreferrer">
                                    <Calendar className="mr-2 size-4" />
                                    {t('previewModal.scheduleButton')}
                                </a>
                            </Button>
                        </DialogFooter>
                    </DialogContent>
                </Dialog>
            </form>
        )
    }

    return (
        <form
            onSubmit={handleSubmit}
            className={cn("flex flex-col gap-6", className)}
            {...props}
        >
            <div className="flex flex-col items-center gap-2 text-center relative">
                <button
                    type="button"
                    onClick={() => setStep("account")}
                    className="absolute left-0 top-1 text-muted-foreground hover:text-foreground"
                >
                    <ArrowLeft className="size-5" />
                </button>
                <h1 className="text-2xl font-bold">{t('auth.companyInfo')}</h1>
                <p className="text-muted-foreground text-sm text-balance">
                    {t('auth.tellUsAbout')}
                </p>
            </div>

            <div className="grid gap-4">
                <div className="grid gap-2">
                    <Label htmlFor="reg-company-name">{t('auth.companyName')} *</Label>
                    <Input
                        id="reg-company-name"
                        type="text"
                        placeholder={t('auth.companyNamePlaceholder')}
                        value={companyName}
                        onChange={(e) => setCompanyName(e.target.value)}
                        required
                        disabled={isLoading}
                    />
                </div>

                <div className="grid grid-cols-2 gap-3">
                    <div className="grid gap-2">
                        <Label htmlFor="reg-city">{t('auth.city')} *</Label>
                        <Input
                            id="reg-city"
                            type="text"
                            placeholder={t('auth.cityPlaceholder')}
                            value={city}
                            onChange={(e) => setCity(e.target.value)}
                            required
                            disabled={isLoading}
                        />
                    </div>
                    <div className="grid gap-2">
                        <Label htmlFor="reg-industry">{t('auth.industry')}</Label>
                        <Input
                            id="reg-industry"
                            type="text"
                            placeholder={t('auth.industryPlaceholder')}
                            value={industry}
                            onChange={(e) => setIndustry(e.target.value)}
                            disabled={isLoading}
                        />
                    </div>
                </div>

                <div className="grid gap-2">
                    <Label htmlFor="reg-address">{t('auth.address')} *</Label>
                    <Input
                        id="reg-address"
                        type="text"
                        placeholder={t('auth.addressPlaceholder')}
                        value={address}
                        onChange={(e) => setAddress(e.target.value)}
                        required
                        disabled={isLoading}
                    />
                </div>

                <div className="grid gap-2">
                    <div className="flex justify-between items-center">
                        <Label htmlFor="reg-vat-number">{t('auth.vatNumber')}</Label>
                        <span className="text-xs text-muted-foreground">{t('auth.optional')}</span>
                    </div>
                    <Input
                        id="reg-vat-number"
                        type="text"
                        placeholder={t('auth.vatNumberPlaceholder')}
                        value={vatNumber}
                        onChange={(e) => setVatNumber(e.target.value)}
                        disabled={isLoading}
                    />
                </div>

                <Button type="submit" className="w-full" disabled={isLoading}>
                    {isLoading ? (
                        <>
                            <Loader2 className="mr-2 size-4 animate-spin" />
                            {t('auth.creating')}
                        </>
                    ) : (
                        t('auth.createAccount')
                    )}
                </Button>
            </div>

            {/* Preview Modal */}
            <Dialog open={showPreviewModal} onOpenChange={setShowPreviewModal}>
                <DialogContent className="sm:max-w-md">
                    <DialogHeader>
                        <DialogTitle>{t('previewModal.title')}</DialogTitle>
                        <DialogDescription className="pt-2 text-base">
                            {t('previewModal.description')}
                        </DialogDescription>
                    </DialogHeader>
                    <DialogFooter className="sm:justify-start pt-4">
                        <Button asChild className="w-full">
                            <a href="https://calendar.app.google/rcKEaY9XqM4Yih57A" target="_blank" rel="noopener noreferrer">
                                <Calendar className="mr-2 size-4" />
                                {t('previewModal.scheduleButton')}
                            </a>
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </form>
    )
}
