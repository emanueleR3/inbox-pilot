'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'

export default function ProfilePage() {
    const router = useRouter()

    useEffect(() => {
        // Redirect to settings page with profile tab selected
        router.replace('/dashboard/settings?tab=profile')
    }, [router])

    return null
}
