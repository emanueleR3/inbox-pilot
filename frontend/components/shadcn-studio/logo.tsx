'use client'

import Image from 'next/image'
import { cn } from '@/lib/utils'

type LogoProps = {
  className?: string
  showText?: boolean
}

const Logo = ({ className, showText = true }: LogoProps) => {
  return (
    <div className={cn('flex items-center gap-2', className)}>
      <Image
        src="/corretto-avatar.png"
        alt="Corretto"
        width={32}
        height={32}
        className="rounded-lg mt-1"
        priority
      />
      {showText && (
        <span className="text-xl font-bold tracking-tight">Corretto</span>
      )}
    </div>
  )
}

export default Logo
