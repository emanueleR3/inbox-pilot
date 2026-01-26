# Internal Quiz API (V2)

This document describes the current **Quiz V2** endpoints exposed by the Automations API router in:

- [automations/api/routers/quiz_router.py](automations/api/routers/quiz_router.py)

Only **V2** is documented here (the legacy quiz implementation is intentionally ignored).

## Base path

The quiz router is mounted in [automations/api/main.py](automations/api/main.py) with:

- Prefix: `/internal-quiz`

So all endpoints below are under `/internal-quiz`.

## Notes / current behavior

- These endpoints are marked `include_in_schema=False`, so they may not appear in Swagger/OpenAPI.
- Sessions are stored in the `quiz_sessions` table (Supabase/Postgres). Restarting the service does not clear active sessions.
- `email` is required to start a quiz and is used as the key to load/update the service in DB.
- On start, the backend checks whether the service has a `qdrant_collection` (scraping done) and returns it as `has_context`.

## Save Pipeline (Background)

The save pipeline runs in background when the user confirms saving (e.g., "ok, salva" in chat or via `/save` endpoint).

**Key features:**
- **Multi-pod safe**: Status is persisted in `quiz_sessions` table, not in-memory
- **Atomic locking**: Uses compare-and-set to prevent duplicate executions across pods
- **Real-time tracking**: Progress is updated in DB at each step

**Save status columns in `quiz_sessions`:**

| Column | Type | Description |
|--------|------|-------------|
| `save_status` | text | Status: `idle`, `running`, `completed`, `failed` |
| `save_phase` | text | Current phase name |
| `save_actual_step` | int | Current step (1-9) |
| `save_total_steps` | int | Total steps (9) |
| `save_error` | text | Error message if failed |
| `save_started_at` | timestamptz | When save started |
| `save_updated_at` | timestamptz | Last status update |
| `save_completed_at` | timestamptz | When save completed |
| `save_details` | jsonb | Additional details (message, paths, counts) |
| `save_run_id` | uuid | Unique identifier for this run |
| `save_worker` | text | Pod/worker identifier |

## Data shapes

### Bullet list item

`bullet_list` is an array of:

```json
{
  "name": "string",
  "completed": true,
  "info": "string | null"
}
```

### Common fields

- `phase`: string describing the current phase of the flow
- `turn_count`: integer
- `max_turns`: integer
- `done`: boolean (when `true`, the quiz is completed)
- `question`: string (the next question to show to the user)

## Endpoints

### POST /internal-quiz/start

Starts a new Quiz V2 session.

**Request body**

```json
{
  "email": "user@example.com"
}
```

**Response (200)**

```json
{
  "session_id": "uuid",
  "question": "string",
  "bullet_list": [
    {"name": "string", "completed": false, "info": null}
  ],
  "phase": "string",
  "turn_count": 0,
  "max_turns": 10,
  "has_context": true,
  "done": false,
  "email": "user@example.com"
}
```

**Errors**

- `400` if `email` is missing
- `500` on unexpected failures

**Example**

```bash
curl -X POST http://localhost:8010/internal-quiz/start \
  -H 'Content-Type: application/json' \
  -d '{"email":"user@example.com"}'
```

---

### POST /internal-quiz/answer

Submits an answer for the current question.

**Request body**

```json
{
  "session_id": "uuid",
  "answer": "my answer"
}
```

Notes:
- The router also accepts `value` as an alias of `answer`, but for V2 clients prefer `answer`.

**Response (200)**

```json
{
  "done": false,
  "question": "string",
  "bullet_list": [
    {"name": "string", "completed": false, "info": null}
  ],
  "phase": "string",
  "turn_count": 1,
  "max_turns": 10,
  "extracted_markdown": null,
  "error": null
}
```

When the quiz completes (`done: true`), `extracted_markdown` may contain the generated markdown.

When the user confirms save (e.g., "ok, salva"), the response will include `save_started: true` indicating that the save pipeline has started in the background. Use `/internal-quiz/save-status` to monitor progress.

**Errors**

- `400` if `session_id` or `answer` is missing
- `404` if `session_id` does not exist
- `500` on unexpected failures

**Example**

```bash
curl -X POST http://localhost:8010/internal-quiz/answer \
  -H 'Content-Type: application/json' \
  -d '{"session_id":"<uuid>","answer":"..."}'
```

---

### GET /internal-quiz/{email}/state

Returns the full state of the current quiz session.

**Response (200)**

```json
{
  "session_id": "uuid",
  "service_id": "string",
  "phase": "string",
  "turn_count": 1,
  "max_turns": 10,
  "business_field": "string | null",
  "bullet_list": [
    {"name": "string", "completed": false, "info": null}
  ],
  "messages": [
    {"role": "assistant", "content": "..."},
    {"role": "user", "content": "..."}
  ],
  "is_done": false,
  "has_context": false,
  "final_markdown": "string | null"
}
```

**Errors**

- `400` if `email` is missing or the quiz is not started yet
- `404` if no quiz session exists for that `email`

**Example**

```bash
curl http://localhost:8010/internal-quiz/<email>/state
```

---

### POST /internal-quiz/finish

Forces the quiz to finish and generates markdown from the current state.

**Request body**

```json
{
  "session_id": "uuid"
}
```

**Response (200)**

```json
{
  "done": true,
  "extracted_markdown": "string | null",
  "bullet_list": [
    {"name": "string", "completed": true, "info": "..."}
  ],
  "error": null
}
```

**Errors**

- `400` if `session_id` is missing
- `404` if `session_id` does not exist

**Example**

```bash
curl -X POST http://localhost:8010/internal-quiz/finish \
  -H 'Content-Type: application/json' \
  -d '{"session_id":"<uuid>"}'
```

---

### GET /internal-quiz/sessions

Lists active quiz sessions from the database.

**Response (200)**

```json
[
  {
    "session_id": "uuid",
    "service_id": "uuid",
    "email": "string",
    "status": "in_progress",
    "phase": "string",
    "turn_count": 0,
    "max_turns": 20,
    "created_at": "2025-01-01T00:00:00Z",
    "updated_at": "2025-01-01T00:00:00Z"
  }
]
```

**Example**

```bash
curl http://localhost:8010/internal-quiz/sessions
```

---

### POST /internal-quiz/save

Manually triggers the save pipeline for a quiz session. Use this endpoint to trigger save programmatically (e.g., from a save button) without relying on chat message interpretation.

The pipeline runs in background and returns immediately. Use `/internal-quiz/save-status` to monitor progress.

**Request body**

```json
{
  "session_id": "uuid"
}
```

**Response (200)**

```json
{
  "started": true,
  "session_id": "uuid",
  "email": "user@example.com"
}
```

**Response (400) - Error cases**

```json
{
  "started": false,
  "error": "Sessione non trovata"
}
```

Possible errors:
- `Sessione non trovata` - Session ID does not exist
- `L'utente non ha una collezione Qdrant (scraping non effettuato)` - User has no qdrant collection
- `Nessun markdown finale da salvare` - No final markdown to save
- `Pipeline già in esecuzione per questa sessione` - Pipeline already running

**Errors**

- `400` if `session_id` is missing or save cannot start
- `500` on unexpected failures

**Example**

```bash
curl -X POST http://localhost:8010/internal-quiz/save \
  -H 'Content-Type: application/json' \
  -d '{"session_id":"<uuid>"}'
```

---

### GET /internal-quiz/save-status

Returns the status of a save pipeline operation. Use this to monitor the progress of context saving.

**Query parameters** (at least one required)

- `session_id` - The quiz session ID
- `email` - User email (used if session_id not provided)

**Response (200) - Pipeline running or completed**

```json
{
  "session_id": "uuid",
  "email": "user@example.com",
  "phase": "EMBEDDING",
  "actual_step": 7,
  "total_steps": 9,
  "started_at": "2025-01-02T10:30:00+00:00",
  "updated_at": "2025-01-02T10:32:15+00:00",
  "completed_at": null,
  "error": null,
  "details": {
    "message": "Embedding di 45 chunks in corso...",
    "chunks_count": 45
  },
  "run_id": "uuid",
  "worker": "pod-abc123:1234",
  "is_running": true,
  "is_completed": false,
  "is_failed": false,
  "save_status": "running"
}
```

**Response (200) - No save in progress (idle)**

```json
{
  "session_id": "uuid",
  "email": "user@example.com",
  "phase": "idle",
  "actual_step": 0,
  "total_steps": 9,
  "started_at": null,
  "updated_at": null,
  "completed_at": null,
  "error": null,
  "details": {},
  "run_id": null,
  "worker": null,
  "is_running": false,
  "is_completed": false,
  "is_failed": false,
  "save_status": "idle"
}
```

**Pipeline phases**

| Phase | Step | Description |
|-------|------|-------------|
| `PENDING` | 0 | Pipeline starting |
| `FETCHING_DATA` | 1 | Fetching scraping data from database |
| `READING_JSON` | 2 | Reading original JSON file |
| `UPDATING_JSON_WITH_LLM` | 3 | Using LLM to update JSON with changes |
| `SAVING_JSON` | 4 | Saving updated JSON file |
| `DELETING_OLD_COLLECTION` | 5 | Deleting old Qdrant collection |
| `CHUNKING` | 6 | Creating chunks from JSON |
| `EMBEDDING` | 7 | Embedding chunks |
| `UPLOADING_TO_QDRANT` | 8 | Uploading to Qdrant |
| `UPDATING_DATABASE` | 9 | Updating database paths |
| `COMPLETED` | 9 | Pipeline completed successfully |
| `FAILED` | varies | Pipeline failed (check error field) |

**Errors**

- `400` if neither `session_id` nor `email` is provided
- `500` on unexpected failures

**Example**

```bash
# By session_id
curl "http://localhost:8010/internal-quiz/save-status?session_id=<uuid>"

# By email
curl "http://localhost:8010/internal-quiz/save-status?email=user@example.com"
```
