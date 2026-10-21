'use client'

import { useState } from 'react'
import Image from 'next/image'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import {
  Field,
  FieldDescription,
  FieldGroup,
  FieldLabel,
} from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import { backendService } from '@/lib/api/backend-service'
import { useLanguage } from '@/lib/context/language-context'
import { ThemeLanguageSwitcher } from '@/components/theme-language-switcher'
import { toast } from 'sonner'
import { Loader2, ArrowLeft, Mail, CheckCircle2 } from 'lucide-react'

export default function ForgotPasswordPage() {
  const { t } = useLanguage()
  const [email, setEmail] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [isSuccess, setIsSuccess] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!email) {
      toast.error(t('forgotPassword.enterEmail'))
      return
    }

    setIsLoading(true)

    try {
      const response = await backendService.resetPassword({ email })
      
      if (response.success) {
        setIsSuccess(true)
        toast.success(response.message || t('forgotPassword.emailSent'))
      } else {
        toast.error(response.message || t('forgotPassword.error'))
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : t('forgotPassword.error')
      toast.error(message)
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="flex min-h-svh w-full items-center justify-center p-6 md:p-10">
      <ThemeLanguageSwitcher />
      <div className="w-full max-w-sm">
        <div className="flex flex-col gap-6">
          {/* Corretto Logo */}
          <div className="flex justify-center">
            <Image
              src="/corretto-avatar.png"
              alt="Corretto"
              width={64}
              height={64}
              className="rounded-xl"
              priority
            />
          </div>

          <Card>
            <CardHeader className="text-center">
              <CardTitle>{t('forgotPassword.title')}</CardTitle>
              <CardDescription>
                {isSuccess ? t('forgotPassword.checkEmail') : t('forgotPassword.description')}
              </CardDescription>
            </CardHeader>
            <CardContent>
              {isSuccess ? (
                <div className="flex flex-col items-center gap-4">
                  <div className="flex h-16 w-16 items-center justify-center rounded-full bg-primary/10">
                    <CheckCircle2 className="h-8 w-8 text-primary" />
                  </div>
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <Mail className="h-4 w-4" />
                    <span>{email}</span>
                  </div>
                  <p className="text-center text-sm text-muted-foreground">
                    {t('forgotPassword.instructions')}
                  </p>
                  <Button
                    variant="outline"
                    className="w-full mt-2"
                    onClick={() => {
                      setIsSuccess(false)
                      setEmail('')
                    }}
                  >
                    {t('forgotPassword.tryAnother')}
                  </Button>
                </div>
              ) : (
                <form onSubmit={handleSubmit}>
                  <FieldGroup>
                    <Field>
                      <FieldLabel htmlFor="email">{t('auth.email')}</FieldLabel>
                      <Input
                        id="email"
                        type="email"
                        placeholder="m@example.com"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        disabled={isLoading}
                        required
                      />
                      <FieldDescription>
                        {t('forgotPassword.emailHint')}
                      </FieldDescription>
                    </Field>
                    <Field>
                      <Button type="submit" disabled={isLoading} className="w-full">
                        {isLoading ? (
                          <>
                            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                            {t('forgotPassword.sending')}
                          </>
                        ) : (
                          t('forgotPassword.sendLink')
                        )}
                      </Button>
                    </Field>
                  </FieldGroup>
                </form>
              )}
            </CardContent>
          </Card>

          {/* Back to login link */}
          <Link
            href="/login"
            className="flex items-center justify-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
          >
            <ArrowLeft className="h-4 w-4" />
            {t('forgotPassword.backToLogin')}
          </Link>
        </div>
      </div>
    </div>
  )
}
