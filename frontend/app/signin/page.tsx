'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Image from 'next/image'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Loader2, CheckCircle, XCircle } from 'lucide-react'
import { useAuth } from '@/lib/context/auth-context'
import { backendService } from '@/lib/api/backend-service'
import { toast } from 'sonner'


// Parse hash fragment from URL (Supabase sends tokens in hash)
function parseHashFragment(hash: string): Record<string, string> {
  if (!hash || hash.length <= 1) return {}

  const params: Record<string, string> = {}
  const fragment = hash.substring(1) // Remove leading #

  fragment.split('&').forEach(pair => {
    const [key, value] = pair.split('=')
    if (key && value) {
      params[decodeURIComponent(key)] = decodeURIComponent(value)
    }
  })

  return params
}

// Decode JWT payload (without verification - backend will verify)
function decodeJwtPayload(token: string): Record<string, unknown> | null {
  try {
    const parts = token.split('.')
    if (parts.length !== 3) return null

    const payload = parts[1]
    // Base64url decode
    const base64 = payload.replace(/-/g, '+').replace(/_/g, '/')
    const jsonPayload = decodeURIComponent(
      atob(base64)
        .split('')
        .map(c => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
        .join('')
    )

    return JSON.parse(jsonPayload)
  } catch {
    return null
  }
}

type AuthStatus = 'loading' | 'success' | 'error'

export default function SignInPage() {
  const router = useRouter()
  const { isAuthenticated, isLoading: authLoading } = useAuth()
  const [status, setStatus] = useState<AuthStatus>('loading')
  const [message, setMessage] = useState('Verifying your email...')

  useEffect(() => {
    // If already authenticated and not loading, redirect to dashboard
    if (!authLoading && isAuthenticated) {
      router.push('/select-subscription')
      return
    }

    // Wait for auth context to be ready before processing
    if (authLoading) return

    const processAuthCallback = async () => {
      try {
        // Get hash fragment from URL
        const hash = window.location.hash
        const params = parseHashFragment(hash)

        const accessToken = params.access_token
        const type = params.type // 'signup', 'recovery', 'magiclink', etc.

        if (!accessToken) {
          // No token in URL - redirect to login
          setStatus('error')
          setMessage('No authentication token found. Redirecting to login...')
          setTimeout(() => router.push('/login'), 2000)
          return
        }

        // Decode the token to get user info
        const payload = decodeJwtPayload(accessToken)
        if (!payload || !payload.email) {
          setStatus('error')
          setMessage('Invalid authentication token. Redirecting to login...')
          setTimeout(() => router.push('/login'), 2000)
          return
        }

        const email = payload.email as string

        setMessage('Fetching your account data...')

        // Set the token for API calls
        backendService.setAccessToken(accessToken)
        backendService.setUserEmail(email)

        // For email confirmation (signup) or magic link, 
        // the user should log in with their credentials to get a full session
        // The Supabase token confirms the email but we need backend auth for subscriptions

        if (type === 'signup') {
          setStatus('success')
          setMessage('Email verified successfully! Please log in to continue.')
          toast.success('Email verified! Welcome to Corretto. Please log in.')
          setTimeout(() => router.push('/login'), 2000)
          return
        }

        if (type === 'recovery') {
          setStatus('success')
          setMessage('Password reset link verified! Redirecting...')
          toast.success('Please set your new password.')
          // Store token for password update and redirect
          sessionStorage.setItem('password_reset_token', accessToken)
          setTimeout(() => router.push('/forgot-password?reset=true'), 1500)
          return
        }

        // For magic link login, try to get user data
        try {
          const userResponse = await backendService.getUser(email)

          if (userResponse && userResponse.id) {
            setStatus('success')
            setMessage('Signed in successfully! Please log in to continue.')
            toast.success('Authentication successful! Please log in.')
            setTimeout(() => router.push('/login'), 1500)
          } else {
            throw new Error('User not found')
          }
        } catch (apiError) {
          console.error('[SignIn] API error:', apiError)
          setStatus('success')
          setMessage('Verified! Please log in to continue.')
          toast.success('Please log in to continue.')
          setTimeout(() => router.push('/login'), 2000)
        }
      } catch (error) {
        console.error('[SignIn] Error processing auth callback:', error)
        setStatus('error')
        setMessage('An error occurred. Redirecting to login...')
        setTimeout(() => router.push('/login'), 2000)
      }
    }

    processAuthCallback()
  }, [authLoading, isAuthenticated, router])

  return (
    <div className="min-h-svh w-full bg-background text-foreground flex items-center justify-center">
      <div className="flex min-h-svh w-full items-center justify-center p-6 md:p-10">
        <div className="w-full max-w-sm flex flex-col gap-6">
          {/* Corretto Logo */}
          <div className="flex justify-center">
            <Image
              src="/corretto-avatar.png"
              alt="Corretto"
              width={64}
              height={64}
              className="rounded-xl shadow-lg"
              priority
            />
          </div>

          <Card className="bg-card/90 backdrop-blur-md border-border/50 shadow-2xl">
            <CardHeader className="text-center">
              <CardTitle>
                {status === 'loading' && 'Verifying...'}
                {status === 'success' && 'Success!'}
                {status === 'error' && 'Verification Failed'}
              </CardTitle>
              <CardDescription>{message}</CardDescription>
            </CardHeader>
            <CardContent className="flex justify-center py-8">
              {status === 'loading' && (
                <Loader2 className="h-12 w-12 animate-spin text-primary" />
              )}
              {status === 'success' && (
                <CheckCircle className="h-12 w-12 text-green-500" />
              )}
              {status === 'error' && (
                <XCircle className="h-12 w-12 text-destructive" />
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}

