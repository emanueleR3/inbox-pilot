
# Scraper Module

Web scraping module for extracting content from websites, processing it through a RAG pipeline, and storing it in Qdrant vector database.

## Pipeline Flow

1. **Scrape** → Crawl website, extract text content
2. **Chunk** → Split content into smaller pieces with overlap
3. **Clean** → LLM cleans noise from chunks
4. **Embed** → Generate OpenAI embeddings
5. **Upload** → Store in Qdrant vector database
6. **Save** → Update `qdrant_collection` field in database

## API Endpoints

The router is mounted with prefix `/scraper` (see `api/v1/src/main.py`). All paths below are relative to that prefix.

### POST /scraper/start

Start a new website scraping job. The job runs in the background.

**Request Body:**
```json
{
    "email": "user@example.com",
    "website_url": "https://example.com",
    "max_pages": 100
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| email | string | Yes | The email (unique) for the subscription service |
| website_url | string | Yes | The URL of the website to scrape |
| max_pages | integer | No | Maximum pages to scrape (default: 100, max: 500) |

**Response (200):**
```json
{
    "message": "Scraping job started",
    "email": "user@example.com",
    "collection_name": "collection_user_example_com_aaaaaaaaaaaa",
    "status": "processing"
}
```

**Errors:**
- `400` - Invalid request (missing required fields)
- `404` - Service not found
- `500` - Internal server error

---

### GET /scraper/status/{service_id}

Get the current status and progress of a scraping job.

### GET /scraper/status/{email}

Get the current status and progress of a scraping job.

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| email | string | The email (unique) for the subscription service |

**Response (200):**
```json
{
    "status": "completed",
    "website_url": "https://example.com",
    "collection_name": "collection_user_example_com_aaaaaaaaaaaa",
    "progress": {
        "step": "completed",
        "current_url": "https://example.com",
        "pages_scraped": 50,
        "chunks_created": 150,
        "chunks_cleaned": 150,
        "chunks_embedded": 150,
        "chunks_uploaded": 150
    },
    "error": null
}
```

**Progress Steps:**
- `initializing` - Job is starting
- `scraping` - Crawling website pages
- `chunking` - Splitting content into chunks
- `cleaning` - LLM cleaning chunks
- `embedding` - Generating embeddings
- `uploading` - Uploading to Qdrant
- `updating_database` - Saving collection name
- `completed` - Job finished successfully
- `completed_no_content` - No content found
- `completed_no_chunks` - No chunks created

**Status Values:**
- `started` - Job has been started
- `completed` - Job finished successfully
- `failed` - Job failed (check `error` field)

**Errors:**
- `404` - Scraping job not found

---

### GET /scraper/collection/{email}

Get information about the Qdrant collection for a service.

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| email | string | The email (unique) for the subscription service |

**Response (200) - Collection exists:**
```json
{
    "collection_name": "collection_123e4567-e89b-12d3-a456-426614174000",
    "exists": true,
    "info": {
        "name": "collection_123e4567-e89b-12d3-a456-426614174000",
        "points_count": 150,
        "vectors_count": 150,
        "status": "green"
    }
}
```

**Response (200) - Collection does not exist:**
```json
{
    "collection_name": "collection_123e4567-e89b-12d3-a456-426614174000",
    "exists": false,
    "info": null
}
```

**Errors:**
- `400` - Invalid request

---

### DELETE /scraper/collection/{email}

Delete the Qdrant collection for a service. This removes all scraped data.

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| email | string | The email (unique) for the subscription service |

**Response (200):**
```json
{
    "message": "Collection collection_123e4567-e89b-12d3-a456-426614174000 deleted successfully",
    "collection_name": "collection_123e4567-e89b-12d3-a456-426614174000"
}
```

**Errors:**
- `400` - Invalid request
- `404` - Collection not found
- `500` - Failed to delete collection

---

## Collection Naming Convention

Collections are generated deterministically from the email (normalized to lowercase and made Qdrant-safe), with a stable suffix to avoid collisions.

Example: `collection_user_example_com_3e3e4ed8c7e6`

Note: the collection name is stored in DB when a scraping job completes successfully.

## Notes

- Emails are normalized (trim + lowercase) before use.
- Scraping job status is stored in-memory; restarting the API process clears the current `/status` tracking.

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| OPENAI_API_KEY | OpenAI API key for embeddings and cleaning | Required |
| QDRANT_URL | Qdrant server URL | http://localhost:6333 |
| QDRANT_API_KEY | Qdrant API key (optional) | None |
| LANGCHAIN_TRACING_V2 | Enable LangSmith tracing | true |
| LANGCHAIN_API_KEY | LangSmith API key | - |
| LANGCHAIN_PROJECT | LangSmith project name | corretto_scraper |

## Database

The module updates the `qdrant_collection` field in the `subscription_services` table when a scraping job completes successfully.