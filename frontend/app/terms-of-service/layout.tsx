import type { Metadata } from 'next'

export const metadata: Metadata = {
    title: 'Terms of Service | Corretto',
    description: 'Terms of Service for Corretto - AI-powered email and calendar management platform. Read our terms and conditions.',
    openGraph: {
        title: 'Terms of Service | Corretto',
        description: 'Terms of Service for Corretto - AI-powered email and calendar management platform.',
        type: 'website',
    },
}

export default function TermsOfServiceLayout({
    children,
}: {
    children: React.ReactNode
}) {
    return children
}
