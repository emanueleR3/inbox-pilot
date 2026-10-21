'use client'

import { useEffect, useState } from 'react'

export function HydrationWrapper({ children }: { children: React.ReactNode }) {
  const [isHydrated, setIsHydrated] = useState(false)

  useEffect(() => {
    // Small delay to ensure smooth transition
    const timer = setTimeout(() => {
      setIsHydrated(true)
    }, 50)
    return () => clearTimeout(timer)
  }, [])

  return (
    <>
      {/* Loading screen - shows immediately, fades out after hydration */}
      <div 
        className={`loading-screen ${isHydrated ? 'hidden' : ''}`}
        aria-hidden={isHydrated}
      />
      
      {/* Page content - starts hidden, fades in after hydration */}
      <div className={`page-content ${isHydrated ? 'hydrated' : ''}`}>
        {children}
      </div>
    </>
  )
}
