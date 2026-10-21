'use client'

import { redirect } from 'next/navigation'

export default function CalendarPage() {
    redirect('/dashboard?tab=calendar')
}
