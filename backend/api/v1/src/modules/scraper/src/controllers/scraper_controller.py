"""Scraper controller for handling website scraping operations."""

from fastapi import HTTPException, status, BackgroundTasks
from typing import Optional, Dict, Any
import asyncio

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
    
    def _generate_collection_name(self, service_id: str) -> str:
        """Generate Qdrant collection name from service_id."""
        return f"collection_{service_id}"
    
    async def start_scraping(
        self, 
        service_id: str, 
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
        if not service_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="service_id is required"
            )
        
        if not website_url:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="website_url is required"
            )
        
        # Verify service exists
        service = self.subscription_service_dao.get_service_by_id(service_id)
        if not service:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Service with id {service_id} not found"
            )
        
        collection_name = self._generate_collection_name(service_id)
        
        # Initialize job status
        scraping_jobs[service_id] = {
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
                service_id,
                website_url,
                collection_name,
                max_pages
            )
            return {
                "message": "Scraping job started",
                "service_id": service_id,
                "collection_name": collection_name,
                "status": "processing"
            }
        else:
            # Run synchronously
            await self._run_scraping_pipeline(
                service_id,
                website_url,
                collection_name,
                max_pages
            )
            return scraping_jobs.get(service_id, {})
    
    async def _run_scraping_pipeline(
        self,
        service_id: str,
        website_url: str,
        collection_name: str,
        max_pages: int
    ):
        """
        Run the complete scraping pipeline: scrape -> chunk -> clean -> embed -> upload.
        """
        try:
            # Step 1: Scrape website
            scraping_jobs[service_id]["progress"]["step"] = "scraping"
            scraping_jobs[service_id]["progress"]["current_url"] = website_url
            print(f"[{service_id}] Starting scraping for {website_url}")
            
            # Define progress callback to update status in real-time
            def update_scraping_progress(pages_scraped: int, current_url: str):
                scraping_jobs[service_id]["progress"]["pages_scraped"] = pages_scraped
                scraping_jobs[service_id]["progress"]["current_url"] = current_url
            
            # Run scraping in thread pool to not block
            loop = asyncio.get_event_loop()
            pages = await loop.run_in_executor(
                None, 
                lambda: scrape_website(website_url, max_pages, update_scraping_progress)
            )
            
            scraping_jobs[service_id]["progress"]["pages_scraped"] = len(pages)
            print(f"[{service_id}] Scraped {len(pages)} pages")
            
            if not pages:
                scraping_jobs[service_id]["status"] = "completed"
                scraping_jobs[service_id]["progress"]["step"] = "completed_no_content"
                return
            
            # Convert ScrapedPage to dict for chunking
            pages_dict = [
                {"url": p.url, "title": p.title, "content": p.content}
                for p in pages
            ]
            
            # Step 2: Chunk pages
            scraping_jobs[service_id]["progress"]["step"] = "chunking"
            print(f"[{service_id}] Chunking pages...")
            
            chunks = await loop.run_in_executor(None, chunk_pages, pages_dict)
            scraping_jobs[service_id]["progress"]["chunks_created"] = len(chunks)
            print(f"[{service_id}] Created {len(chunks)} chunks")
            
            if not chunks:
                scraping_jobs[service_id]["status"] = "completed"
                scraping_jobs[service_id]["progress"]["step"] = "completed_no_chunks"
                return
            
            # Step 3: Clean chunks with LLM
            scraping_jobs[service_id]["progress"]["step"] = "cleaning"
            print(f"[{service_id}] Cleaning chunks with LLM...")
            
            # Define progress callback for cleaning
            def update_cleaning_progress(chunks_cleaned: int):
                scraping_jobs[service_id]["progress"]["chunks_cleaned"] = chunks_cleaned
            
            cleaned_chunks = await loop.run_in_executor(
                None, 
                lambda: clean_all_chunks(chunks, progress_callback=update_cleaning_progress)
            )
            scraping_jobs[service_id]["progress"]["chunks_cleaned"] = len(cleaned_chunks)
            print(f"[{service_id}] Cleaned {len(cleaned_chunks)} chunks")
            
            # Step 4: Embed chunks
            scraping_jobs[service_id]["progress"]["step"] = "embedding"
            print(f"[{service_id}] Embedding chunks...")
            
            embedded_chunks = await loop.run_in_executor(None, embed_chunks, cleaned_chunks)
            scraping_jobs[service_id]["progress"]["chunks_embedded"] = len(embedded_chunks)
            print(f"[{service_id}] Embedded {len(embedded_chunks)} chunks")
            
            # Step 5: Upload to Qdrant
            scraping_jobs[service_id]["progress"]["step"] = "uploading"
            print(f"[{service_id}] Uploading to Qdrant collection '{collection_name}'...")
            
            total_points = await loop.run_in_executor(
                None,
                upload_to_qdrant,
                collection_name,
                embedded_chunks
            )
            scraping_jobs[service_id]["progress"]["chunks_uploaded"] = total_points
            print(f"[{service_id}] Uploaded {total_points} points to Qdrant")
            
            # Step 6: Update database with collection name
            scraping_jobs[service_id]["progress"]["step"] = "updating_database"
            print(f"[{service_id}] Updating database with collection name...")
            
            success = self.subscription_service_dao.update_qdrant_collection(
                service_id, 
                collection_name
            )
            
            if not success:
                print(f"[{service_id}] Warning: Failed to update database with collection name")
            
            # Complete
            scraping_jobs[service_id]["status"] = "completed"
            scraping_jobs[service_id]["progress"]["step"] = "completed"
            print(f"[{service_id}] Scraping pipeline completed successfully")
            
        except Exception as e:
            scraping_jobs[service_id]["status"] = "failed"
            scraping_jobs[service_id]["error"] = str(e)
            print(f"[{service_id}] Scraping pipeline failed: {e}")
    
    def get_scraping_status(self, service_id: str) -> Dict[str, Any]:
        """
        Get the status of a scraping job.
        
        Args:
            service_id: The service_id for the subscription service
            
        Returns:
            Dictionary with job status
        """
        if not service_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="service_id is required"
            )
        
        if service_id not in scraping_jobs:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No scraping job found for service_id {service_id}"
            )
        
        return scraping_jobs[service_id]
    
    def get_collection_status(self, service_id: str) -> Dict[str, Any]:
        """
        Get the status of the Qdrant collection for a service.
        
        Args:
            service_id: The service_id for the subscription service
            
        Returns:
            Dictionary with collection information
        """
        if not service_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="service_id is required"
            )
        
        # Get collection name from database
        collection_name = self.subscription_service_dao.get_qdrant_collection(service_id)
        
        if not collection_name:
            # Try generating the name
            collection_name = self._generate_collection_name(service_id)
        
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
    
    def delete_service_collection(self, service_id: str) -> Dict[str, Any]:
        """
        Delete the Qdrant collection for a service.
        
        Args:
            service_id: The service_id for the subscription service
            
        Returns:
            Dictionary with deletion status
        """
        if not service_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="service_id is required"
            )
        
        collection_name = self._generate_collection_name(service_id)
        
        if not collection_exists(collection_name):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Collection {collection_name} not found"
            )
        
        success = delete_collection(collection_name)
        
        if success:
            # Clear the collection name from database
            self.subscription_service_dao.update_qdrant_collection(service_id, None)
            
            return {
                "message": f"Collection {collection_name} deleted successfully",
                "collection_name": collection_name
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete collection {collection_name}"
            )
