# Setup Workflow — Complete API Call Map

This document describes **every API call** made during the setup flow, in execution order, with exact arguments and their sources.

---

## Phase 0: Initialization (`setup-context.tsx` → `refreshSetupState`)

Runs automatically when the setup page loads.

### Call 1 — Get existing services

```
GET /subscriptionServiceRouter/get_subscription_service/{subscription_id}
```

| Argument | Source |
|---|---|
| `subscription_id` | `currentSubscription.subscription_id` (from login response, stored in auth context cookie) |

**Returns:** `SubscriptionService[]` — array of services. Each includes `service_id`, `email`, `email_provider`, `calendar_provider`, `config_completed`, etc.

**What it does:** Determines which setup steps are already complete. Stores `service_id` in the setup context for later use by step components.

### Call 2 — Check website scraping status (conditional)

```
GET /scraper/collection/{email}
```

| Argument | Source |
|---|---|
| `email` | `services[0].email` — from the response of Call 1 |

**Only called if:** Call 1 returned a service with a valid, non-null email.

**Returns:** `{ exists: boolean, info: { points_count, vectors_count, status } }`

**What it does:** If `exists === true`, marks the "website" step as completed.

---

## Phase 1: Email Step (`step-email.tsx`)

The user chooses a provider (Google, Microsoft, or Custom IMAP).

### Path A: Google / Microsoft OAuth

#### Call 3A — Resolve `service_id` (conditional)

If `serviceId` from setup context and `currentSubscription.services[0].service_id` are both null:

```
GET /subscriptionServiceRouter/get_subscription_service/{subscription_id}
```

| Argument | Source |
|---|---|
| `subscription_id` | `currentSubscription.subscription_id` |

**Returns:** `SubscriptionService[]` — uses `services[0].service_id`

#### Call 4A — Start OAuth flow

```
POST /auth/oauth/login/{provider_name}
```

| Argument | Value | Source |
|---|---|---|
| `provider_name` (URL path) | `"google"` or `"microsoft"` | User selection in UI |
| `subscription_id` | UUID string | `currentSubscription.subscription_id` (auth context) |
| `services` | `"all"` or `"mail"` | Hardcoded based on provider selection logic |
| `email` | email string or `null` | `connectedEmail` from setup context (null on first run) |
| `service_id` | UUID string | Resolved via `resolveServiceId()` — tries: (1) `serviceId` from setup context, (2) `currentSubscription.services[0].service_id`, (3) API call above |

**Returns:** `{ success: boolean, url: string }` — the `url` is the OAuth consent screen URL.

**What happens next:** Frontend opens a popup to the returned `url`. After the user authenticates with Google/Microsoft, the backend handles the callback (`/auth/google/callback` or `/auth/microsoft/callback`) and posts a message back to the frontend via `window.postMessage`.

### Path B: Custom IMAP

#### Call 3B — Resolve `service_id` (same logic as 3A)

#### Call 4B — Custom provider login

```
POST /auth/custom-provider/login
```

| Argument | Value | Source |
|---|---|---|
| `server_imap` | e.g. `"imap.example.com"` | User input in form |
| `server_smtp` | e.g. `"smtp.example.com"` | User input in form |
| `imap_port` | e.g. `993` | User input in form (parsed to int) |
| `smtp_port` | e.g. `465` | User input in form (parsed to int) |
| `email` | e.g. `"user@example.com"` | User input in form |
| `password` | user's password | User input in form |
| `subscription_id` | UUID string | `currentSubscription.subscription_id` (auth context) |
| `calendar_provider` | `"null"` (string) | Hardcoded — calendar is configured separately in Step 2 |
| `service_id` | UUID string | Same resolution as 3A |

**Returns:** `{ status: "success" | "error", message: string, data: { email, email_provider, ... } }`

---

## Phase 2: Calendar Step (`step-calendar.tsx`)

> **Only shown for Custom IMAP users.** Google/Microsoft users skip this step because their calendar is connected via the `services: "all"` parameter in the email OAuth call.

### Call 5 — Resolve `service_id` (conditional, same pattern)

### Call 6 — Start calendar OAuth

```
POST /auth/oauth/login/{provider_name}
```

| Argument | Value | Source |
|---|---|---|
| `provider_name` (URL path) | `"google"` or `"microsoft"` | User selection in UI |
| `subscription_id` | UUID string | `currentSubscription.subscription_id` (auth context) |
| `services` | `"calendar"` | Hardcoded — only calendar scope |
| `email` | email string | `connectedEmail` from setup context (set after email step) |
| `service_id` | UUID string | Resolved via: (1) `serviceId` from setup context, (2) `currentSubscription.services[0].service_id`, (3) API fetch |

**Returns:** `{ success: boolean, url: string }` — same OAuth popup flow as email step.

---

## Phase 3: Website Step (`step-website.tsx`)

### Call 7 — Discover URLs

```
POST /scraper/research
```

| Argument | Value | Source |
|---|---|---|
| `website_url` | e.g. `"https://example.com"` | User input in text field |
| `max_urls` | `200` | Hardcoded default |

**Returns:** `{ website_url: string, urls: string[], count: number }`

### Call 8 — Get email for scraping

```
GET /subscriptionServiceRouter/get_subscription_service/{subscription_id}
```

| Argument | Source |
|---|---|
| `subscription_id` | `currentSubscription.subscription_id` (auth context) |

**What it does:** Finds the service matching `connectedEmail` (from setup context). Falls back to the first service with a valid email.

### Call 9 — Start scraping

```
POST /scraper/start
```

| Argument | Value | Source |
|---|---|---|
| `email` | email string | `service.email` — from Call 8 response, matched against `connectedEmail` |
| `website_url` | URL string | User input from the text field |
| `urls` | array of URL strings | User-selected URLs from the discovery results (Call 7) |

**Returns:** `{ message, email, collection_name, status }`

### Call 10 — Poll scraping status (repeating)

```
GET /scraper/status/{email}
```

| Argument | Source |
|---|---|
| `email` | `service.email` — from Call 8 |

**Polled every 3 seconds** until `status === "completed"` or `"failed"`.

**Returns:** `{ status: "started" | "processing" | "completed" | "failed", progress: { step, current_url, pages_scraped, ... } }`

---

## Phase 4: Quiz Step (`step-quiz.tsx`)

### Call 11 — Try to recover existing quiz session

```
GET /subscriptionServiceRouter/quiz/sessions/{email}
```

| Argument | Source |
|---|---|
| `email` | `connectedEmail` from setup context |

**Returns:** `QuizSessionByEmailResponse | null` — includes `session_id`, `bullet_list`, `final_markdown`, `is_done`

### Call 12 — Start new quiz (if no existing session)

```
POST /subscriptionServiceRouter/quiz/start
```

| Argument | Value | Source |
|---|---|---|
| `email` | email string | `connectedEmail` from setup context |

**Returns:** `{ session_id, question, bullet_list, done }`

### Call 13 — Answer quiz (per user message)

```
POST /subscriptionServiceRouter/quiz/answer
```

| Argument | Value | Source |
|---|---|---|
| `session_id` | UUID string | From Call 11 or 12 response |
| `answer` | user's text | User input in chat |

**Returns:** `{ session_id, question, bullet_list, extracted_markdown, done }`

### Call 14 — Save/update final markdown (on review)

```
PATCH /quiz/update-final-markdown
```

| Argument | Value | Source |
|---|---|---|
| `session_id` | UUID string | From quiz session |
| `final_markdown` | markdown string wrapped in code fence | Edited by user in review UI, or auto-generated by AI |

### Call 15 — Save quiz to DB (on complete, only if website was scraped)

```
POST /subscriptionServiceRouter/quiz/save
```

| Argument | Value | Source |
|---|---|---|
| `session_id` | UUID string | From quiz session |

**Returns:** `{ started: boolean, email: string, error?: string }`

---

## Phase 5: Static Quiz Step (`step-static-quiz.tsx`)

### Call 16 — Fetch existing calendar config

```
GET /subscriptionServiceRouter/get-calendar-information
```

No arguments. Uses auth token for identification.

**Returns:** `{ message, result: { business_hours, appointment_duration, email_signature, tone_of_voice, phone_numbers } }`

### Call 17 — Get email fallback (conditional)

Only if `connectedEmail` from setup context is null:

```
GET /subscriptionServiceRouter/get_subscription_service/{subscription_id}
```

| Argument | Source |
|---|---|
| `subscription_id` | `currentSubscription.subscription_id` (auth context) |

### Call 18 — Save static quiz settings

```
POST /subscriptionServiceRouter/static-quiz
```

| Argument | Value | Source |
|---|---|---|
| `email` | email string | `connectedEmail` from setup context, or fallback from Call 17 |
| `business_hours` | `{ "0": ["09:00-17:00"], ... }` | User configuration in UI |
| `appointment_duration` | e.g. `30` | User selection in UI |
| `email_signature` | text string | User input |
| `tone_of_voice` | text string | User input |
| `phone_numbers` | `{ "Main": "+39..." }` | User input (dynamic key-value pairs) |
| `draft` | boolean | User toggle |

---

## Phase 6: Complete Step (`step-complete.tsx`)

No API calls. Displays a success animation and redirects to `/dashboard` after 10 seconds.

The subscription is locally marked as configured via `markSubscriptionConfigured()` in auth context (updates the cookie, no API call).

---

## Summary — Argument Source Reference

| Source | Accessed as | Available from |
|---|---|---|
| **Subscription ID** | `currentSubscription.subscription_id` | Login response → auth context → cookie |
| **Service ID** | `serviceId` (setup context) or `currentSubscription.services[0].service_id` | Login response or `GET /get_subscription_service` |
| **Connected Email** | `connectedEmail` (setup context) | Set after email step OAuth/IMAP completes |
| **Session ID** (quiz) | Local state in `step-quiz.tsx` | From `GET /quiz/sessions/{email}` or `POST /quiz/start` |
| **User Input** | Various form fields | Direct user interaction |
| **Auth Token** | `backendService.accessToken` | Login response → `setAccessToken()` → in-memory + cookie |

---

## Known Issues

1. **`GET /auth/get-subscriptions/{userId}`** — Called by `service-list/page.tsx` via `refreshSubscriptions()`. **Endpoint does not exist on the backend** → always returns 404. Error is caught and silenced, no functional impact, but shows in console.

2. **`service_id` availability** — For freshly created subscriptions, the `services` array in the login response may be empty. The `service_id` must then be resolved via `GET /get_subscription_service`. If that also returns empty, the email step OAuth call will fail because `service_id` is now mandatory on the backend.
