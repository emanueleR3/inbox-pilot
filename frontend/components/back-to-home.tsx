'use client'

import Link from 'next/link'
import { ArrowLeft } from 'lucide-react'
import { useLanguage } from '@/lib/context/language-context'

export function BackToHome() {
    const { t } = useLanguage()

    return (
        <div className="fixed top-4 left-4 z-50">
            <Link
                href="/"
                className="flex items-center gap-2 text-muted-foreground hover:text-foreground transition-colors"
            >
                <ArrowLeft className="h-4 w-4" />
                <span className="text-sm font-medium">{t('auth.backToHome')}</span>
            </Link>
        </div>
    )
}
