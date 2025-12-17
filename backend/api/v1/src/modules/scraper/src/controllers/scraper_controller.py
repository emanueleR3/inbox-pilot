"""Scraper controller for handling website scraping operations."""

from fastapi import HTTPException, status, BackgroundTasks
from typing import Optional, Dict, Any
import asyncio
import re
import uuid

from src.core.DAO.subscription_service_dao import SubscriptionServiceDAO
from src.modules.scraper.src.utils.scraping import scrape_website, ScrapedPage
from src.modules.scraper.src.utils.chunking import chunk_pages, Chunk
from src.modules.scraper.src.utils.cleaning import clean_all_chunks
from src.modules.scraper.src.utils.embedding import embed_chunks
from src.modules.scraper.src.utils.qdrant_utils import (
    upload_to_qdrant,
    delete_collection,
    collection_exists,
    get_collection_info
)


# In-memory storage for scraping job status
scraping_jobs: Dict[str, Dict[str, Any]] = {}


class ScraperController:
    """Controller for website scraping operations."""
    
    def __init__(self):
        self.subscription_service_dao = SubscriptionServiceDAO()
    
    def _normalize_email_key(self, email: str) -> str:
        return (email or "").strip().lower()

    def _generate_collection_name(self, email: str) -> str:
        """Generate a stable, Qdrant-safe collection name from email."""
        normalized = self._normalize_email_key(email)
        safe = re.sub(r"[^a-z0-9]+", "_", normalized).strip("_")
        # deterministic suffix to avoid collisions and keep name short
        suffix = uuid.uuid5(uuid.NAMESPACE_DNS, normalized).hex[:12]
        safe_prefix = safe[:32] if safe else "user"
        return f"collection_{safe_prefix}_{suffix}"
    
    async def start_scraping(
        self, 
        email: str, 
        website_url: str, 
        max_pages: int = 100,
        background_tasks: BackgroundTasks = None
    ) -> Dict[str, Any]:
        """
        Start the scraping process for a website.
        
        Args:
            service_id: The service_id for the subscription service
            website_url: The URL of the website to scrape
            max_pages: Maximum number of pages to scrape
            background_tasks: FastAPI BackgroundTasks for async processing
            
        Returns:
            Dictionary with job information
        """
        email_key = self._normalize_email_key(email)
        if not email_key:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="email is required"
            )
        
        if not website_url:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="website_url is required"
            )
        
        # Verify service exists
        service = self.subscription_service_dao.get_service_by_email(email_key)
        if not service:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Service with email {email_key} not found"
            )
        
        collection_name = self._generate_collection_name(email_key)
        
        # Initialize job status
        scraping_jobs[email_key] = {
            "status": "started",
            "website_url": website_url,
            "collection_name": collection_name,
            "progress": {
                "step": "initializing",
                "current_url": "",
                "pages_scraped": 0,
                "chunks_created": 0,
                "chunks_cleaned": 0,
                "chunks_embedded": 0,
                "chunks_uploaded": 0
            },
            "error": None
        }
        
        if background_tasks:
            # Run in background
            background_tasks.add_task(
                self._run_scraping_pipeline,
                email_key,
                website_url,
                collection_name,
                max_pages
            )
            return {
                "message": "Scraping job started",
                "email": email_key,
                "collection_name": collection_name,
                "status": "processing"
            }
        else:
            # Run synchronously
            await self._run_scraping_pipeline(
                email_key,
                website_url,
                collection_name,
                max_pages
            )
            return scraping_jobs.get(email_key, {})
    
    async def _run_scraping_pipeline(
        self,
        email: str,
        website_url: str,
        collection_name: str,
        max_pages: int
    ):
        """
        Run the complete scraping pipeline: scrape -> chunk -> clean -> embed -> upload.
        """
        try:
            # Step 1: Scrape website
            scraping_jobs[email]["progress"]["step"] = "scraping"
            scraping_jobs[email]["progress"]["current_url"] = website_url
            print(f"[{email}] Starting scraping for {website_url}")
            
            # Define progress callback to update status in real-time
            def update_scraping_progress(pages_scraped: int, current_url: str):
                scraping_jobs[email]["progress"]["pages_scraped"] = pages_scraped
                scraping_jobs[email]["progress"]["current_url"] = current_url
            
            # Run scraping in thread pool to not block
            loop = asyncio.get_event_loop()
            pages = await loop.run_in_executor(
                None, 
                lambda: scrape_website(website_url, max_pages, update_scraping_progress)
            )
            
            scraping_jobs[email]["progress"]["pages_scraped"] = len(pages)
            print(f"[{email}] Scraped {len(pages)} pages")
            
            if not pages:
                scraping_jobs[email]["status"] = "completed"
                scraping_jobs[email]["progress"]["step"] = "completed_no_content"
                return
            
            # Convert ScrapedPage to dict for chunking
            pages_dict = [
                {"url": p.url, "title": p.title, "content": p.content}
                for p in pages
            ]
            
            # Step 2: Chunk pages
            scraping_jobs[email]["progress"]["step"] = "chunking"
            print(f"[{email}] Chunking pages...")
            
            chunks = await loop.run_in_executor(None, chunk_pages, pages_dict)
            scraping_jobs[email]["progress"]["chunks_created"] = len(chunks)
            print(f"[{email}] Created {len(chunks)} chunks")
            
            if not chunks:
                scraping_jobs[email]["status"] = "completed"
                scraping_jobs[email]["progress"]["step"] = "completed_no_chunks"
                return
            
            # Step 3: Clean chunks with LLM
            scraping_jobs[email]["progress"]["step"] = "cleaning"
            print(f"[{email}] Cleaning chunks with LLM...")
            
            # Define progress callback for cleaning
            def update_cleaning_progress(chunks_cleaned: int):
                scraping_jobs[email]["progress"]["chunks_cleaned"] = chunks_cleaned
            
            cleaned_chunks = await loop.run_in_executor(
                None, 
                lambda: clean_all_chunks(chunks, progress_callback=update_cleaning_progress)
            )
            scraping_jobs[email]["progress"]["chunks_cleaned"] = len(cleaned_chunks)
            print(f"[{email}] Cleaned {len(cleaned_chunks)} chunks")
            
            # Step 4: Embed chunks
            scraping_jobs[email]["progress"]["step"] = "embedding"
            print(f"[{email}] Embedding chunks...")
            
            embedded_chunks = await loop.run_in_executor(None, embed_chunks, cleaned_chunks)
            scraping_jobs[email]["progress"]["chunks_embedded"] = len(embedded_chunks)
            print(f"[{email}] Embedded {len(embedded_chunks)} chunks")
            
            # Step 5: Upload to Qdrant
            scraping_jobs[email]["progress"]["step"] = "uploading"
            print(f"[{email}] Uploading to Qdrant collection '{collection_name}'...")
            
            total_points = await loop.run_in_executor(
                None,
                upload_to_qdrant,
                collection_name,
                embedded_chunks
            )
            scraping_jobs[email]["progress"]["chunks_uploaded"] = total_points
            print(f"[{email}] Uploaded {total_points} points to Qdrant")
            
            # Step 6: Update database with collection name
            scraping_jobs[email]["progress"]["step"] = "updating_database"
            print(f"[{email}] Updating database with collection name...")
            
            success = self.subscription_service_dao.update_qdrant_collection_by_email(email, collection_name)
            
            if not success:
                print(f"[{email}] Warning: Failed to update database with collection name")
            
            # Complete
            scraping_jobs[email]["status"] = "completed"
            scraping_jobs[email]["progress"]["step"] = "completed"
            print(f"[{email}] Scraping pipeline completed successfully")
            
        except Exception as e:
            scraping_jobs[email]["status"] = "failed"
            scraping_jobs[email]["error"] = str(e)
            print(f"[{email}] Scraping pipeline failed: {e}")

    def get_scraping_status(self, email: str) -> Dict[str, Any]:
        """
        Get the status of a scraping job.
        
        Args:
            email: The email for the subscription service
            
        Returns:
            Dictionary with job status
        """
        email_key = self._normalize_email_key(email)
        if not email_key:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="email is required"
            )
        
        if email_key not in scraping_jobs:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No scraping job found for email {email_key}"
            )
        
        return scraping_jobs[email_key]
    
    def get_collection_status(self, email: str) -> Dict[str, Any]:
        """
        Get the status of the Qdrant collection for a service.
        
        Args:
            email: The email for the subscription service
            
        Returns:
            Dictionary with collection information
        """
        email_key = self._normalize_email_key(email)
        if not email_key:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="email is required"
            )
        
        # Get collection name from database
        collection_name = self.subscription_service_dao.get_qdrant_collection_by_email(email_key)
        
        if not collection_name:
            # Try generating the name
            collection_name = self._generate_collection_name(email_key)
        
        # Check if collection exists
        if not collection_exists(collection_name):
            return {
                "collection_name": collection_name,
                "exists": False,
                "info": None
            }
        
        # Get collection info
        info = get_collection_info(collection_name)
        
        return {
            "collection_name": collection_name,
            "exists": True,
            "info": info
        }
    
    def delete_service_collection(self, email: str) -> Dict[str, Any]:
        """
        Delete the Qdrant collection for a service.
        
        Args:
            email: The email for the subscription service
            
        Returns:
            Dictionary with deletion status
        """
        email_key = self._normalize_email_key(email)
        if not email_key:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="email is required"
            )
        
        collection_name = self._generate_collection_name(email_key)
        
        if not collection_exists(collection_name):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Collection {collection_name} not found"
            )
        
        success = delete_collection(collection_name)
        
        if success:
            # Clear the collection name from database
            self.subscription_service_dao.update_qdrant_collection_by_email(email_key, None)
            
            return {
                "message": f"Collection {collection_name} deleted successfully",
                "collection_name": collection_name
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete collection {collection_name}"
            )
