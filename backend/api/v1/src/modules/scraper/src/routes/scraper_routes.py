"""FastAPI routes for web scraping operations."""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from pydantic import BaseModel, Field
from typing import Optional

from src.modules.scraper.src.controllers.scraper_controller import ScraperController

router = APIRouter(tags=["scraper"])
controller = ScraperController()


class StartScrapingRequest(BaseModel):
    """Request model for starting a scraping job."""
    email: str = Field(..., description="The email for the subscription service")
    website_url: str = Field(..., description="The URL of the website to scrape")
    max_pages: Optional[int] = Field(100, description="Maximum number of pages to scrape", ge=1, le=500)


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


@router.post(
    "/start",
    response_model=StartScrapingResponse,
    summary="Start a website scraping job",
    description="""
    Start a new scraping job for a website. The scraping process follows these steps:
    1. Scrape all pages from the website (respecting max_pages limit)
    2. Chunk the content into smaller pieces
    3. Clean the chunks using LLM to remove noise
    4. Generate embeddings for each chunk
    5. Upload embeddings to Qdrant vector database
    6. Store the collection name in the database
    
    The job runs in the background and you can check the status using the /status endpoint.
    """,
    responses={
        200: {
            "description": "Scraping job started successfully",
            "content": {
                "application/json": {
                    "example": {
                        "message": "Scraping job started",
                        "email": "123e4567-e89b-12d3-a456-426614174000",
                        "collection_name": "collection_123e4567-e89b-12d3-a456-426614174000",
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
        max_pages=request.max_pages,
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
                        "collection_name": "collection_123e4567-e89b-12d3-a456-426614174000",
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
                        "collection_name": "collection_123e4567-e89b-12d3-a456-426614174000",
                        "exists": True,
                        "info": {
                            "name": "collection_123e4567-e89b-12d3-a456-426614174000",
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
                        "message": "Collection collection_123e4567-e89b-12d3-a456-426614174000 deleted successfully",
                        "collection_name": "collection_123e4567-e89b-12d3-a456-426614174000"
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
