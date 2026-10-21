'use client'

import Link from 'next/link'
import { Sparkles, Globe, Moon, Sun, Monitor, Check } from 'lucide-react'

import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'

import { cn } from '@/lib/utils'

import Logo from '@/components/shadcn-studio/logo'
import { useTheme } from '@/lib/context/theme-context'
import { useLanguage } from '@/lib/context/language-context'

type HeaderProps = {
  className?: string
}

import { useState, useEffect } from 'react'

const Header = ({ className }: HeaderProps) => {
  const { theme, setTheme, resolvedTheme } = useTheme()
  const { language, setLanguage, t } = useLanguage()
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    setMounted(true)
  }, [])

  return (
    <header className={cn('bg-background/80 backdrop-blur-md sticky top-0 z-50 h-16 border-b border-border/50', className)}>
      <div className='mx-auto flex h-full max-w-7xl items-center justify-between gap-6 px-4 sm:px-6 lg:px-8'>
        {/* Logo */}
        <Link href='/'>
          <Logo className='gap-3' />
        </Link>

        {/* CTA Buttons */}
        <div className='flex items-center gap-1 sm:gap-2'>
          {/* Theme Switcher */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant='ghost' size='icon' className='h-9 w-9'>
                {!mounted ? (
                  <Sun className='h-4 w-4' />
                ) : resolvedTheme === 'dark' ? (
                  <Moon className='h-4 w-4' />
                ) : (
                  <Sun className='h-4 w-4' />
                )}
                <span className='sr-only'>{t('theme.title')}</span>
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align='end'>
              <DropdownMenuItem onClick={() => setTheme('light')}>
                <Sun className='mr-2 h-4 w-4' />
                {t('theme.light')}
                {theme === 'light' && <Check className='ml-auto h-4 w-4' />}
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => setTheme('dark')}>
                <Moon className='mr-2 h-4 w-4' />
                {t('theme.dark')}
                {theme === 'dark' && <Check className='ml-auto h-4 w-4' />}
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => setTheme('system')}>
                <Monitor className='mr-2 h-4 w-4' />
                {t('theme.system')}
                {theme === 'system' && <Check className='ml-auto h-4 w-4' />}
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>

          {/* Language Switcher */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant='ghost' size='icon' className='h-9 w-9'>
                <Globe className='h-4 w-4' />
                <span className='sr-only'>{t('language.title')}</span>
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align='end'>
              <DropdownMenuItem onClick={() => setLanguage('en')}>
                <span className='mr-2'>🇬🇧</span>
                {t('language.en')}
                {language === 'en' && <Check className='ml-auto h-4 w-4' />}
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => setLanguage('it')}>
                <span className='mr-2'>🇮🇹</span>
                {t('language.it')}
                {language === 'it' && <Check className='ml-auto h-4 w-4' />}
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>

          <div className='w-px h-5 bg-border/60 mx-1 max-sm:hidden' />

          <Button variant='ghost' className='max-sm:hidden' asChild>
            <Link href='/login'>{t('auth.signIn')}</Link>
          </Button>

          <Button className='rounded-lg' asChild>
            <Link href='/login?mode=register'>{t('auth.getStartedShort')}</Link>
          </Button>
        </div>
      </div>
    </header>
  )
}

export default Header
