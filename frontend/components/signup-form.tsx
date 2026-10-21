
'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Image from 'next/image'
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
import { PasswordInput } from '@/components/ui/password-input'
import { backendService } from '@/lib/api/backend-service'
import { useLanguage } from '@/lib/context/language-context'
import { toast } from 'sonner'
import { Loader2 } from 'lucide-react'

export function SignupForm({ ...props }: React.ComponentProps<typeof Card>) {
  const router = useRouter()
  const { t } = useLanguage()

  // Form state
  const [step, setStep] = useState<'account' | 'subscription'>('account')
  const [isLoading, setIsLoading] = useState(false)

  // Account fields
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')

  // Subscription fields
  const [companyName, setCompanyName] = useState('')
  const [industry, setIndustry] = useState('')
  const [vatNumber, setVatNumber] = useState('')
  const [city, setCity] = useState('')
  const [address, setAddress] = useState('')

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

    setStep('subscription')
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!companyName || !city || !address) {
      toast.error(t('auth.fillRequired'))
      return
    }

    setIsLoading(true)

    try {
      const response = await backendService.createAccount({
        email,
        password,
        subscription: {
          name: companyName,
          vat_number: vatNumber || undefined,
          city,
          address,
          active: true,
          current_period_end: new Date(
            Date.now() + 30 * 24 * 60 * 60 * 1000
          ).toISOString(), // 30 days trial
          plan: 'personal',
          industry: industry || undefined,
        },
      })

      toast.success(response.message || t('auth.accountCreated'))

      // Redirect to confirmation page
      router.push(`/signup/confirmation?email=${encodeURIComponent(email)}`)
    } catch (error) {
      const message = error instanceof Error ? error.message : t('auth.registrationFailed')
      toast.error(message)
    } finally {
      setIsLoading(false)
    }
  }

  if (step === 'account') {
    return (
      <div className="flex flex-col gap-6 relative">


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

        <Card {...props}>
          <CardHeader className="text-center">
            <CardTitle>{t('auth.createAccount')}</CardTitle>
            <CardDescription>
              {t('auth.getStarted')}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleAccountNext}>
              <FieldGroup>
                <Field>
                  <FieldLabel htmlFor="email">{t('auth.email')}</FieldLabel>
                  <Input
                    id="email"
                    type="email"
                    placeholder={t('auth.emailPlaceholder')}
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                  />
                  <FieldDescription>
                    {t('auth.contactYou')}
                  </FieldDescription>
                </Field>
                <Field>
                  <FieldLabel htmlFor="password">{t('auth.password')}</FieldLabel>
                  <PasswordInput
                    id="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                  />
                  <FieldDescription>
                    {t('auth.passwordMinLength')}
                  </FieldDescription>
                </Field>
                <Field>
                  <FieldLabel htmlFor="confirm-password">
                    {t('auth.confirmPassword')}
                  </FieldLabel>
                  <PasswordInput
                    id="confirm-password"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    required
                  />
                </Field>
                <Field>
                  <Button type="submit" className="w-full">
                    {t('auth.continue')}
                  </Button>
                  <FieldDescription className="text-center">
                    {t('auth.haveAccount')}{' '}
                    <a
                      href="/login"
                      className="underline underline-offset-4 hover:text-primary"
                    >
                      {t('auth.signIn')}
                    </a>
                  </FieldDescription>
                </Field>
              </FieldGroup>
            </form>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-6 relative">
      {/* Back to Home Arrow - Also on step 2 */}


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

      <Card {...props}>
        <CardHeader className="text-center">
          <CardTitle>{t('auth.companyInfo')}</CardTitle>
          <CardDescription>
            {t('auth.tellUsAbout')}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit}>
            <FieldGroup>
              <Field>
                <FieldLabel htmlFor="company-name">{t('auth.companyName')} *</FieldLabel>
                <Input
                  id="company-name"
                  type="text"
                  placeholder={t('auth.companyNamePlaceholder')}
                  value={companyName}
                  onChange={(e) => setCompanyName(e.target.value)}
                  disabled={isLoading}
                  required
                />
              </Field>
              <Field>
                <FieldLabel htmlFor="industry">{t('auth.industry')}</FieldLabel>
                <Input
                  id="industry"
                  type="text"
                  placeholder={t('auth.industryPlaceholder')}
                  value={industry}
                  onChange={(e) => setIndustry(e.target.value)}
                  disabled={isLoading}
                />
              </Field>
              <Field>
                <FieldLabel htmlFor="vat-number">{t('auth.vatNumber')}</FieldLabel>
                <Input
                  id="vat-number"
                  type="text"
                  placeholder={t('auth.vatNumberPlaceholder')}
                  value={vatNumber}
                  onChange={(e) => setVatNumber(e.target.value)}
                  disabled={isLoading}
                />
                <FieldDescription>{t('auth.optional')}</FieldDescription>
              </Field>
              <Field>
                <FieldLabel htmlFor="city">{t('auth.city')} *</FieldLabel>
                <Input
                  id="city"
                  type="text"
                  placeholder={t('auth.cityPlaceholder')}
                  value={city}
                  onChange={(e) => setCity(e.target.value)}
                  disabled={isLoading}
                  required
                />
              </Field>
              <Field>
                <FieldLabel htmlFor="address">{t('auth.address')} *</FieldLabel>
                <Input
                  id="address"
                  type="text"
                  placeholder={t('auth.addressPlaceholder')}
                  value={address}
                  onChange={(e) => setAddress(e.target.value)}
                  disabled={isLoading}
                  required
                />
              </Field>
              <FieldGroup>
                <div className="flex gap-2">
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => setStep('account')}
                    disabled={isLoading}
                    className="flex-1"
                  >
                    {t('auth.back')}
                  </Button>
                  <Button type="submit" disabled={isLoading} className="flex-1">
                    {isLoading ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        {t('auth.creating')}
                      </>
                    ) : (
                      t('auth.createAccount')
                    )}
                  </Button>
                </div>
              </FieldGroup>
            </FieldGroup>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}
