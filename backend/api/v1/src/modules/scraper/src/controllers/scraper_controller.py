"""Scraper controller for handling website scraping operations."""

from fastapi import HTTPException, status, BackgroundTasks
from typing import Optional, Dict, Any
import asyncio
import re
import uuid
import os
import json
import socket
import traceback
from urllib.parse import urlparse
from pathlib import Path
from dotenv import load_dotenv

from src.core.DAO.subscription_service_dao import SubscriptionServiceDAO
from src.modules.scraper.src.utils.scraping import (
    ScrapedPage,
    discover_website_urls,
    scrape_selected_urls,
)
from src.modules.scraper.src.utils.chunking import chunk_pages, Chunk
from src.modules.scraper.src.utils.cleaning import clean_all_pages
from src.modules.scraper.src.utils.embedding import embed_chunks
from src.modules.scraper.src.utils.qdrant_utils import (
    upload_to_qdrant,
    delete_collection,
    collection_exists,
    get_collection_info,
    QDRANT_URL as EFFECTIVE_QDRANT_URL,
)

load_dotenv()

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

    def _scrapings_dir(self) -> Path:
        # Keep the default aligned with the Kubernetes deployment volumeMount.
        return Path(os.getenv("SCRAPINGS_DIR", "/app/scrapings"))

    def _scrapings_filename(self, email: str) -> str:
        clean_mail = (email or "").strip().lower().replace(".", "_").replace("@", "_at_")
        return f"scraper_{clean_mail}.json"

    def _write_scrapings_json(self, email: str, pages: list[dict]) -> str:
        """Write cleaned pages to the mounted scrapings directory (atomic)."""
        out_dir = self._scrapings_dir()
        try:
            # Do NOT create missing parents (e.g. '/data') because some deployments
            # run with a read-only root filesystem; the mount should provide the directory.
            out_dir.mkdir(parents=False, exist_ok=True)
        except Exception as e:
            raise RuntimeError(
                f"SCRAPINGS_DIR is not writable or does not exist: {out_dir}. "
                f"Ensure the Kubernetes volume is mounted there. Underlying error: {e}"
            )
        out_path = out_dir / self._scrapings_filename(email)
        tmp_path = out_path.with_suffix(out_path.suffix + ".tmp")

        payload = [{"url": p.get("url", ""), "content": p.get("content", "")} for p in (pages or [])]
        with tmp_path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        tmp_path.replace(out_path)
        return str(out_path)

    def _scrapings_db_path(self, email: str, container_path: str) -> str:
        """Return the path to store in DB.

        By default we store the container path.
        If SCRAPINGS_DB_DIR is set, we store a host-visible path (string only).
        """
        db_dir = (os.getenv("SCRAPINGS_DB_DIR") or "").strip()
        if not db_dir:
            return container_path
        return str(Path(db_dir) / self._scrapings_filename(email))

    def debug_snapshot(self, email: Optional[str] = None) -> Dict[str, Any]:
        """Temporary diagnostic snapshot for mount + Qdrant connectivity."""
        debug_enabled = os.getenv("SCRAPER_DEBUG", "").strip().lower() in {"1", "true", "yes"}
        if not debug_enabled:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Debug endpoint disabled. Set SCRAPER_DEBUG=true to enable temporarily.",
            )

        out_dir = self._scrapings_dir()
        result: Dict[str, Any] = {
            "pod": {
                "hostname": os.getenv("HOSTNAME"),
            },
            "env": {
                "QDRANT_URL": os.getenv("QDRANT_URL"),
                "SCRAPINGS_DIR": os.getenv("SCRAPINGS_DIR"),
            },
            "scrapings_dir": {
                "path": str(out_dir),
                "exists": out_dir.exists(),
                "is_dir": out_dir.is_dir(),
                "list": [],
                "writable": False,
                "write_error": None,
            },
            "scrapings_file": None,
            "qdrant": {
                "url": os.getenv("QDRANT_URL"),
                "effective_url": EFFECTIVE_QDRANT_URL,
                "parsed": None,
                "dns": None,
                "tcp_connect": None,
                "client_get_collections": None,
            },
        }

        # Filesystem checks
        try:
            if out_dir.exists() and out_dir.is_dir():
                result["scrapings_dir"]["list"] = sorted([p.name for p in out_dir.iterdir()])[:50]
            # writability test
            test_path = out_dir / ".__writetest__"
            test_path.write_text("ok", encoding="utf-8")
            test_path.unlink(missing_ok=True)
            result["scrapings_dir"]["writable"] = True
        except Exception as e:
            result["scrapings_dir"]["write_error"] = f"{type(e).__name__}: {e}"

        if email:
            expected = out_dir / self._scrapings_filename(email)
            file_info: Dict[str, Any] = {
                "email": self._normalize_email_key(email),
                "expected_path": str(expected),
                "exists": expected.exists(),
                "size": None,
            }
            try:
                if expected.exists():
                    file_info["size"] = expected.stat().st_size
            except Exception as e:
                file_info["size"] = f"error: {type(e).__name__}: {e}"
            result["scrapings_file"] = file_info

        # Qdrant connectivity checks
        qurl = os.getenv("QDRANT_URL", "").strip()
        try:
            parsed = urlparse(qurl)
            host = parsed.hostname
            port = parsed.port or (443 if parsed.scheme == "https" else 80)
            result["qdrant"]["parsed"] = {
                "scheme": parsed.scheme,
                "host": host,
                "port": port,
                "path": parsed.path,
            }

            # DNS
            dns_info = []
            if host:
                for fam, stype, proto, canon, sockaddr in socket.getaddrinfo(host, port, proto=socket.IPPROTO_TCP):
                    dns_info.append({"family": fam, "socktype": stype, "proto": proto, "sockaddr": sockaddr})
            result["qdrant"]["dns"] = dns_info[:10]

            # TCP connect
            tcp_ok = False
            tcp_err = None
            if host:
                try:
                    with socket.create_connection((host, port), timeout=2.5):
                        tcp_ok = True
                except Exception as e:
                    tcp_err = f"{type(e).__name__}: {e}"
            result["qdrant"]["tcp_connect"] = {"ok": tcp_ok, "error": tcp_err}

            # Qdrant client check (collections)
            try:
                from src.modules.scraper.src.utils.qdrant_utils import get_qdrant_client

                client = get_qdrant_client()
                cols = client.get_collections()
                result["qdrant"]["client_get_collections"] = {
                    "ok": True,
                    "count": len(cols.collections),
                    "names": [c.name for c in cols.collections][:25],
                }
            except Exception as e:
                result["qdrant"]["client_get_collections"] = {
                    "ok": False,
                    "error": f"{type(e).__name__}: {e}",
                }
        except Exception as e:
            result["qdrant"]["parsed"] = None
            result["qdrant"]["dns"] = None
            result["qdrant"]["tcp_connect"] = {"ok": False, "error": f"{type(e).__name__}: {e}"}

        return result

    async def discover_urls(self, website_url: str, max_urls: int = 200) -> Dict[str, Any]:
        """Discover website URLs for the pre-scrape selection step."""
        if not website_url:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="website_url is required",
            )

        print(f"[discover_urls] start: {website_url} (max_urls={max_urls})")
        loop = asyncio.get_running_loop()
        urls = await loop.run_in_executor(None, lambda: discover_website_urls(website_url, max_urls=max_urls))
        print(f"[discover_urls] done: {len(urls)} urls")
        return {
            "website_url": website_url,
            "urls": urls,
            "count": len(urls),
        }
    
    async def start_scraping(
        self, 
        email: str, 
        website_url: str,
        urls: list[str],
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

        if not urls:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="urls is required and must be a non-empty array",
            )
        
        # Verify service exists
        service = self.subscription_service_dao.get_service_by_email(email_key)
        if not service:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Service with email {email_key} not found"
            )
        
        collection_name = self._generate_collection_name(email_key)
        
        # Save website URL to subscriptions table
        try:
            ok = self.subscription_service_dao.update_subscription_website_by_email(email_key, website_url)
            if not ok:
                print(f"[{email_key}] Warning: Failed to update website URL in subscriptions table")
        except Exception as e:
            print(f"[{email_key}] Warning: Error updating website URL: {e}")
        
        # Initialize job status
        scraping_jobs[email_key] = {
            "status": "started",
            "website_url": website_url,
            "collection_name": collection_name,
            "progress": {
                "step": "initializing",
                "current_url": "",
                "pages_scraped": 0,
                "pages_cleaned": 0,
                "chunks_created": 0,
                "chunks_embedded": 0,
                "chunks_uploaded": 0
            },
            "export": {
                "scrapings_json_path": None,
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
                urls,
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
                urls,
            )
            return scraping_jobs.get(email_key, {})
    
    async def _run_scraping_pipeline(
        self,
        email: str,
        website_url: str,
        collection_name: str,
        urls: list[str],
    ):
        """
        Run the complete scraping pipeline: scrape -> chunk -> clean -> embed -> upload.
        """
        try:
            # DEBUG header: print runtime env that can explain "connection refused" / missing files
            print(
                f"[{email}] DEBUG env: QDRANT_URL={os.getenv('QDRANT_URL')} "
                f"(effective={EFFECTIVE_QDRANT_URL}) SCRAPINGS_DIR={os.getenv('SCRAPINGS_DIR')} "
                f"(effective={self._scrapings_dir()})"
            )
            # Step 1: Scrape selected URLs
            scraping_jobs[email]["progress"]["step"] = "scraping"
            scraping_jobs[email]["progress"]["current_url"] = website_url
            print(f"[{email}] Starting scraping for {website_url}")
            
            # Define progress callback to update status in real-time
            def update_scraping_progress(pages_scraped: int, current_url: str):
                scraping_jobs[email]["progress"]["pages_scraped"] = pages_scraped
                scraping_jobs[email]["progress"]["current_url"] = current_url
            
            # Run scraping in thread pool to not block
            loop = asyncio.get_running_loop()
            pages = await loop.run_in_executor(
                None, 
                lambda: scrape_selected_urls(urls, update_scraping_progress)
            )
            
            scraping_jobs[email]["progress"]["pages_scraped"] = len(pages)
            print(f"[{email}] Scraped {len(pages)} pages")
            
            if not pages:
                scraping_jobs[email]["status"] = "completed"
                scraping_jobs[email]["progress"]["step"] = "completed_no_content"
                return
            
            # Convert ScrapedPage to dict
            pages_dict = [{"url": p.url, "title": p.title, "content": p.content} for p in pages]

            # Step 2: Clean pages with LLM (once, before chunking)
            scraping_jobs[email]["progress"]["step"] = "page_cleaning"
            print(f"[{email}] Cleaning pages with LLM...")

            def update_pages_cleaned(pages_cleaned: int):
                scraping_jobs[email]["progress"]["pages_cleaned"] = pages_cleaned

            cleaned_pages = await loop.run_in_executor(
                None,
                lambda: clean_all_pages(pages_dict, progress_callback=update_pages_cleaned),
            )

            # Best-effort: if cleaning returns empty (e.g. no OPENAI_API_KEY), fall back
            pages_for_chunking = cleaned_pages if cleaned_pages else pages_dict

            # Step 3: Save cleaned pages JSON export to mounted scrapings folder
            scraping_jobs[email]["progress"]["step"] = "exporting_json"
            print(f"[{email}] Exporting scrapings JSON...")
            export_path = await loop.run_in_executor(
                None,
                lambda: self._write_scrapings_json(email, pages_for_chunking),
            )
            scraping_jobs[email]["export"]["scrapings_json_path"] = export_path
            try:
                p = Path(export_path)
                print(f"[{email}] Exported JSON path={export_path} exists={p.exists()} size={p.stat().st_size if p.exists() else None}")
            except Exception as e:
                print(f"[{email}] Warning: cannot stat exported JSON: {type(e).__name__}: {e}")

            # Persist JSON export path on DB (unique by email)
            try:
                db_path = self._scrapings_db_path(email, export_path)
                ok = self.subscription_service_dao.update_scraping_collection_path_by_email(email, db_path)
                if not ok:
                    print(f"[{email}] Warning: Failed to update scraping_collection_path")
            except Exception as e:
                print(f"[{email}] Warning: Error updating scraping_collection_path: {e}")
            
            # Step 4: Chunk pages
            scraping_jobs[email]["progress"]["step"] = "chunking"
            print(f"[{email}] Chunking pages...")
            
            chunks = await loop.run_in_executor(None, chunk_pages, pages_for_chunking)
            scraping_jobs[email]["progress"]["chunks_created"] = len(chunks)
            print(f"[{email}] Created {len(chunks)} chunks")
            
            if not chunks:
                scraping_jobs[email]["status"] = "completed"
                scraping_jobs[email]["progress"]["step"] = "completed_no_chunks"
                return
            
            # Step 5: Embed chunks
            scraping_jobs[email]["progress"]["step"] = "embedding"
            print(f"[{email}] Embedding chunks...")
            
            embedded_chunks = await loop.run_in_executor(None, embed_chunks, chunks)
            scraping_jobs[email]["progress"]["chunks_embedded"] = len(embedded_chunks)
            print(f"[{email}] Embedded {len(embedded_chunks)} chunks")
            
            # Step 6: Upload to Qdrant
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
            
            # Step 7: Update database with collection name
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
            print(f"[{email}] Traceback:\n{traceback.format_exc()}")

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
