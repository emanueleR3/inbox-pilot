
# Scraper Module

Web scraping module for extracting content from websites, processing it through a RAG pipeline, and storing it in Qdrant vector database.

## Pipeline Flow

1. **Research** → Discover website URLs (user selects what to scrape)
2. **Scrape** → Fetch only the selected URLs, extract text content
3. **Page Clean** → LLM cleans page content once (before chunking)
4. **Export JSON** → Save cleaned pages to a JSON file on the server
5. **Chunk** → Split cleaned content into smaller pieces with overlap
6. **Embed** → Generate OpenAI embeddings
7. **Upload** → Store in Qdrant vector database
8. **Save** → Update DB fields `qdrant_collection` and `scraping_collection_path`

## API Endpoints

### POST /scraper/research

Discover indexable URLs of the provided website.
Use this endpoint to let the user pick which URLs to scrape.

**Request Body:**
```json
{
    "website_url": "https://example.com",
    "max_urls": 200
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| website_url | string | Yes | Root URL of the website |
| max_urls | integer | No | Max URLs returned (default: 200) |

**Response (200):**
```json
{
    "website_url": "https://example.com",
    "urls": [
        "https://example.com",
        "https://example.com/about"
    ],
    "count": 2
}
```

---

### POST /scraper/start

Start a new website scraping job. The job runs in the background.

**Request Body:**
```json
{
        "email": "user@example.com",
        "website_url": "https://example.com",
        "urls": [
            "https://example.com",
            "https://example.com/about"
        ]
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| email | string | Yes | Unique email of the subscription service |
| website_url | string | Yes | Root URL of the website |
| urls | string[] | Yes | Selected URLs to scrape (must be non-empty) |

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

### GET /scraper/status/{email}

Get the current status and progress of a scraping job.

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| email | string | Unique email of the subscription service |

**Response (200):**
```json
{
    "status": "completed",
    "website_url": "https://example.com",
    "collection_name": "collection_user_example_com_aaaaaaaaaaaa",
    "progress": {
        "step": "completed",
        "pages_scraped": 50,
        "pages_cleaned": 50,
        "chunks_created": 150,
        "chunks_embedded": 150,
        "chunks_uploaded": 150
    },
    "error": null
}
```

**Progress Steps:**
- `initializing` - Job is starting
- `scraping` - Crawling website pages
- `page_cleaning` - Cleaning page content with LLM
- `exporting_json` - Saving the JSON export to server storage
- `chunking` - Splitting content into chunks
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
| email | string | Unique email of the subscription service |

**Response (200) - Collection exists:**
```json
{
    "collection_name": "collection_user_example_com_aaaaaaaaaaaa",
    "exists": true,
    "info": {
        "name": "collection_user_example_com_aaaaaaaaaaaa",
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
| email | string | Unique email of the subscription service |

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

Collections are named deterministically from the service email.

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| OPENAI_API_KEY | OpenAI API key for embeddings and cleaning | Required |
| QDRANT_URL | Qdrant server URL | http://localhost:6333 |
| QDRANT_API_KEY | Qdrant API key (optional) | None |
| SCRAPINGS_DIR | Directory where JSON export is written | /app/scrapings |
| SCRAPINGS_DB_DIR | Optional: path string saved in DB for scraping_collection_path | (defaults to SCRAPINGS_DIR) |
| LANGCHAIN_TRACING_V2 | Enable LangSmith tracing | true |
| LANGCHAIN_API_KEY | LangSmith API key | - |
| LANGCHAIN_PROJECT | LangSmith project name | corretto_scraper |

## Database

The module updates these fields in the `subscription_services` table (identified by unique `email`):

- `qdrant_collection`: Qdrant collection name
- `scraping_collection_path`: path of the JSON export file saved on server