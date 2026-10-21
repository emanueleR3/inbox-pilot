'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'

// This page is deprecated - redirect to the new flow
export default function SubscriptionDetailsPage() {
    const router = useRouter()

    useEffect(() => {
        router.replace('/select-subscription')
    }, [router])

    return null
}
