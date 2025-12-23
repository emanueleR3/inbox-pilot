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
