'use client'

import Link from 'next/link'

import { useLanguage } from '@/lib/context/language-context'
import Logo from '@/components/shadcn-studio/logo'
import { cn } from '@/lib/utils'

type FooterProps = {
    className?: string
}

const Footer = ({ className }: FooterProps) => {
    const { t } = useLanguage()
    const currentYear = new Date().getFullYear()

    return (
        <footer className={cn('bg-background/80 backdrop-blur-md border-t border-border/50', className)}>
            <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
                <div className="flex flex-col items-center gap-6 sm:flex-row sm:justify-between">
                    {/* Logo */}
                    <Link href="/">
                        <Logo className="gap-3" />
                    </Link>

                    {/* Legal Links */}
                    <nav className="flex items-center gap-6 text-sm text-muted-foreground">
                        <Link
                            href="/privacy-policy"
                            className="hover:text-foreground transition-colors"
                        >
                            {t('legal.privacyPolicy')}
                        </Link>
                        <Link
                            href="/terms-of-service"
                            className="hover:text-foreground transition-colors"
                        >
                            {t('legal.termsOfService')}
                        </Link>
                    </nav>
                </div>

                {/* Copyright */}
                <div className="mt-6 border-t border-border/50 pt-6 text-center text-sm text-muted-foreground">
                    <p>
                        © {currentYear} Corretto. {t('legal.allRightsReserved')}
                    </p>
                </div>
            </div>
        </footer>
    )
}

export default Footer
