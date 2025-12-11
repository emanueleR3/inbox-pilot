"""Scraper models for request/response schemas."""
from pydantic import BaseModel, Field
from typing import Optional, List


class ScrapedPageModel(BaseModel):
    """Model for a scraped page."""
    url: str = Field(..., description="URL of the scraped page")
    title: str = Field(..., description="Title of the page")
    content: str = Field(..., description="Extracted text content")


class ChunkModel(BaseModel):
    """Model for a text chunk."""
    id: str = Field(..., description="Unique chunk identifier")
    url: str = Field(..., description="Source URL")
    title: str = Field(..., description="Source page title")
    page_index: int = Field(..., description="Index of the source page")
    chunk_index: int = Field(..., description="Index of the chunk within the page")
    text: str = Field(..., description="Chunk text content")


class ScrapingProgressModel(BaseModel):
    """Model for scraping job progress."""
    step: str = Field(..., description="Current step in the pipeline")
    current_url: str = Field("", description="Currently processing URL")
    pages_scraped: int = Field(0, description="Number of pages scraped")
    chunks_created: int = Field(0, description="Number of chunks created")
    chunks_cleaned: int = Field(0, description="Number of chunks cleaned")
    chunks_embedded: int = Field(0, description="Number of chunks embedded")
    chunks_uploaded: int = Field(0, description="Number of chunks uploaded")


class ScrapingJobModel(BaseModel):
    """Model for a scraping job."""
    status: str = Field(..., description="Job status: started, processing, completed, failed")
    website_url: Optional[str] = Field(None, description="URL being scraped")
    collection_name: Optional[str] = Field(None, description="Qdrant collection name")
    progress: Optional[ScrapingProgressModel] = Field(None, description="Job progress")
    error: Optional[str] = Field(None, description="Error message if failed")


class CollectionInfoModel(BaseModel):
    """Model for Qdrant collection information."""
    name: str = Field(..., description="Collection name")
    points_count: int = Field(..., description="Number of points in collection")
    vectors_count: int = Field(..., description="Number of vectors in collection")
    status: str = Field(..., description="Collection status")
