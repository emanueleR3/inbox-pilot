'use client'

import { useEffect } from 'react'
import Image from 'next/image'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { RotateCcw, Home } from 'lucide-react'

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  useEffect(() => {
    // Log the error to an error reporting service
    console.error(error)
  }, [error])

  return (
    <div className="grid min-h-svh grid-cols-1 lg:grid-cols-2">
      {/* Left Section: Content */}
      <div className="flex flex-col items-center justify-center px-4 py-8 text-center">
        {/* Corretto Logo */}
        <div className="mb-8">
          <Image
            src="/corretto-avatar.png"
            alt="Corretto"
            width={80}
            height={80}
            className="rounded-2xl"
            priority
          />
        </div>
        
        <h2 className="mb-4 text-5xl font-bold text-primary">Whoops!</h2>
        <h3 className="mb-2 text-2xl font-semibold">Something went wrong</h3>
        <p className="text-muted-foreground mb-8 max-w-sm">
          An unexpected error occurred. Don&apos;t worry, we&apos;re on it. Please try again or go back to the home page.
        </p>
        
        <div className="flex flex-col sm:flex-row gap-3">
          <Button onClick={reset} size="lg" className="gap-2">
            <RotateCcw className="h-4 w-4" />
            Try again
          </Button>
          <Button asChild variant="outline" size="lg" className="gap-2">
            <Link href="/">
              <Home className="h-4 w-4" />
              Back to home
            </Link>
          </Button>
        </div>
      </div>

      {/* Right Section: Illustration */}
      <div className="relative max-h-svh w-full p-2 max-lg:hidden">
        <div className="h-full w-full rounded-2xl bg-slate-900 dark:bg-slate-800 flex items-center justify-center">
          {/* Decorative error background */}
          <div className="text-[12rem] font-black text-slate-800 dark:text-slate-700 select-none opacity-50">
            ERROR
          </div>
        </div>
      </div>
    </div>
  )
}
