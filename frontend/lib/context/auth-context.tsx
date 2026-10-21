'use client'

import React, { createContext, useContext, useState, useCallback, useEffect } from 'react'
import { backendService, type Subscription, type LoginResponse, type SubscriptionServiceInfo } from '@/lib/api/backend-service'

// Auth session - kept in memory, token stored in cookie for session restore
interface AuthSession {
  access_token: string
  user: {
    id: string
    email: string
  }
  subscriptions: Subscription[]
  jwt?: string
  sub_selected: number
}

// Context state
interface AuthState {
  isLoading: boolean
  isAuthenticated: boolean
  session: AuthSession | null
  currentSubscription: Subscription | null
}

// Context actions
interface AuthActions {
  login: (email: string, password: string) => Promise<LoginResponse>
  logout: () => Promise<void>
  selectSubscription: (subscriptionId: string) => void
  refreshUserData: () => Promise<void>
  refreshSubscriptions: () => Promise<void>
  setSessionFromResponse: (response: LoginResponse['result']) => void
  markSubscriptionConfigured: () => void
  addServiceToSubscription: (service: SubscriptionServiceInfo) => void
  updateServiceInSubscription: (serviceId: string, updates: Partial<SubscriptionServiceInfo>) => void
  activeServiceId: string | null
  setActiveServiceId: (serviceId: string | null) => void
}

type AuthContextType = AuthState & AuthActions

const AuthContext = createContext<AuthContextType | undefined>(undefined)

const AUTH_COOKIE_KEY = 'auth_session'
const TOKEN_COOKIE_KEY = 'auth_token'
const SESSION_DATA_KEY = 'auth_data'
const ACTIVE_SERVICE_KEY = 'active_service_id'

// Cookie helpers
function setCookie(name: string, value: string, days: number = 7) {
  if (typeof document === 'undefined') return
  const expires = new Date(Date.now() + days * 24 * 60 * 60 * 1000).toUTCString()
  document.cookie = `${name}=${encodeURIComponent(value)}; path=/; expires=${expires}; SameSite=Lax`
}

function getCookie(name: string): string | null {
  if (typeof document === 'undefined') return null
  const match = document.cookie.match(new RegExp('(^| )' + name + '=([^;]+)'))
  return match ? decodeURIComponent(match[2]) : null
}

function deleteCookie(name: string) {
  if (typeof document === 'undefined') return
  document.cookie = `${name}=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT`
}

// Store session data in cookie
function saveSessionToCookie(session: AuthSession | null) {
  if (session) {
    setCookie(AUTH_COOKIE_KEY, 'true')
    setCookie(TOKEN_COOKIE_KEY, session.access_token)
    setCookie(SESSION_DATA_KEY, JSON.stringify({
      user: session.user,
      subscriptions: session.subscriptions,
      sub_selected: session.sub_selected,
    }))
  } else {
    deleteCookie(AUTH_COOKIE_KEY)
    deleteCookie(TOKEN_COOKIE_KEY)
    deleteCookie(SESSION_DATA_KEY)
  }
}

// Restore session from cookie
function getSessionFromCookie(): AuthSession | null {
  const token = getCookie(TOKEN_COOKIE_KEY)
  const dataStr = getCookie(SESSION_DATA_KEY)
  if (!token || !dataStr) return null
  try {
    const data = JSON.parse(dataStr)
    return {
      access_token: token,
      user: data.user,
      subscriptions: data.subscriptions,
      sub_selected: data.sub_selected,
    }
  } catch {
    return null
  }
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [isLoading, setIsLoading] = useState(true) // Start loading to check session
  const [session, setSession] = useState<AuthSession | null>(null)
  const [activeServiceId, setActiveServiceIdState] = useState<string | null>(() => {
    if (typeof document === 'undefined') return null
    return getCookie(ACTIVE_SERVICE_KEY)
  })

  const setActiveServiceId = useCallback((serviceId: string | null) => {
    setActiveServiceIdState(serviceId)
    if (serviceId) {
      setCookie(ACTIVE_SERVICE_KEY, serviceId)
    } else {
      deleteCookie(ACTIVE_SERVICE_KEY)
    }
  }, [])

  // Update session in memory and cookie (supports functional updates to prevent race conditions)
  const updateSession = useCallback((updater: AuthSession | null | ((prev: AuthSession | null) => AuthSession | null)) => {
    setSession(prev => {
      const newSession = typeof updater === 'function' ? updater(prev) : updater
      saveSessionToCookie(newSession)
      backendService.setAccessToken(newSession?.access_token ?? null)
      backendService.setUserEmail(newSession?.user?.email ?? null)
      return newSession
    })
  }, [])

  // Validate and restore session on mount
  useEffect(() => {
    const validateSession = async () => {
      const storedSession = getSessionFromCookie()

      if (!storedSession) {
        setIsLoading(false)
        return
      }

      // Set token for API calls
      backendService.setAccessToken(storedSession.access_token)
      backendService.setUserEmail(storedSession.user.email)

      try {
        // Validate by fetching user data from server
        const userResponse = await backendService.getUser(storedSession.user.email)

        if (userResponse && userResponse.id) {
          // Valid session - restore it
          setSession(storedSession)
        } else {
          // Invalid - clear and require login
          saveSessionToCookie(null)
          backendService.setAccessToken(null)
          backendService.setUserEmail(null)
        }
      } catch (error) {
        console.error('[Auth] Session validation failed:', error)
        // Clear invalid session
        saveSessionToCookie(null)
        backendService.setAccessToken(null)
        backendService.setUserEmail(null)
      } finally {
        setIsLoading(false)
      }
    }

    validateSession()
  }, [])

  // Set session from API response
  const setSessionFromResponse = useCallback((result: LoginResponse['result']) => {
    const newSession: AuthSession = {
      access_token: result.jwt,
      user: {
        id: result.id,
        email: result.email,
      },
      subscriptions: result.subscriptions,
      sub_selected: result.sub_selected,
    }
    updateSession(newSession)
  }, [updateSession])

  // Login
  const login = useCallback(async (email: string, password: string): Promise<LoginResponse> => {
    setIsLoading(true)
    try {
      const response = await backendService.login({ email, password })
      setSessionFromResponse(response.result)
      return response
    } finally {
      setIsLoading(false)
    }
  }, [setSessionFromResponse])

  // Logout
  const logout = useCallback(async () => {
    try {
      await backendService.logout()
    } catch (error) {
      console.error('[Auth] Logout API error:', error)
    } finally {
      updateSession(null)
    }
  }, [updateSession])

  // Select subscription
  const selectSubscription = useCallback((subscriptionId: string) => {
    if (!session) return

    const index = session.subscriptions.findIndex(s => s.subscription_id === subscriptionId)
    if (index !== -1) {
      const updatedSession: AuthSession = {
        ...session,
        sub_selected: index,
      }
      updateSession(updatedSession)
    }
  }, [session, updateSession])

  // Refresh user data - derive config status from services already in session (from login response)
  const refreshUserData = useCallback(async () => {
    if (!session?.subscriptions) return

    try {
      const updatedSubscriptions = session.subscriptions.map((sub) => {
        const services = sub.services || []
        const isConfigured = services.some(s => {
          if (!s) return false
          const val = s.config_completed
          if (typeof val === 'boolean') return val
          if (typeof val === 'string') return (val as string).toLowerCase() === 'true'
          return false
        })
        return { ...sub, is_configurated: isConfigured }
      })

      const updatedSession: AuthSession = {
        ...session,
        subscriptions: updatedSubscriptions,
      }
      updateSession(updatedSession)
    } catch (error) {
      console.error('[Auth] Failed to refresh user data:', error)
    }
  }, [session, updateSession])

  // Refresh subscriptions from API (fetches fresh data including newly created services)
  // NOTE: /auth/get-subscriptions/{userId} is not implemented in the backend.
  // Subscriptions are returned in the login response instead.
  // This method gracefully handles the 404 by falling back to the existing session data.
  const refreshSubscriptions = useCallback(async () => {
    if (!session?.user?.id) return

    try {
      const subscriptions = await backendService.getSubscriptionsByUserId(session.user.id)
      if (subscriptions && Array.isArray(subscriptions) && subscriptions.length > 0) {
        const updatedSession: AuthSession = {
          ...session,
          subscriptions,
        }
        updateSession(updatedSession)
      }
    } catch {
      // Endpoint not implemented – subscriptions from login response are used instead
    }
  }, [session, updateSession])

  // Mark current subscription as configured
  const markSubscriptionConfigured = useCallback(() => {
    updateSession((prevSession) => {
      if (!prevSession) return prevSession

      const updatedSubscriptions = prevSession.subscriptions.map((sub, index) =>
        index === prevSession.sub_selected
          ? { ...sub, is_configurated: true }
          : sub
      )

      return {
        ...prevSession,
        subscriptions: updatedSubscriptions,
      }
    })
  }, [updateSession])

  // Add a newly created service to the current subscription in session
  const addServiceToSubscription = useCallback((service: SubscriptionServiceInfo) => {
    updateSession((prevSession) => {
      if (!prevSession) return prevSession

      const updatedSubscriptions = prevSession.subscriptions.map((sub, index) =>
        index === prevSession.sub_selected
          ? { ...sub, services: [...(sub.services || []), service] }
          : sub
      )

      return {
        ...prevSession,
        subscriptions: updatedSubscriptions,
      }
    })
  }, [updateSession])

  // Update an existing service in the current subscription
  const updateServiceInSubscription = useCallback((serviceId: string, updates: Partial<SubscriptionServiceInfo>) => {
    updateSession((prevSession) => {
      if (!prevSession) return prevSession

      const updatedSubscriptions = prevSession.subscriptions.map((sub, index) =>
        index === prevSession.sub_selected
          ? {
            ...sub,
            services: (sub.services || []).map(s =>
              s.service_id === serviceId ? { ...s, ...updates } : s
            ),
          }
          : sub
      )

      return {
        ...prevSession,
        subscriptions: updatedSubscriptions,
      }
    })
  }, [updateSession])

  // Computed values
  const isAuthenticated = !!session?.access_token
  const currentSubscription = session
    ? session.subscriptions[session.sub_selected] || null
    : null

  const value: AuthContextType = {
    isLoading,
    isAuthenticated,
    session,
    currentSubscription,
    login,
    logout,
    selectSubscription,
    refreshUserData,
    refreshSubscriptions,
    setSessionFromResponse,
    markSubscriptionConfigured,
    addServiceToSubscription,
    updateServiceInSubscription,
    activeServiceId,
    setActiveServiceId,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

// Helper to normalize is_configurated value (handles boolean or string)
function normalizeIsConfigured(value: boolean | string | undefined): boolean {
  if (typeof value === 'boolean') return value
  if (typeof value === 'string') return value.toLowerCase() === 'true'
  return false
}

// Hook for checking if subscription is configured
export function useSubscriptionConfig() {
  const { currentSubscription } = useAuth()
  return {
    isConfigured: normalizeIsConfigured(currentSubscription?.is_configurated),
    subscriptionId: currentSubscription?.subscription_id,
    subscription: currentSubscription,
  }
}
