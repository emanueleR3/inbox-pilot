"""FastAPI routes for web scraping operations."""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from fastapi.params import Depends
from pydantic import BaseModel, Field
from typing import Optional, List

from src.core.dependecy import get_current_user
from src.modules.scraper.src.controllers.scraper_controller import ScraperController

router = APIRouter(
    dependencies=[Depends(get_current_user)],
    tags=["scraper"]
)
controller = ScraperController()


class StartScrapingRequest(BaseModel):
    """Request model for starting a scraping job."""
    email: str = Field(..., description="The email (unique) for the subscription service")
    website_url: str = Field(..., description="The root URL of the website")
    urls: List[str] = Field(..., description="Selected URLs of the website to scrape", min_length=1)


class DiscoverUrlsRequest(BaseModel):
    """Request model for discovering URLs of a website before scraping."""
    website_url: str = Field(..., description="The root URL of the website")
    max_urls: Optional[int] = Field(200, description="Maximum number of URLs to return", ge=1, le=2000)


class DiscoverUrlsResponse(BaseModel):
    """Response model for discovered URLs."""
    website_url: str
    urls: List[str]
    count: int


class StartScrapingResponse(BaseModel):
    """Response model for starting a scraping job."""
    message: str
    email: str
    collection_name: str
    status: str


class ScrapingStatusResponse(BaseModel):
    """Response model for scraping job status."""
    status: str
    website_url: Optional[str] = None
    collection_name: Optional[str] = None
    progress: Optional[dict] = None
    error: Optional[str] = None


class CollectionStatusResponse(BaseModel):
    """Response model for collection status."""
    collection_name: str
    exists: bool
    info: Optional[dict] = None


class DeleteCollectionResponse(BaseModel):
    """Response model for deleting a collection."""
    message: str
    collection_name: str


class DebugResponse(BaseModel):
    """Response model for debug snapshot."""
    pod: dict
    env: dict
    scrapings_dir: dict
    scrapings_file: Optional[dict] = None
    qdrant: dict


@router.get(
    "/debug",
    response_model=DebugResponse,
    summary="Temporary debug snapshot",
    description="""
    Temporary diagnostic endpoint to debug Qdrant connectivity and SCRAPINGS_DIR mounts.

    Disabled by default. Enable it temporarily by setting SCRAPER_DEBUG=true in the API deployment.
    """,
)
def debug_scraper(email: Optional[str] = Query(None, description="Optional email to check expected JSON export file")):
    return controller.debug_snapshot(email=email)


@router.post(
    "/research",
    response_model=DiscoverUrlsResponse,
    summary="Discover website URLs",
    description="""
    Discover indexable URLs of the provided website.

    This is meant to let the user select which URLs to scrape before starting the pipeline.
    """,
)
async def research_urls(request: DiscoverUrlsRequest):
    return await controller.discover_urls(
        website_url=request.website_url,
        max_urls=request.max_urls or 200,
    )


@router.post(
    "/start",
    response_model=StartScrapingResponse,
    summary="Start a website scraping job",
    description="""
    Start a new scraping job for a website. The scraping process follows these steps:
    1. Scrape only the selected URLs
    2. Clean page content with LLM (once)
    3. Export cleaned pages to JSON on the server
    4. Chunk the cleaned content
    5. Generate embeddings for each chunk
    6. Upload embeddings to Qdrant vector database
    7. Store the collection name in the database
    
    The job runs in the background and you can check the status using the /status endpoint.
    """,
    responses={
        200: {
            "description": "Scraping job started successfully",
            "content": {
                "application/json": {
                    "example": {
                        "message": "Scraping job started",
                        "email": "user@example.com",
                        "collection_name": "collection_user_example_com",
                        "status": "processing"
                    }
                }
            }
        },
        400: {"description": "Invalid request - missing required fields"},
        404: {"description": "Service not found"},
        500: {"description": "Internal server error"}
    }
)
async def start_scraping(
    request: StartScrapingRequest,
    background_tasks: BackgroundTasks
):
    """
    Start a website scraping job.
    
    The scraping process will:
    - Crawl the website starting from the provided URL
    - Extract and clean text content
    - Generate embeddings and store in Qdrant
    - Save the collection name to the database
    """
    return await controller.start_scraping(
        email=request.email,
        website_url=request.website_url,
        urls=request.urls,
        background_tasks=background_tasks
    )


@router.get(
    "/status/{email}",
    response_model=ScrapingStatusResponse,
    summary="Get scraping job status",
    description="Get the current status and progress of a scraping job.",
    responses={
        200: {
            "description": "Scraping job status",
            "content": {
                "application/json": {
                    "example": {
                        "status": "completed",
                        "website_url": "https://example.com",
                        "collection_name": "collection_user_example_com_aaaaaaaaaaaa",
                        "progress": {
                            "step": "completed",
                            "pages_scraped": 50,
                            "chunks_created": 150,
                            "chunks_cleaned": 150,
                            "chunks_embedded": 150,
                            "chunks_uploaded": 150
                        },
                        "error": None
                    }
                }
            }
        },
        404: {"description": "Scraping job not found"},
    }
)
def get_scraping_status(email: str):
    """
    Get the status of a scraping job.
    
    Returns the current step, progress counters, and any errors.
    """
    return controller.get_scraping_status(email)


@router.get(
    "/collection/{email}",
    response_model=CollectionStatusResponse,
    summary="Get collection status",
    description="Get information about the Qdrant collection for a service.",
    responses={
        200: {
            "description": "Collection status",
            "content": {
                "application/json": {
                    "example": {
                        "collection_name": "collection_user_example_com_aaaaaaaaaaaa",
                        "exists": True,
                        "info": {
                            "name": "collection_user_example_com_aaaaaaaaaaaa",
                            "points_count": 150,
                            "vectors_count": 150,
                            "status": "green"
                        }
                    }
                }
            }
        },
        400: {"description": "Invalid request"},
    }
)
def get_collection_status(email: str):
    """
    Get information about the Qdrant collection for a service.
    
    Returns whether the collection exists and its current stats.
    """
    return controller.get_collection_status(email)


@router.delete(
    "/collection/{email}",
    response_model=DeleteCollectionResponse,
    summary="Delete collection",
    description="Delete the Qdrant collection for a service.",
    responses={
        200: {
            "description": "Collection deleted successfully",
            "content": {
                "application/json": {
                    "example": {
                        "message": "Collection collection_user_example_com_aaaaaaaaaaaa deleted successfully",
                        "collection_name": "collection_user_example_com_aaaaaaaaaaaa"
                    }
                }
            }
        },
        404: {"description": "Collection not found"},
        500: {"description": "Failed to delete collection"}
    }
)
def delete_collection(email: str):
    """
    Delete the Qdrant collection for a service.
    
    This will remove all scraped data for the service.
    """
    return controller.delete_service_collection(email)
