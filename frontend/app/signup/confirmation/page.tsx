'use client'

import { Suspense } from 'react'
import { useSearchParams } from 'next/navigation'
import Image from 'next/image'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { ThemeLanguageSwitcher } from '@/components/theme-language-switcher'
import { useLanguage } from '@/lib/context/language-context'
import { Mail, CheckCircle2, ArrowRight, Loader2 } from 'lucide-react'

function ConfirmationContent() {
  const searchParams = useSearchParams()
  const email = searchParams.get('email') || 'your email'
  const { t } = useLanguage()

  return (
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
        <CardHeader className="text-center pb-2">
          <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-primary/10">
            <Mail className="h-8 w-8 text-primary" />
          </div>
          <CardTitle className="text-2xl">{t('signup.checkEmail')}</CardTitle>
          <CardDescription className="text-base">
            {t('signup.confirmationSent')}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="rounded-lg bg-muted p-4 text-center">
            <p className="font-medium text-foreground">{email}</p>
          </div>

          <div className="space-y-4">
            <div className="flex items-start gap-3">
              <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary/10">
                <CheckCircle2 className="h-4 w-4 text-primary" />
              </div>
              <div className="text-sm text-muted-foreground">
                {t('signup.clickLink')}
              </div>
            </div>
            <div className="flex items-start gap-3">
              <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary/10">
                <CheckCircle2 className="h-4 w-4 text-primary" />
              </div>
              <div className="text-sm text-muted-foreground">
                {t('signup.autoLogin')}
              </div>
            </div>
            <div className="flex items-start gap-3">
              <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary/10">
                <CheckCircle2 className="h-4 w-4 text-primary" />
              </div>
              <div className="text-sm text-muted-foreground">
                {t('signup.completeSetup')}
              </div>
            </div>
          </div>

          <div className="border-t pt-4">
            <p className="text-center text-sm text-muted-foreground">
              {t('signup.spamNotice')}{' '}
              <a
                href="/login?mode=register"
                className="text-primary underline underline-offset-4 hover:text-primary/80"
              >
                {t('signup.tryAgain')}
              </a>
            </p>
          </div>

          <Button
            variant="outline"
            className="w-full"
            onClick={() => window.location.href = '/login'}
          >
            {t('signup.goToLogin')}
            <ArrowRight className="ml-2 h-4 w-4" />
          </Button>
        </CardContent>
      </Card>
    </div>
  )
}

function LoadingFallback() {
  const { t } = useLanguage()
  return (
    <div className="flex flex-col gap-6 items-center">
      <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      <p className="text-muted-foreground">{t('signup.loading')}</p>
    </div>
  )
}

export default function ConfirmationPage() {
  return (
    <div className="flex min-h-svh w-full items-center justify-center p-6 md:p-10">
      <ThemeLanguageSwitcher />
      <div className="w-full max-w-md">
        <Suspense fallback={<LoadingFallback />}>
          <ConfirmationContent />
        </Suspense>
      </div>
    </div>
  )
}
