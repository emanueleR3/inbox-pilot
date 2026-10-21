'use client'

import { redirect } from 'next/navigation'

export default function EmailPage() {
    redirect('/dashboard?tab=email')
}
