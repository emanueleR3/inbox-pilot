import type { Metadata } from 'next'

export const metadata: Metadata = {
    title: 'Privacy Policy | Corretto',
    description: 'Privacy Policy for Corretto - AI-powered email and calendar management platform. Learn how we handle your data.',
    openGraph: {
        title: 'Privacy Policy | Corretto',
        description: 'Privacy Policy for Corretto - AI-powered email and calendar management platform.',
        type: 'website',
    },
}

export default function PrivacyPolicyLayout({
    children,
}: {
    children: React.ReactNode
}) {
    return children
}
