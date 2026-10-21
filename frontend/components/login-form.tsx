"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { useAuth } from "@/lib/context/auth-context"
import { backendService } from "@/lib/api/backend-service"
import { useLanguage } from "@/lib/context/language-context"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Loader2, ArrowLeft, CheckCircle2 } from "lucide-react"
import { toast } from "sonner"
import { PasswordInput } from "@/components/ui/password-input"

interface LoginFormProps extends React.ComponentProps<"div"> {
  onForgotPassword?: () => void
}

export function LoginForm({
  className,
  onForgotPassword,
  ...props
}: LoginFormProps) {
  const router = useRouter()
  const { login } = useAuth()
  const { t } = useLanguage()

  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [isLoading, setIsLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!email || !password) {
      toast.error(t('auth.fillAllFields'))
      return
    }

    setIsLoading(true)

    try {
      const response = await login(email, password)
      toast.success(response.message || t('auth.loginSuccess'))
      router.push('/select-subscription')
    } catch (error) {
      const message = error instanceof Error ? error.message : t('auth.loginFailed')
      toast.error(message)
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className={cn("flex flex-col gap-6", className)} {...props}>
      <form onSubmit={handleSubmit} className="flex flex-col gap-6">
        <div className="flex flex-col items-center gap-2 text-center">
          <h1 className="text-2xl font-bold">{t('auth.welcomeBack')}</h1>
          <p className="text-muted-foreground text-sm text-balance">
            {t('auth.signInToAccount')}
          </p>
        </div>

        <div className="grid gap-4">
          <div className="grid gap-2">
            <Label htmlFor="email">{t('auth.email')}</Label>
            <Input
              id="email"
              type="email"
              placeholder={t('auth.emailPlaceholder')}
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              disabled={isLoading}
            />
          </div>

          <div className="grid gap-2">
            <div className="flex items-center">
              <Label htmlFor="password">{t('auth.password')}</Label>
              <button
                type="button"
                onClick={onForgotPassword}
                className="ml-auto text-sm underline-offset-4 hover:underline text-muted-foreground"
              >
                {t('auth.forgotPassword')}
              </button>
            </div>
            <PasswordInput
              id="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              disabled={isLoading}
            />
          </div>

          <Button type="submit" className="w-full" disabled={isLoading}>
            {isLoading ? (
              <>
                <Loader2 className="mr-2 size-4 animate-spin" />
                {t('auth.signingIn')}
              </>
            ) : (
              t('auth.signIn')
            )}
          </Button>
        </div>
      </form>
    </div>
  )
}

interface ForgotPasswordFormProps extends React.ComponentProps<"div"> {
  onBack?: () => void
}

export function ForgotPasswordForm({
  className,
  onBack,
  ...props
}: ForgotPasswordFormProps) {
  const { t } = useLanguage()
  const [email, setEmail] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [success, setSuccess] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!email) {
      toast.error(t('auth.fillAllFields'))
      return
    }

    setIsLoading(true)

    try {
      await backendService.resetPassword({ email })
      setSuccess(true)
    } catch (error) {
      const message = error instanceof Error ? error.message : "Si è verificato un errore."
      toast.error(message)
    } finally {
      setIsLoading(false)
    }
  }

  if (success) {
    return (
      <div className={cn("flex flex-col gap-6", className)} {...props}>
        <div className="flex flex-col items-center gap-4 text-center">
          <div className="size-16 rounded-full bg-chart-2/20 flex items-center justify-center">
            <CheckCircle2 className="size-8 text-chart-2" />
          </div>
          <h1 className="text-2xl font-bold">Email inviata!</h1>
          <p className="text-muted-foreground text-sm text-balance">
            Abbiamo inviato un&apos;email a <strong>{email}</strong> con le istruzioni per reimpostare la password.
          </p>
          <Button variant="outline" onClick={onBack} className="mt-2 text-foreground">
            <ArrowLeft className="mr-2 size-4" />
            Torna al login
          </Button>
        </div>
      </div>
    )
  }

  return (
    <div className={cn("flex flex-col gap-6", className)} {...props}>
      <form onSubmit={handleSubmit} className="flex flex-col gap-6">
        <div className="flex flex-col items-center gap-2 text-center">
          <h1 className="text-2xl font-bold">Recupera password</h1>
          <p className="text-muted-foreground text-sm text-balance">
            Inserisci la tua email per ricevere il link di reset
          </p>
        </div>

        <div className="grid gap-4">
          <div className="grid gap-2">
            <Label htmlFor="reset-email">Email</Label>
            <Input
              id="reset-email"
              type="email"
              placeholder="mario.rossi@esempio.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              disabled={isLoading}
            />
          </div>

          <Button type="submit" className="w-full" disabled={isLoading}>
            {isLoading ? (
              <>
                <Loader2 className="mr-2 size-4 animate-spin" />
                Invio in corso...
              </>
            ) : (
              "Invia link di reset"
            )}
          </Button>

          <Button type="button" variant="ghost" onClick={onBack} className="w-full">
            <ArrowLeft className="mr-2 size-4" />
            Torna al login
          </Button>
        </div>
      </form>
    </div>
  )
}
