import Image from 'next/image'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Home } from 'lucide-react'

export default function NotFound() {
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
        
        <h2 className="mb-4 text-6xl font-bold text-primary">404</h2>
        <h3 className="mb-2 text-2xl font-semibold">Whoops! Page not found</h3>
        <p className="text-muted-foreground mb-8 max-w-sm">
          The page you&apos;re looking for doesn&apos;t exist or has been moved. Let&apos;s get you back on track.
        </p>
        
        <Button asChild size="lg" className="gap-2">
          <Link href="/">
            <Home className="h-4 w-4" />
            Back to home
          </Link>
        </Button>
      </div>

      {/* Right Section: Illustration */}
      <div className="relative max-h-svh w-full p-2 max-lg:hidden">
        <div className="h-full w-full rounded-2xl bg-slate-900 dark:bg-slate-800 flex items-center justify-center">
          {/* Decorative 404 background */}
          <div className="text-[20rem] font-black text-slate-800 dark:text-slate-700 select-none opacity-50">
            404
          </div>
        </div>
      </div>
    </div>
  )
}
