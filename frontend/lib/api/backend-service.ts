/*
  BackendService: Unified API client for Corretto
  Base URL: process.env.NEXT_PUBLIC_API_URL || 'https://api.corretto.pro'
  Adapted for Next.js from the original Vite implementation
*/

// ---------- Shared Types ----------
export interface Session {
  access_token: string
  refresh_token?: string
  expires_in?: number
  user?: {
    id: string
    email: string
  }
}

export interface ApiMessage {
  message: string
}

export interface ApiErrorShape {
  detail?: string
  message?: string
  status_code?: number
}

// Subscription type used throughout the app
// Service info as returned inside each subscription from login/session endpoints
export interface SubscriptionServiceInfo {
  service_id: string
  email: string
  subscription_id?: string
  email_provider?: string
  calendar_provider?: string
  config_completed?: boolean
  activated?: boolean
  draft?: boolean
  name?: string
}

export interface Subscription {
  subscription_id: string
  name: string
  vat_number?: string
  city: string
  address: string
  active: boolean
  current_period_end: string
  plan?: string
  industry?: string
  // Can be boolean or string "true"/"false" from API
  is_configurated?: boolean | string
  // Services nested from login/session response
  services?: SubscriptionServiceInfo[]
}

// Auth
export interface RegisterRequest {
  email: string
  password: string
  subscription: {
    name: string
    vat_number?: string
    city: string
    address: string
    active: boolean
    current_period_end: string
    plan?: string
    industry?: string
  }
}

export interface RegisterResponse {
  message: string
  result: {
    id: string
    email: string
    subscriptions: Subscription[]
    jwt: string
    sub_selected: number
  }
}

export interface CreateNewSubsRequest {
  user: {
    id: string
    email: string
  }
  jwt: string
  subscription: {
    name: string
    vat_number?: string
    city: string
    address: string
    active: boolean
    current_period_end: string
    plan?: string
    industry?: string
  }
}

export interface CreateNewSubsResponse {
  message: string
  result: {
    id: string
    email: string
    subscriptions: Subscription[]
    jwt: string
    sub_selected: number
  }
}

export interface LoginRequest {
  email: string
  password: string
}

export interface LoginResponse {
  message: string
  result: {
    id: string
    email: string
    subscriptions: Subscription[]
    jwt: string
    sub_selected: number
  }
}

export interface MagicLinkRequest {
  email: string
}

export interface MagicLinkResponse {
  message: string
  success: boolean
}

export interface ResetPasswordRequest {
  email: string
}

export interface ResetPasswordResponse {
  message: string
  success: boolean
}

export type UpdatePasswordRequest =
  | { old_password: string; new_password: string }
  | { access_token: string; new_password: string }

export interface UpdatePasswordResponse {
  message: string
  success: boolean
}

export interface GetUserResponse {
  id: string
  email: string
  subscription?: Subscription
}

export interface GetUserBySubscriptionResponse {
  user_id: string
  email: string
  subscription_id: string
}

// OAuth Configuration
export interface OAuthLoginRequest {
  subscription_id: string
  services: 'all' | 'calendar' | 'mail'
  email: string | null
  service_id?: string | null
}

export interface OAuthLoginResponse {
  success: boolean
  message?: string
  url?: string
}

// Custom Provider Configuration
export interface CustomProviderRequest {
  server_imap: string
  server_smtp: string
  imap_port: number
  smtp_port: number
  email: string
  password: string
  subscription_id: string
  calendar_provider: string
  service_id?: string | null
}

export interface CustomProviderResponse {
  status: "success" | "error"
  message: string
  data?: {
    email: string
    subscription_id: string
    email_provider: string
    imap_server: string
    smtp_server: string
  }
}

// Account Setup Interfaces
export interface EmailConfigRequest {
  provider: 'google' | 'microsoft' | 'custom'
  email?: string
  password?: string
  imap_server?: string
  imap_port?: number
  smtp_server?: string
  smtp_port?: number
}

export interface EmailConfigResponse {
  success: boolean
  message: string
}

export interface Calendar {
  id: string
  name: string
  description?: string
  isPrimary?: boolean
  color?: string
}

export interface GetCalendarsResponse {
  calendars: Calendar[]
}

export interface CreateCalendarRequest {
  provider: 'google' | 'microsoft'
  name: string
  description?: string
  color?: string
}

export interface CreateCalendarResponse {
  calendar: Calendar
}

export interface CalendarSelectionRequest {
  provider: 'google' | 'microsoft' | 'custom'
  calendar_ids: string[]
}

export interface CalendarSelectionResponse {
  success: boolean
  message: string
}

// Calendar Event Types (based on /calendars/events API)
export interface CalendarEventAttendee {
  email: string
  name?: string
  response_status?: 'accepted' | 'declined' | 'tentative' | 'needsAction'
}

export interface CalendarEventOrganizer {
  email: string
  name?: string
}

export interface CalendarEvent {
  id: string
  title: string
  description?: string
  start: string  // ISO 8601 datetime
  end: string    // ISO 8601 datetime
  location?: string
  organizer?: CalendarEventOrganizer
  attendees: CalendarEventAttendee[]
  is_all_day: boolean
  status: 'confirmed' | 'tentative' | 'cancelled'
  html_link?: string
  thread_summary: string  // AI thread summary or "Evento non generato da email gestita da AI"
  created_by_ai?: boolean
}

export interface GetCalendarEventsRequest {
  provider: 'google' | 'microsoft'
  email: string
  time_min?: string  // ISO 8601
  time_max?: string  // ISO 8601
  max_results?: number
  calendar_id?: string
}

export interface CreateCalendarEventRequest {
  provider: 'google' | 'microsoft'
  email: string
  title: string
  start: string  // ISO 8601
  end: string    // ISO 8601
  description?: string
  location?: string
  attendees?: string[]  // list of email addresses
  is_all_day?: boolean
  calendar_id?: string  // default: "primary"
  timezone?: string     // default: "Europe/Rome"
  reminders?: number[]  // minutes before (Google only)
}

export interface CreateCalendarEventResponse {
  success: boolean
  event_id: string
  message: string
  event?: {
    id: string
    title: string
    description?: string
    start: string
    end: string
    location?: string
    is_all_day: boolean
    status: string
  }
}

export interface UpdateCalendarEventRequest {
  provider: 'google' | 'microsoft'
  email: string
  title?: string
  description?: string
  start?: string  // ISO 8601
  end?: string    // ISO 8601
  location?: string
  attendees?: string[]
  is_all_day?: boolean
  calendar_id?: string
  timezone?: string
}

export interface UpdateCalendarEventResponse {
  success: boolean
  event_id: string
  message: string
  event?: {
    id: string
    title: string
    description?: string
    start: string
    end: string
    location?: string
    is_all_day: boolean
    status: string
  }
}

export interface DeleteCalendarEventRequest {
  provider: 'google' | 'microsoft'
  email: string
  calendar_id?: string  // default: "primary"
}

export interface DeleteCalendarEventResponse {
  success: boolean
  event_id: string
  message: string
}

// -------------------- Mailbox / Email Types --------------------
export type EmailThreadStatus = 'OPEN' | 'HUMAN_REVIEW' | 'CLOSED' | 'PENDING'

export interface EmailThreadSummary {
  thread_id: string
  subject: string
  category?: string
  subcategory?: string
  status: EmailThreadStatus
  last_message_at: string  // ISO 8601
  last_sender_email: string
  human_response: boolean
  summary?: string
  email_count: number
  has_attachments: boolean
  max_priority: number  // 0-1 score
}

export interface EmailMessage {
  id: string
  subject: string
  body: string
  direction: 'INBOUND' | 'OUTBOUND'
  outcome?: string  // e.g., 'SENT', 'DRAFT', 'SMTP_ERROR'
  datetime: string  // ISO 8601
  has_attachment: boolean
  ai_generated: boolean
  priority_score?: number
}

export interface EmailThreadDetail {
  thread_id: string
  subject: string
  messages: EmailMessage[]
  message_count: number
}

export interface FailedOutboundEmail {
  email_id: string
  thread_id: string
  datetime: string
  outcome: string  // e.g., 'SMTP_ERROR'
  body: string
}

export interface GetInboxThreadsRequest {
  box_email: string
  status?: EmailThreadStatus
  category?: string
  subcategory?: string
  limit?: number  // default 50
  offset?: number  // default 0
}

export interface SendEmailAttachment {
  filename: string
  content: string  // base64 encoded
  content_type?: string  // MIME type, default: application/octet-stream
}

export interface SendEmailRequest {
  provider: 'google' | 'microsoft'
  email: string  // sender email (authenticated account)
  to: string[]
  subject: string
  body: string
  cc?: string[]
  bcc?: string[]
  reply_to?: string
  is_html?: boolean
  attachments?: SendEmailAttachment[]
}

export interface SendEmailResponse {
  success: boolean
  message_id: string
  message: string
}

// -------------------- Quiz / Onboarding --------------------

export interface QuizQuestion {
  id: string
  text: string
  helper_text?: string
  order: number
}

export type ReasoningStatus = 'pending' | 'in_progress' | 'completed'

export interface ReasoningItem {
  id: string
  text: string
  status: ReasoningStatus
}

export interface BulletItem {
  name: string
  completed: boolean
  info: string | null
}

export interface StartQuizRequest {
  email: string
}

export interface StartQuizResponse {
  session_id: string
  question: string
  bullet_list: BulletItem[]
  phase: string
  turn_count: number
  max_turns: number
  has_context: boolean
  done: boolean
  email?: string
  reasoning_items?: ReasoningItem[]
  estimated_progress?: number
}

export interface AnswerQuizRequest {
  session_id: string
  answer: string
}

export interface AnswerQuizResponse {
  done: boolean
  question?: string
  bullet_list: BulletItem[]
  phase: string
  turn_count: number
  max_turns: number
  extracted_markdown?: string
  error?: string
  reasoning_items?: ReasoningItem[]
  estimated_progress?: number
  save_started?: boolean  // Added: indicates save pipeline started in background
}

// Quiz Save Types
export interface SaveQuizRequest {
  session_id: string
}

export interface SaveQuizResponse {
  started: boolean
  session_id: string
  email: string
  error?: string
}

export interface QuizSaveStatusResponse {
  session_id: string
  email: string
  phase: string
  actual_step: number
  total_steps: number
  started_at?: string
  updated_at?: string
  completed_at?: string
  details?: Record<string, unknown>
  run_id?: string
  worker?: string
  is_running: boolean
  is_completed: boolean
  is_failed: boolean
  save_status: 'idle' | 'running' | 'completed' | 'failed'
  error?: string
}

// Quiz Session (from /sessions endpoint)
export interface QuizSession {
  session_id: string
  service_id: string
  email: string
  status: 'in_progress' | 'completed' | 'failed'
  phase: string
  turn_count: number
  max_turns: number
  created_at: string
  updated_at: string
}

// Quiz Session by Email Response (from /quiz/sessions/{email} endpoint)
export interface QuizSessionByEmailResponse {
  session_id: string
  service_id: string
  phase: string
  business_field?: string
  bullet_list?: string[]
  is_done: boolean
  has_context: boolean
  final_markdown?: string
}

export type QuizResponse = StartQuizResponse | AnswerQuizResponse

export interface StaticQuizRequest {
  email: string
  business_hours?: Record<string, string[]>
  appointment_duration?: number
  email_signature?: string
  tone_of_voice?: string
  phone_numbers?: Record<string, string> | string[]
  draft?: boolean
}

export interface StaticQuizResponse {
  success: boolean
  message: string
  data: {
    email: string
    business_hours?: Record<string, string[]>
    appointment_duration?: number
    email_signature?: string
    tone_of_voice?: string
    phone_numbers?: Record<string, string>
  }
}

export interface UpdateInformationResponse {
  message: string
  success: boolean
}

export interface SetupCalendarInfoResponse {
  message: string
  success: boolean
}

// Frontend-friendly state (camelCase)
export interface QuizState {
  sessionId: string
  phase: string
  turnCount: number
  maxTurns: number
  bulletList: BulletItem[]
  isDone: boolean
  question?: string | null
  finalMarkdown?: string
  error?: string
}

export interface GetQuizStateResponse {
  session_id: string
  service_id?: string
  email?: string
  phase: string
  turn_count: number
  max_turns: number
  bullet_list: BulletItem[]
  messages?: ThreadMessage[]
  is_done: boolean
  has_context: boolean
  final_markdown?: string | null
}

export interface FinishQuizRequest {
  session_id: string
  extracted_markdown?: string
}

export interface FinishQuizResponse {
  done: boolean
  extracted_markdown?: string | null
  bullet_list: BulletItem[]
  error?: string | null
}

export interface SaveQuizMarkdownRequest {
  email: string
  markdown: string
}

export interface SaveQuizMarkdownResponse {
  success: boolean
  message: string
}

export interface UpdateFinalMarkdownRequest {
  session_id: string
  final_markdown: string
}

export interface UpdateFinalMarkdownResponse {
  success: boolean
  message: string
}





// Subscription Service Details
export interface BaseSubscriptionService {
  service_id: string  // UUID of the subscription service
  email: string
  subscription_id?: string
  confidence_response_threshold: number
  confidence_review_mail: number
  priority_threshold: number
  confidence_classification_threshold: number
  urgent_meeting_threshold: number
  config_completed?: boolean
  activated?: boolean
  information?: string
}

export interface GoogleSubscriptionService extends BaseSubscriptionService {
  email_provider: 'google'
  calendar_provider: 'google'
  hashed_access_token: string
  hashed_refresh_token: string
  expiry_token: string
  history_id: string
}

export interface MicrosoftSubscriptionService extends BaseSubscriptionService {
  email_provider: 'microsoft'
  calendar_provider: 'microsoft'
  hashed_access_token: string
  hashed_refresh_token: string
  expiry_token: string
  microsoft_subscription_id_inbound: string
  microsoft_subscription_id_outbound: string
  microsoft_expiration_datetime_inbound: string
  microsoft_expiration_datetime_outbound: string
}

export interface ImapSubscriptionService extends BaseSubscriptionService {
  email_provider: 'imap'
  imap_server: string
  imap_port: number
  smtp_server: string
  smtp_port: number
  hashed_password: string
}

export type SubscriptionService = GoogleSubscriptionService | MicrosoftSubscriptionService | ImapSubscriptionService

export type GetSubscriptionServiceResponse = SubscriptionService[]

// Subscription Configuration
export interface AIConfiguration {
  confidence_response_threshold: number
  confidence_review_mail: number
  priority_threshold: number
  confidence_classification_threshold: number
  urgent_meeting_threshold: number
  draft?: boolean
}

export interface GetConfigResponse {
  status: 'ok' | 'not_found'
  result?: AIConfiguration
}

export interface UpdateConfigResponse {
  status: 'ok'
  result: AIConfiguration
}

// Service Settings (business_hours, phone_numbers, etc.)
export interface ServiceSettings {
  business_hours?: Record<string, string[]>
  appointment_duration?: number
  email_signature?: string
  tone_of_voice?: string
  phone_numbers?: string[] | Record<string, string>
}

export type GetServiceSettingsResponse = ServiceSettings

export type UpdateServiceSettingsResponse = ServiceSettings

// Subscription Details (full subscription record)
export interface SubscriptionDetails {
  subscription_id: string
  name: string
  vat_number?: string
  city?: string
  address?: string
  active: boolean
  current_period_end?: string
  plan?: string
  website?: string
  industry?: string
  employee_count?: number
  products_service?: string
  tone_of_voice?: string
  signature?: string
  phone_number?: string
}

export interface UpdateSubscriptionPayload {
  name?: string
  vat_number?: string
  city?: string
  address?: string
  active?: boolean
  current_period_end?: string
  plan?: string
  website?: string
  industry?: string
  employee_count?: number
  products_service?: string
  tone_of_voice?: string
  signature?: string
  phone_number?: string
}

// -------------------- Metrics APIs --------------------

export interface MetricsMetadata {
  date_from: string
  date_to: string
  subscription_id: string
}

// Overview Metrics (KPI cards)
export interface OverviewMetricsResponse {
  ticket_total: number
  ticket_automatizzati: number
  deflection_rate_pct: number
  avg_response_time_seconds: number
  alert_attivi: number
  metadata: MetricsMetadata
}

// Automation Metrics
export interface AIvsHuman {
  human_response: boolean
  count: number
}

export interface DeflectionTrend {
  day: string
  deflection_pct: number
}

export interface DeflectionByCategory {
  category: string
  deflection_pct: number
}

export interface AutomationMetricsResponse {
  ai_vs_human: AIvsHuman[]
  deflection_trend: DeflectionTrend[]
  deflection_by_category: DeflectionByCategory[]
  metadata: MetricsMetadata
}

// AI Quality Metrics
export interface OutcomeDistribution {
  outcome: string
  count: number
}

export interface AvgScoreByOutcome {
  outcome: string
  avg_score: number
}

export interface AIQualityMetricsResponse {
  outcome_distribution: OutcomeDistribution[]
  success_rate_pct: number
  pct_negative_feedback: number
  avg_score_by_outcome: AvgScoreByOutcome[]
  metadata: MetricsMetadata
}

// Risk Metrics
export interface TicketCritico {
  thread_id: string
  priority_score: number
  processed_at: string
}

export interface RiskMetricsResponse {
  num_ticket_critici: number
  ticket_critici_list: TicketCritico[]
  priority_alerts: TicketCritico[]
  avg_time_to_first_ai_seconds: number
  metadata: MetricsMetadata
}

// Usage Metrics
export interface EmailPerDay {
  day: string
  count: number
}

export interface ThreadsPerCategory {
  category: string
  count: number
}

export interface UsageMetricsResponse {
  email_processate: number
  email_per_giorno: EmailPerDay[]
  total_minutes_processed: number
  thread_attivi: number
  threads_per_category: ThreadsPerCategory[]
  attachments: { count: number }
  metadata: MetricsMetadata
}

// Events/Calendar Metrics
export interface EventsPerType {
  event_type: string
  count: number
}

export interface EventsTrend {
  day: string
  count: number
}

export interface EventsMetricsResponse {
  totale_eventi: number
  eventi_creati_ai: number
  eventi_creati_umano: number
  ai_pct: number
  eventi_per_tipo: EventsPerType[]
  trend: EventsTrend[]
  metadata: MetricsMetadata
}

// -------------------- Jerry Chatbot APIs --------------------
export interface CreateThreadRequest {
  user_id: string
}

export interface CreateThreadResponse {
  thread_id: string
}

export interface SendMessageRequest {
  user_id: string
  message: string
  thread_id?: string
}

export interface SendMessageResponse {
  thread_id: string
  response: string
}

export interface StreamMessageRequest {
  user_id: string
  message: string
  thread_id?: string
}

export interface StreamMessageChunk {
  type?: string
  content?: string
  error?: string
  thread_id?: string
  [key: string]: unknown
}

export interface ThreadMessage {
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp?: string
}

export interface GetThreadHistoryResponse {
  messages: ThreadMessage[]
}

export interface DeleteThreadResponse {
  message: string
  success: boolean
}

export interface ExecuteToolRequest {
  tool_name: string
  tool_params: Record<string, unknown>
  thread_id?: string
  user_id?: string
}

export interface ExecuteToolResponse {
  result: unknown
  success: boolean
}

export interface Tool {
  name: string
  description: string
  parameters?: Record<string, unknown>
}

export interface GetAvailableToolsResponse {
  tools: Tool[]
}

// -------------------- Scraper APIs --------------------
export interface DiscoverUrlsRequest {
  website_url: string
  max_urls?: number
}

export interface DiscoverUrlsResponse {
  website_url: string
  urls: string[]
  count: number
}

export interface CalendarBusinessHours {
  [key: string]: string[]
}

export interface SetupCalendarInfoRequest {
  email?: string
  business_hours: CalendarBusinessHours
  appointment_duration: number
}

export interface GetCalendarInfoResponse {
  message: string
  result: {
    business_hours: CalendarBusinessHours
    appointment_duration: number
    email_signature?: string
    tone_of_voice?: string
    phone_numbers?: Record<string, string>
  } | string
}

export interface StartScrapingRequest {
  email: string
  website_url: string
  urls: string[]
}

export interface StartScrapingResponse {
  message: string
  email: string
  collection_name: string
  status: string
}

export interface ScrapingStatusResponse {
  status: 'started' | 'processing' | 'completed' | 'failed'
  website_url?: string
  collection_name?: string
  progress?: {
    step: string
    current_url?: string
    pages_scraped?: number
    chunks_created?: number
    chunks_cleaned?: number
    chunks_embedded?: number
    chunks_uploaded?: number
  }
  error?: string | null
}

export interface CollectionStatusResponse {
  collection_name: string
  exists: boolean
  info?: {
    name: string
    points_count: number
    vectors_count: number
    status: string
  } | null
}

export interface DeleteCollectionResponse {
  message: string
  collection_name: string
}

// -------------------- Notifications --------------------

export interface AppNotification {
  notification_id: string
  text: string
  type: string
  email: string
  email_id?: string
  view: boolean
  email_body?: string
  email_datetime?: string
  email_message_id?: string
  email_outcome?: string
  email_direction?: string
  email_has_attachment?: boolean
}

export interface GetNotificationsResponse {
  notifications: AppNotification[]
  total: number
}

export interface MarkNotificationReadResponse {
  success: boolean
  message: string
  notification_id: string
  view: boolean
}

export class BackendService {
  private baseUrl: string
  private accessToken: string | null = null
  private userEmail: string | null = null

  constructor(baseUrl?: string) {
    this.baseUrl = (baseUrl || process.env.NEXT_PUBLIC_API_URL || 'https://api.corretto.pro').replace(/\/$/, '')
  }

  // Set the access token (called after login)
  setAccessToken(token: string | null) {
    this.accessToken = token
  }

  // Set the user email (called after login)
  setUserEmail(email: string | null) {
    this.userEmail = email
  }

  private getCurrentUserEmail(): string | undefined {
    return this.userEmail || undefined
  }

  private getAuthHeaders(): Record<string, string> {
    return this.accessToken ? { Authorization: `Bearer ${this.accessToken}` } : {}
  }

  private async handleResponse<T>(response: Response, path: string): Promise<T> {
    if (!response.ok) {
      let msg = response.statusText
      try {
        const data = (await response.json()) as ApiErrorShape
        msg = data.detail || data.message || msg
      } catch {
        // ignore parse error
      }
      console.error(`[BackendService] Error ${response.status} on ${path}:`, msg)
      throw new Error(msg)
    }

    const text = await response.text()
    if (!text) return undefined as unknown as T
    try {
      return JSON.parse(text) as T
    } catch {
      return text as unknown as T
    }
  }

  private async request<T>(path: string, init: RequestInit = {}): Promise<T> {
    const url = `${this.baseUrl}${path}`
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      ...this.getAuthHeaders(),
      ...(init.headers || {}),
    }
    const res = await fetch(url, { ...init, headers })
    return this.handleResponse<T>(res, path)
  }

  // -------------------- Auth APIs --------------------

  async oauthLogin(provider: 'google' | 'microsoft', subscriptionId: string, services: 'all' | 'calendar' | 'mail', email: string | null, serviceId?: string | null): Promise<OAuthLoginResponse> {
    const payload: OAuthLoginRequest = { subscription_id: subscriptionId, services, email, service_id: serviceId || null }
    const response = await this.request<OAuthLoginResponse>(`/auth/oauth/login/${provider}`, {
      method: 'POST',
      body: JSON.stringify(payload)
    })
    return response
  }

  async customProviderLogin(data: CustomProviderRequest): Promise<CustomProviderResponse> {
    const response = await this.request<CustomProviderResponse>('/auth/custom-provider/login', {
      method: 'POST',
      body: JSON.stringify(data)
    })
    return response
  }

  async getUser(email: string): Promise<GetUserResponse> {
    const response = await this.request<GetUserResponse>(`/auth/get-user/${encodeURIComponent(email)}`, { method: 'GET' })
    return response
  }

  async getUserBySubscription(subscriptionId: string): Promise<GetUserBySubscriptionResponse> {
    const response = await this.request<GetUserBySubscriptionResponse>(`/auth/get-user-by-subscription/${encodeURIComponent(subscriptionId)}`, { method: 'GET' })
    return response
  }

  /**
   * NOTE: This endpoint is not yet implemented in the backend.
   * Subscriptions are returned in the login response instead.
   * Use the subscriptions from the session/login response.
   */
  async getSubscriptionsByUserId(userId: string): Promise<Subscription[]> {
    const response = await this.request<Subscription[]>(`/auth/get-subscriptions/${encodeURIComponent(userId)}`, { method: 'GET' })
    return response
  }

  async createAccount(payload: RegisterRequest): Promise<RegisterResponse> {
    const response = await this.request<RegisterResponse>('/auth/create-account', { method: 'POST', body: JSON.stringify(payload) })
    return response
  }

  async createNewSubscription(payload: CreateNewSubsRequest): Promise<CreateNewSubsResponse> {
    const response = await this.request<CreateNewSubsResponse>('/auth/create-new-subs', { method: 'POST', body: JSON.stringify(payload) })
    return response
  }

  async login(payload: LoginRequest): Promise<LoginResponse> {
    const response = await this.request<LoginResponse>('/auth/login', { method: 'POST', body: JSON.stringify(payload) })
    return response
  }

  async sendMagicLink(payload: MagicLinkRequest): Promise<MagicLinkResponse> {
    const response = await this.request<MagicLinkResponse>('/auth/magic-link', { method: 'POST', body: JSON.stringify(payload) })
    return response
  }

  // -------------------- Quiz Methods --------------------

  async startQuiz(payload: StartQuizRequest): Promise<QuizResponse> {
    const response = await this.request<QuizResponse>('/subscriptionServiceRouter/quiz/start', {
      method: 'POST',
      body: JSON.stringify(payload)
    })
    return response
  }

  async answerQuiz(payload: AnswerQuizRequest): Promise<QuizResponse> {
    const response = await this.request<QuizResponse>('/subscriptionServiceRouter/quiz/answer', {
      method: 'POST',
      body: JSON.stringify(payload)
    })
    return response
  }

  async getQuizState(sessionId: string): Promise<GetQuizStateResponse> {
    const response = await this.request<GetQuizStateResponse>(`/subscriptionServiceRouter/quiz/${encodeURIComponent(sessionId)}/state`, {
      method: 'GET'
    })
    return response
  }

  async getQuizSessions(): Promise<QuizSession[]> {
    const response = await this.request<QuizSession[]>('/subscriptionServiceRouter/quiz/sessions', {
      method: 'GET'
    })
    return response
  }

  async getQuizSessionByEmail(email: string): Promise<QuizSessionByEmailResponse | null> {
    try {
      const response = await this.request<QuizSessionByEmailResponse>(
        `/subscriptionServiceRouter/quiz/sessions/${encodeURIComponent(email)}`,
        { method: 'GET' }
      )
      return response
    } catch (error) {
      // 404 means no session found for this email - this is expected
      return null
    }
  }

  async updateStaticQuiz(payload: StaticQuizRequest): Promise<StaticQuizResponse> {
    const response = await this.request<StaticQuizResponse>('/subscriptionServiceRouter/static-quiz', {
      method: 'POST',
      body: JSON.stringify(payload)
    })
    return response
  }

  async updateFinalMarkdown(payload: UpdateFinalMarkdownRequest): Promise<UpdateFinalMarkdownResponse> {
    const response = await this.request<UpdateFinalMarkdownResponse>('/quiz/update-final-markdown', {
      method: 'PATCH',
      body: JSON.stringify(payload)
    })
    return response
  }

  async saveQuiz(payload: SaveQuizRequest): Promise<SaveQuizResponse> {
    const response = await this.request<SaveQuizResponse>('/subscriptionServiceRouter/quiz/save', {
      method: 'POST',
      body: JSON.stringify(payload)
    })
    return response
  }

  async getQuizSaveStatus(sessionId: string, email: string): Promise<QuizSaveStatusResponse> {
    const params = new URLSearchParams({ session_id: sessionId, email })
    const response = await this.request<QuizSaveStatusResponse>(
      `/subscriptionServiceRouter/quiz/save-status?${params.toString()}`,
      { method: 'GET' }
    )
    return response
  }

  async resetPassword(payload: ResetPasswordRequest): Promise<ResetPasswordResponse> {
    const response = await this.request<ResetPasswordResponse>('/auth/reset-password', { method: 'POST', body: JSON.stringify(payload) })
    return response
  }

  async updatePassword(payload: UpdatePasswordRequest): Promise<UpdatePasswordResponse> {
    const response = await this.request<UpdatePasswordResponse>('/auth/update-password', { method: 'POST', body: JSON.stringify(payload) })
    return response
  }

  async logout(): Promise<ApiMessage> {
    const response = await this.request<ApiMessage>('/auth/logout', { method: 'POST' })
    return response
  }

  async deleteUser(userId: string): Promise<ApiMessage> {
    const response = await this.request<ApiMessage>(`/auth/delete/${encodeURIComponent(userId)}`, { method: 'DELETE' })
    return response
  }



  // -------------------- Subscription Service --------------------

  async getConfiguration(subscriptionId: string): Promise<GetConfigResponse> {
    const response = await this.request<GetConfigResponse>(`/subscriptionServiceRouter/get-config/${encodeURIComponent(subscriptionId)}`, { method: 'GET' })
    return response
  }

  async updateConfiguration(subscriptionId: string, payload: Partial<AIConfiguration>): Promise<UpdateConfigResponse> {
    const response = await this.request<UpdateConfigResponse>(`/subscriptionServiceRouter/update-config/${encodeURIComponent(subscriptionId)}`, { method: 'PATCH', body: JSON.stringify(payload) })
    return response
  }

  async getSubscriptionService(subscriptionId: string): Promise<GetSubscriptionServiceResponse> {
    const response = await this.request<GetSubscriptionServiceResponse>(`/subscriptionServiceRouter/get_subscription_service/${encodeURIComponent(subscriptionId)}`, { method: 'GET' })
    return response
  }

  async createNewService(subscriptionId: string, name: string): Promise<{ success: boolean; service: SubscriptionServiceInfo }> {
    const response = await this.request<{ success: boolean; service: SubscriptionServiceInfo }>('/subscriptionServiceRouter/create-new-service', {
      method: 'POST',
      body: JSON.stringify({ subscription_id: subscriptionId, name })
    })
    return response
  }

  // -------------------- Service Settings APIs --------------------

  async getServiceSettings(email: string): Promise<GetServiceSettingsResponse> {
    const response = await this.request<GetServiceSettingsResponse>(`/subscriptionServiceRouter/service-settings/${encodeURIComponent(email)}`, { method: 'GET' })
    return response
  }

  async updateServiceSettings(email: string, payload: Partial<ServiceSettings>): Promise<UpdateServiceSettingsResponse> {
    const response = await this.request<UpdateServiceSettingsResponse>(`/subscriptionServiceRouter/service-settings/${encodeURIComponent(email)}`, {
      method: 'PATCH',
      body: JSON.stringify(payload)
    })
    return response
  }

  // -------------------- Subscription APIs --------------------

  async getSubscriptionById(subscriptionId: string): Promise<SubscriptionDetails> {
    const response = await this.request<SubscriptionDetails>(`/subscription/${encodeURIComponent(subscriptionId)}`, { method: 'GET' })
    return response
  }

  async updateSubscription(subscriptionId: string, payload: UpdateSubscriptionPayload): Promise<SubscriptionDetails> {
    const response = await this.request<SubscriptionDetails>(`/subscription/${encodeURIComponent(subscriptionId)}`, {
      method: 'PATCH',
      body: JSON.stringify(payload)
    })
    return response
  }


  // -------------------- Metrics APIs --------------------

  async getOverviewMetrics(serviceId: string, dateFrom?: string, dateTo?: string): Promise<OverviewMetricsResponse> {
    const params = new URLSearchParams()
    if (dateFrom) params.append('date_from', dateFrom)
    if (dateTo) params.append('date_to', dateTo)
    const queryString = params.toString() ? `?${params.toString()}` : ''
    const response = await this.request<OverviewMetricsResponse>(
      `/metric/overview/${encodeURIComponent(serviceId)}${queryString}`,
      { method: 'GET' }
    )
    return response
  }

  async getAutomationMetrics(serviceId: string, dateFrom?: string, dateTo?: string): Promise<AutomationMetricsResponse> {
    const params = new URLSearchParams()
    if (dateFrom) params.append('date_from', dateFrom)
    if (dateTo) params.append('date_to', dateTo)
    const queryString = params.toString() ? `?${params.toString()}` : ''
    const response = await this.request<AutomationMetricsResponse>(
      `/metric/automation/${encodeURIComponent(serviceId)}${queryString}`,
      { method: 'GET' }
    )
    return response
  }

  async getAIQualityMetrics(serviceId: string, dateFrom?: string, dateTo?: string): Promise<AIQualityMetricsResponse> {
    const params = new URLSearchParams()
    if (dateFrom) params.append('date_from', dateFrom)
    if (dateTo) params.append('date_to', dateTo)
    const queryString = params.toString() ? `?${params.toString()}` : ''
    const response = await this.request<AIQualityMetricsResponse>(
      `/metric/ai-quality/${encodeURIComponent(serviceId)}${queryString}`,
      { method: 'GET' }
    )
    return response
  }

  async getRiskMetrics(serviceId: string, dateFrom?: string, dateTo?: string): Promise<RiskMetricsResponse> {
    const params = new URLSearchParams()
    if (dateFrom) params.append('date_from', dateFrom)
    if (dateTo) params.append('date_to', dateTo)
    const queryString = params.toString() ? `?${params.toString()}` : ''
    const response = await this.request<RiskMetricsResponse>(
      `/metric/risk/${encodeURIComponent(serviceId)}${queryString}`,
      { method: 'GET' }
    )
    return response
  }

  async getUsageMetrics(serviceId: string, dateFrom?: string, dateTo?: string): Promise<UsageMetricsResponse> {
    const params = new URLSearchParams()
    if (dateFrom) params.append('date_from', dateFrom)
    if (dateTo) params.append('date_to', dateTo)
    const queryString = params.toString() ? `?${params.toString()}` : ''
    const response = await this.request<UsageMetricsResponse>(
      `/metric/usage/${encodeURIComponent(serviceId)}${queryString}`,
      { method: 'GET' }
    )
    return response
  }

  async getEventsMetrics(serviceId: string, dateFrom?: string, dateTo?: string): Promise<EventsMetricsResponse> {
    const params = new URLSearchParams()
    if (dateFrom) params.append('date_from', dateFrom)
    if (dateTo) params.append('date_to', dateTo)
    const queryString = params.toString() ? `?${params.toString()}` : ''
    const response = await this.request<EventsMetricsResponse>(
      `/metric/events/${encodeURIComponent(serviceId)}${queryString}`,
      { method: 'GET' }
    )
    return response
  }

  // -------------------- Health --------------------

  health(): Promise<{ status?: string;[k: string]: unknown }> {
    return this.request('/health', { method: 'GET' })
  }

  // -------------------- Jerry Chatbot APIs --------------------

  createThread(userId: string): Promise<CreateThreadResponse> {
    const payload: CreateThreadRequest = { user_id: userId }
    return this.request('/jerry/thread/create', {
      method: 'POST',
      body: JSON.stringify(payload)
    })
  }

  sendMessage(userId: string, message: string, threadId?: string): Promise<SendMessageResponse> {
    const payload: SendMessageRequest = { user_id: userId, message, thread_id: threadId }
    return this.request('/jerry/message', {
      method: 'POST',
      body: JSON.stringify(payload)
    })
  }

  async * streamMessage(userId: string, message: string, threadId?: string): AsyncGenerator<StreamMessageChunk> {
    const payload: StreamMessageRequest = { user_id: userId, message, thread_id: threadId }
    const url = `${this.baseUrl}/jerry/message`
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      ...this.getAuthHeaders(),
    }

    const response = await fetch(url, {
      method: 'POST',
      headers,
      body: JSON.stringify(payload)
    })

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      throw new Error(errorData.detail || `HTTP error! status: ${response.status}`)
    }

    const contentType = response.headers.get('content-type') || ''

    // Check if response is SSE stream or regular JSON
    if (contentType.includes('text/event-stream')) {
      // Handle SSE streaming response
      const reader = response.body?.getReader()
      if (!reader) {
        throw new Error('Response body is not readable')
      }

      const decoder = new TextDecoder()
      let buffer = ''

      try {
        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          buffer += decoder.decode(value, { stream: true })
          const lines = buffer.split('\n')
          buffer = lines.pop() || ''

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const data = line.slice(6)
              if (data.trim()) {
                try {
                  const parsed = JSON.parse(data) as StreamMessageChunk
                  yield parsed
                } catch (e) {
                  console.error('Failed to parse SSE data:', data, e)
                }
              }
            }
          }
        }
      } finally {
        reader.releaseLock()
      }
    } else {
      // Handle regular JSON response (non-streaming)
      const data = await response.json()
      // Yield the complete response as a single chunk
      yield {
        thread_id: data.thread_id,
        content: data.response || data.content || '',
      }
    }
  }

  getThreadHistory(threadId: string): Promise<GetThreadHistoryResponse> {
    return this.request(`/jerry/thread/${encodeURIComponent(threadId)}/history`, {
      method: 'GET'
    })
  }

  deleteThread(threadId: string): Promise<DeleteThreadResponse> {
    return this.request(`/jerry/thread/${encodeURIComponent(threadId)}`, {
      method: 'DELETE'
    })
  }

  executeTool(toolName: string, toolParams: Record<string, unknown>, threadId?: string, userId?: string): Promise<ExecuteToolResponse> {
    const payload: ExecuteToolRequest = {
      tool_name: toolName,
      tool_params: toolParams,
      thread_id: threadId,
      user_id: userId
    }
    return this.request('/jerry/tool/execute', {
      method: 'POST',
      body: JSON.stringify(payload)
    })
  }

  getAvailableTools(): Promise<GetAvailableToolsResponse> {
    return this.request('/jerry/tools', {
      method: 'GET'
    })
  }

  // -------------------- Scraper APIs --------------------

  // -------------------- Scraper Methods --------------------

  async discoverUrls(websiteUrl: string, maxUrls: number = 200): Promise<DiscoverUrlsResponse> {
    const payload: DiscoverUrlsRequest = { website_url: websiteUrl, max_urls: maxUrls }
    const response = await this.request<DiscoverUrlsResponse>('/scraper/research', {
      method: 'POST',
      body: JSON.stringify(payload)
    })
    return response
  }

  async startScraping(payload: StartScrapingRequest): Promise<StartScrapingResponse> {
    const response = await this.request<StartScrapingResponse>('/scraper/start', { method: 'POST', body: JSON.stringify(payload) })
    return response
  }

  async getScrapingStatus(email: string): Promise<ScrapingStatusResponse> {
    const response = await this.request<ScrapingStatusResponse>(`/scraper/status/${encodeURIComponent(email)}`, {
      method: 'GET'
    })
    return response
  }

  async getCollectionStatus(email: string): Promise<CollectionStatusResponse> {
    const response = await this.request<CollectionStatusResponse>(`/scraper/collection/${encodeURIComponent(email)}`, {
      method: 'GET'
    })
    return response
  }



  async updateInformation(email: string, content: string, subscriptionId?: string): Promise<UpdateInformationResponse> {
    // Determine the URL based on the parameters
    let url = `/subscriptionServiceRouter/information/${encodeURIComponent(email)}`
    if (subscriptionId) {
      url += `?subscription_id=${encodeURIComponent(subscriptionId)}`
    }

    // The content is a JSON-stringified string as per OpenAPI definition type: string
    const response = await this.request<UpdateInformationResponse>(url, {
      method: 'PATCH',
      body: JSON.stringify(content)
    })
    return response
  }

  async setupCalendarInformation(payload: SetupCalendarInfoRequest): Promise<SetupCalendarInfoResponse> {
    const response = await this.request<SetupCalendarInfoResponse>('/subscriptionServiceRouter/setup-calendar-information', {
      method: 'POST',
      body: JSON.stringify(payload)
    })
    return response
  }


  async getCalendarInformation(): Promise<GetCalendarInfoResponse> {
    const response = await this.request<GetCalendarInfoResponse>('/subscriptionServiceRouter/get-calendar-information', {
      method: 'GET'
    })
    return response
  }

  async getCalendarEvents(payload: GetCalendarEventsRequest): Promise<CalendarEvent[]> {
    const response = await this.request<CalendarEvent[]>('/calendars/events', {
      method: 'POST',
      body: JSON.stringify(payload)
    })
    return response
  }

  async createCalendarEvent(payload: CreateCalendarEventRequest): Promise<CreateCalendarEventResponse> {
    const response = await this.request<CreateCalendarEventResponse>('/calendars/events/create', {
      method: 'POST',
      body: JSON.stringify(payload)
    })
    return response
  }

  async updateCalendarEvent(eventId: string, payload: UpdateCalendarEventRequest): Promise<UpdateCalendarEventResponse> {
    const response = await this.request<UpdateCalendarEventResponse>(`/calendars/events/${encodeURIComponent(eventId)}`, {
      method: 'PATCH',
      body: JSON.stringify(payload)
    })
    return response
  }

  async deleteCalendarEvent(eventId: string, payload: DeleteCalendarEventRequest): Promise<DeleteCalendarEventResponse> {
    const response = await this.request<DeleteCalendarEventResponse>(`/calendars/events/${encodeURIComponent(eventId)}`, {
      method: 'DELETE',
      body: JSON.stringify(payload)
    })
    return response
  }

  async deleteCollection(email: string): Promise<DeleteCollectionResponse> {
    const response = await this.request<DeleteCollectionResponse>(`/scraper/collection/${encodeURIComponent(email)}`, {
      method: 'DELETE'
    })
    return response
  }

  // -------------------- Mailbox APIs --------------------

  async getInboxThreads(payload: GetInboxThreadsRequest): Promise<EmailThreadSummary[]> {
    const response = await this.request<EmailThreadSummary[]>('/mailbox/threads/inbox', {
      method: 'POST',
      body: JSON.stringify(payload)
    })
    return response
  }

  async getHumanReviewThreads(email: string, limit: number = 50, offset: number = 0): Promise<EmailThreadSummary[]> {
    const params = new URLSearchParams()
    params.append('email', email)
    params.append('limit', limit.toString())
    params.append('offset', offset.toString())
    const response = await this.request<EmailThreadSummary[]>(`/mailbox/threads/human-review?${params.toString()}`, {
      method: 'GET'
    })
    return response
  }

  async getThreadConversation(threadId: string): Promise<EmailThreadDetail> {
    const response = await this.request<EmailThreadDetail>(`/mailbox/threads/${encodeURIComponent(threadId)}`, {
      method: 'GET'
    })
    return response
  }

  async getFailedOutboundEmails(serviceId: string): Promise<FailedOutboundEmail[]> {
    const response = await this.request<FailedOutboundEmail[]>(`/mailbox/emails/outbound/failed/${encodeURIComponent(serviceId)}`, {
      method: 'GET'
    })
    return response
  }

  async getThreadsByCategory(category: string, subcategory?: string): Promise<EmailThreadSummary[]> {
    const params = new URLSearchParams()
    params.append('category', category)
    if (subcategory) {
      params.append('subcategory', subcategory)
    }
    const response = await this.request<EmailThreadSummary[]>(`/mailbox/threads/by-category?${params.toString()}`, {
      method: 'GET'
    })
    return response
  }

  async sendEmail(payload: SendEmailRequest): Promise<SendEmailResponse> {
    const response = await this.request<SendEmailResponse>('/mailbox/send', {
      method: 'POST',
      body: JSON.stringify(payload)
    })
    return response
  }

  // ── Attachments ──────────────────────────────────────────────

  private async requestBlob(path: string, init: RequestInit = {}): Promise<Blob> {
    const url = `${this.baseUrl}${path}`
    const headers: HeadersInit = {
      ...this.getAuthHeaders(),
      ...(init.headers || {}),
    }
    const res = await fetch(url, { ...init, headers })
    if (!res.ok) {
      throw new Error(`Failed to fetch blob: ${res.status} ${res.statusText}`)
    }
    return res.blob()
  }

  // ── Attachments ──────────────────────────────────────────────

  async getAttachments(serviceId: string, limit = 50, offset = 0): Promise<GetAttachmentsResponse> {
    const params = new URLSearchParams()
    params.append('service_id', serviceId)
    params.append('limit', limit.toString())
    params.append('offset', offset.toString())
    return this.request<GetAttachmentsResponse>(`/attachments/?${params.toString()}`, {
      method: 'GET'
    })
  }

  async getAttachmentsByReceiver(receiver: string, serviceId: string, limit = 50, offset = 0): Promise<GetAttachmentsByReceiverResponse> {
    const params = new URLSearchParams()
    params.append('service_id', serviceId)
    params.append('limit', limit.toString())
    params.append('offset', offset.toString())
    return this.request<GetAttachmentsByReceiverResponse>(`/attachments/receiver/${encodeURIComponent(receiver)}?${params.toString()}`, {
      method: 'GET'
    })
  }

  async getNotifications(email: string): Promise<GetNotificationsResponse> {
    return this.request<GetNotificationsResponse>(`/notification/retrieve/${encodeURIComponent(email)}`, {
      method: 'GET'
    })
  }

  async markNotificationRead(notificationId: string): Promise<MarkNotificationReadResponse> {
    return this.request<MarkNotificationReadResponse>(`/notification/setTrue/${encodeURIComponent(notificationId)}`, {
      method: 'PATCH'
    })
  }

  async getAttachmentPreview(attachmentId: string): Promise<Blob> {
    return this.requestBlob(`/attachments/${encodeURIComponent(attachmentId)}/preview`, {
      method: 'GET'
    })
  }

  async downloadAttachment(attachmentId: string): Promise<Blob> {
    return this.requestBlob(`/attachments/${encodeURIComponent(attachmentId)}/download`, {
      method: 'GET'
    })
  }
}

// ── Attachment Types ──────────────────────────────────────────

export interface AttachmentEmailContext {
  subject: string
  sender_email: string
  cc_emails?: string[]
  summary: string
  category: string
  subcategory: string
  started_at: string
  last_message_at: string
  available: boolean
}

export interface Attachment {
  attachment_id: string
  thread_id: string
  email_id: string
  sender: string
  receiver: string
  cc?: string[]
  file_name: string
  mime_type: string
  size_bytes: number
  created_at: string
  service_id: string
  email_context?: AttachmentEmailContext
}

export interface ReceiverGroup {
  receiver: string
  count: number
  attachments: Attachment[]
}

export interface GetAttachmentsResponse {
  grouped_by_receiver: ReceiverGroup[]
  unique_formats: string[]
  total_receivers: number
  total_attachments: number
  limit: number
  offset: number
}

export interface GetAttachmentsByReceiverResponse {
  receiver: string
  attachments: Attachment[]
  unique_formats: string[]
  total: number
  limit: number
  offset: number
}

// Export a default singleton instance
export const backendService = new BackendService()
export default BackendService
