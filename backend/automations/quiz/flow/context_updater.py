"""
Context Updater - Handles finalizing context updates when user saves.

This module:
1. Reads the original scraping JSON from server
2. Updates it with conversation changes via LLM
3. Saves as [name]_v2.json
4. Deletes old Qdrant collection
5. Creates new Qdrant collection with updated content
"""

import os
import json
import hashlib
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

from db_client import get_scraping_data, update_scraping_paths
from automations.quiz.flow.config import get_llm
from automations.quiz.prompts import (
    CONTEXT_JSON_UPDATE_SYSTEM_PROMPT,
    CONTEXT_JSON_UPDATE_USER_PROMPT_TEMPLATE,
)
from automations.quiz.models.llm_response import ContextJsonUpdateResponse


# Get scrapings directory from environment (mounted in K8s)
SCRAPINGS_DIR = os.getenv("SCRAPINGS_DIR", "/app/scrapings")


@dataclass
class Chunk:
    """Represents a text chunk with metadata (matches scraper module)."""
    id: str
    url: str
    title: str
    page_index: int
    chunk_index: int
    text: str
    deprecated: bool = False
    source: str = ""
    content_hash: str = ""


def read_scraping_json(json_path: str) -> Optional[List[Dict]]:
    """
    Read the scraping JSON file from server.
    
    Args:
        json_path: Path to the JSON file (from DB scraping_collection_path)
        
    Returns:
        List of dicts with url and content, or None if error
    """
    try:
        # Get the host path prefix from environment (for path conversion)
        SCRAPINGS_DB_DIR = os.getenv("SCRAPINGS_DB_DIR", "/home/deploy/corretto/data/scrapings")
        
        # Convert host path to container path
        # DB stores: /home/deploy/corretto/data/scrapings/scraper_xxx.json
        # Container needs: /app/scrapings/scraper_xxx.json
        if json_path.startswith(SCRAPINGS_DB_DIR):
            # Replace host path prefix with container path prefix
            relative_path = json_path[len(SCRAPINGS_DB_DIR):].lstrip("/")
            full_path = os.path.join(SCRAPINGS_DIR, relative_path)
            print(f"📂 [CONTEXT_UPDATER] Converted host path to container path: {full_path}")
        elif json_path.startswith("/"):
            # Absolute path but not host path - try to extract basename
            basename = os.path.basename(json_path)
            full_path = os.path.join(SCRAPINGS_DIR, basename)
            print(f"📂 [CONTEXT_UPDATER] Using basename from absolute path: {full_path}")
        else:
            # Relative path - use as-is in SCRAPINGS_DIR
            full_path = os.path.join(SCRAPINGS_DIR, json_path)
        
        # Fallback: try just the filename if path doesn't exist
        if not os.path.exists(full_path):
            basename = os.path.basename(json_path)
            fallback_path = os.path.join(SCRAPINGS_DIR, basename)
            print(f"⚠️ [CONTEXT_UPDATER] Path not found, trying fallback: {fallback_path}")
            if os.path.exists(fallback_path):
                full_path = fallback_path
        
        print(f"📂 [CONTEXT_UPDATER] Reading JSON from: {full_path}")
        
        with open(full_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"✅ [CONTEXT_UPDATER] Loaded {len(data)} items from JSON")
        return data
        
    except FileNotFoundError:
        print(f"❌ [CONTEXT_UPDATER] JSON file not found: {json_path}")
        print(f"   Tried path: {full_path}")
        print(f"   SCRAPINGS_DIR: {SCRAPINGS_DIR}")
        # List directory contents for debugging
        try:
            files = os.listdir(SCRAPINGS_DIR)
            print(f"   Available files in SCRAPINGS_DIR: {files}")
        except Exception:
            print(f"   Could not list SCRAPINGS_DIR")
        return None
    except json.JSONDecodeError as e:
        print(f"❌ [CONTEXT_UPDATER] Invalid JSON: {e}")
        return None
    except Exception as e:
        print(f"❌ [CONTEXT_UPDATER] Error reading JSON: {e}")
        return None


def update_json_with_llm(
    original_json: List[Dict],
    conversation_log: List[str],
    final_markdown: str
) -> Optional[List[Dict]]:
    """
    Use LLM to update the JSON with conversation changes.
    
    Args:
        original_json: Original scraped JSON
        conversation_log: List of change log entries
        final_markdown: Final confirmed markdown
        
    Returns:
        Updated JSON list, or None if error
    """
    try:
        print(f"🤖 [CONTEXT_UPDATER] Calling LLM to update JSON...")
        
        llm = get_llm(temperature=0.1)
        structured_llm = llm.with_structured_output(ContextJsonUpdateResponse, method="function_calling")
        
        # Format conversation log
        log_text = "\n".join([f"- {entry}" for entry in conversation_log]) if conversation_log else "(Nessuna modifica)"
        
        # Format original JSON
        original_json_text = json.dumps(original_json, indent=2, ensure_ascii=False)
        
        user_prompt = CONTEXT_JSON_UPDATE_USER_PROMPT_TEMPLATE.format(
            original_json=original_json_text,
            conversation_log=log_text,
            final_markdown=final_markdown
        )
        
        response: ContextJsonUpdateResponse = structured_llm.invoke([
            {"role": "system", "content": CONTEXT_JSON_UPDATE_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ])
        
        # Convert response to list of dicts
        updated_json = [{"url": item.url, "content": item.content} for item in response.updated_json]
        
        print(f"✅ [CONTEXT_UPDATER] LLM returned {len(updated_json)} updated items")
        return updated_json
        
    except Exception as e:
        print(f"❌ [CONTEXT_UPDATER] Error updating JSON with LLM: {e}")
        return None


def save_updated_json(original_path: str, updated_json: List[Dict]) -> Optional[str]:
    """
    Save the updated JSON as [name]_v2.json.
    
    Args:
        original_path: Original JSON path
        updated_json: Updated JSON data
        
    Returns:
        New file path, or None if error
    """
    try:
        # Generate new filename
        base_name = os.path.basename(original_path)
        name_without_ext = os.path.splitext(base_name)[0]
        
        # Add _v2 suffix (or increment if already has version)
        if "_v2" in name_without_ext:
            # Already has v2, increment to v3, v4, etc.
            parts = name_without_ext.rsplit("_v", 1)
            if len(parts) == 2 and parts[1].isdigit():
                new_version = int(parts[1]) + 1
                new_name = f"{parts[0]}_v{new_version}.json"
            else:
                new_name = f"{name_without_ext}_v2.json"
        else:
            new_name = f"{name_without_ext}_v2.json"
        
        new_path = os.path.join(SCRAPINGS_DIR, new_name)
        
        print(f"💾 [CONTEXT_UPDATER] Saving updated JSON to: {new_path}")
        
        with open(new_path, 'w', encoding='utf-8') as f:
            json.dump(updated_json, f, indent=2, ensure_ascii=False)
        
        print(f"✅ [CONTEXT_UPDATER] Saved updated JSON successfully")
        return new_path
        
    except Exception as e:
        print(f"❌ [CONTEXT_UPDATER] Error saving JSON: {e}")
        return None


def chunk_pages(pages: List[Dict]) -> List[Chunk]:
    """
    Chunk pages into smaller text chunks (simplified version).
    
    Args:
        pages: List of dicts with url and content
        
    Returns:
        List of Chunk objects
    """
    MAX_CHARS = 2000
    MIN_CHARS = 200
    
    all_chunks: List[Chunk] = []
    
    for page_index, page in enumerate(pages):
        content = page.get('content', '').strip()
        url = page.get('url', '')
        
        if not content:
            continue
        
        # If content is short enough, single chunk
        if len(content) < MAX_CHARS:
            chunk = Chunk(
                id=f"{page_index}_0",
                url=url,
                title="",
                page_index=page_index,
                chunk_index=0,
                text=content,
                deprecated=False,
                source="quiz_updated",
                content_hash=hashlib.sha256(content.encode('utf-8')).hexdigest(),
            )
            all_chunks.append(chunk)
        else:
            # Split by paragraphs
            paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
            current_text = ""
            chunk_index = 0
            
            for para in paragraphs:
                if len(current_text) + len(para) + 2 > MAX_CHARS:
                    if current_text:
                        chunk = Chunk(
                            id=f"{page_index}_{chunk_index}",
                            url=url,
                            title="",
                            page_index=page_index,
                            chunk_index=chunk_index,
                            text=current_text,
                            deprecated=False,
                            source="quiz_updated",
                            content_hash=hashlib.sha256(current_text.encode('utf-8')).hexdigest(),
                        )
                        all_chunks.append(chunk)
                        chunk_index += 1
                        current_text = para
                else:
                    current_text = f"{current_text}\n\n{para}" if current_text else para
            
            # Remaining text
            if current_text:
                chunk = Chunk(
                    id=f"{page_index}_{chunk_index}",
                    url=url,
                    title="",
                    page_index=page_index,
                    chunk_index=chunk_index,
                    text=current_text,
                    deprecated=False,
                    source="quiz_updated",
                    content_hash=hashlib.sha256(current_text.encode('utf-8')).hexdigest(),
                )
                all_chunks.append(chunk)
    
    print(f"🔪 [CONTEXT_UPDATER] Created {len(all_chunks)} chunks from {len(pages)} pages")
    return all_chunks


def embed_and_upload_to_qdrant(
    chunks: List[Chunk],
    collection_name: str
) -> Tuple[bool, int]:
    """
    Embed chunks and upload to Qdrant.
    
    Args:
        chunks: List of Chunk objects to embed
        collection_name: Name for the new Qdrant collection
        
    Returns:
        Tuple of (success, points_count)
    """
    try:
        from openai import OpenAI
        from qdrant_client import QdrantClient
        from qdrant_client.models import Distance, VectorParams, Batch
        
        QDRANT_URL = os.getenv("QDRANT_URL", "http://qdrant:6333")
        QDRANT_API_KEY = os.getenv("QDRANT_API_KEY") or None
        EMBEDDING_MODEL = os.getenv("QUIZ_EMBEDDING_MODEL", "text-embedding-3-small")
        VECTOR_SIZE = 1536  # text-embedding-3-small
        
        print(f"🔗 [CONTEXT_UPDATER] Connecting to Qdrant at: {QDRANT_URL}")
        
        # Initialize clients
        openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        qdrant_client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
        
        # Embed all chunks
        texts = [chunk.text for chunk in chunks]
        print(f"🧠 [CONTEXT_UPDATER] Embedding {len(texts)} chunks...")
        
        # Batch embeddings (max 2048 per request)
        all_vectors = []
        batch_size = 100
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]
            response = openai_client.embeddings.create(model=EMBEDDING_MODEL, input=batch_texts)
            batch_vectors = [item.embedding for item in response.data]
            all_vectors.extend(batch_vectors)
            print(f"   Embedded {len(all_vectors)}/{len(texts)} chunks...")
        
        # Create collection
        print(f"📦 [CONTEXT_UPDATER] Creating collection: {collection_name}")
        qdrant_client.recreate_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=VECTOR_SIZE,
                distance=Distance.COSINE,
            ),
        )
        
        # Upload points
        ids = list(range(1, len(chunks) + 1))
        payloads = [
            {
                "url": chunk.url,
                "title": chunk.title,
                "page_index": chunk.page_index,
                "chunk_index": chunk.chunk_index,
                "source": chunk.source,
                "text": chunk.text,
                "deprecated": chunk.deprecated,
                "content_hash": chunk.content_hash
            }
            for chunk in chunks
        ]
        
        points = Batch(ids=ids, vectors=all_vectors, payloads=payloads)
        qdrant_client.upsert(collection_name=collection_name, points=points)
        
        print(f"✅ [CONTEXT_UPDATER] Uploaded {len(chunks)} points to collection: {collection_name}")
        return True, len(chunks)
        
    except Exception as e:
        print(f"❌ [CONTEXT_UPDATER] Error embedding/uploading to Qdrant: {e}")
        return False, 0


def delete_qdrant_collection(collection_name: str) -> bool:
    """
    Delete a Qdrant collection.
    
    Args:
        collection_name: Name of the collection to delete
        
    Returns:
        True if successful
    """
    try:
        from qdrant_client import QdrantClient
        
        QDRANT_URL = os.getenv("QDRANT_URL", "http://qdrant:6333")
        QDRANT_API_KEY = os.getenv("QDRANT_API_KEY") or None
        
        client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
        client.delete_collection(collection_name=collection_name)
        
        print(f"🗑️ [CONTEXT_UPDATER] Deleted collection: {collection_name}")
        return True
        
    except Exception as e:
        print(f"❌ [CONTEXT_UPDATER] Error deleting collection: {e}")
        return False


def finalize_context_update(
    email: str,
    conversation_log: List[str],
    final_markdown: str
) -> bool:
    """
    Main function to finalize context update when user saves.
    
    1. Fetch scraping_collection_path from DB
    2. Read JSON from server path
    3. Call LLM to update JSON based on conversation_log + markdown
    4. Save as [original_name]_v2.json
    5. Delete old Qdrant collection
    6. Chunk, embed, and upload to new Qdrant collection
    7. Update DB with new paths
    
    Args:
        email: User email (key in subscription_services)
        conversation_log: List of change log entries from quiz
        final_markdown: Final confirmed markdown
        
    Returns:
        True if successful
    """
    print(f"\n{'='*60}")
    print(f"🔄 [CONTEXT_UPDATER] Starting context update for: {email}")
    print(f"{'='*60}")
    
    # Step 1: Get scraping data from DB
    scraping_data = get_scraping_data(email)
    if not scraping_data:
        print(f"❌ [CONTEXT_UPDATER] No scraping data found for email: {email}")
        return False
    
    original_json_path = scraping_data.get("scraping_collection_path")
    old_collection_name = scraping_data.get("qdrant_collection")
    
    if not original_json_path:
        print(f"❌ [CONTEXT_UPDATER] No scraping_collection_path in DB")
        return False
    
    print(f"📄 Original JSON path: {original_json_path}")
    print(f"📦 Old collection: {old_collection_name}")
    
    # Step 2: Read original JSON
    original_json = read_scraping_json(original_json_path)
    if not original_json:
        print(f"❌ [CONTEXT_UPDATER] Failed to read original JSON")
        return False
    
    # Step 3: Update JSON with LLM
    updated_json = update_json_with_llm(original_json, conversation_log, final_markdown)
    if not updated_json:
        print(f"❌ [CONTEXT_UPDATER] Failed to update JSON with LLM")
        return False
    
    # Step 4: Save updated JSON
    new_json_path = save_updated_json(original_json_path, updated_json)
    if not new_json_path:
        print(f"❌ [CONTEXT_UPDATER] Failed to save updated JSON")
        return False
    
    # Step 5: Delete old Qdrant collection
    if old_collection_name:
        delete_qdrant_collection(old_collection_name)
    
    # Step 6: Create new collection
    # Generate new collection name
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    email_safe = email.replace("@", "_at_").replace(".", "_")
    new_collection_name = f"quiz_updated_{email_safe}_{timestamp}"
    
    chunks = chunk_pages(updated_json)
    if not chunks:
        print(f"⚠️ [CONTEXT_UPDATER] No chunks to upload")
    else:
        success, points_count = embed_and_upload_to_qdrant(chunks, new_collection_name)
        if not success:
            print(f"❌ [CONTEXT_UPDATER] Failed to create new Qdrant collection")
            return False
    
    # Step 7: Update DB with new paths
    # Store the full host path for DB (using SCRAPINGS_DB_DIR)
    SCRAPINGS_DB_DIR = os.getenv("SCRAPINGS_DB_DIR", "/home/deploy/corretto/data/scrapings")
    new_json_path_for_db = os.path.join(SCRAPINGS_DB_DIR, os.path.basename(new_json_path))
    
    if not update_scraping_paths(email, new_json_path_for_db, new_collection_name):
        print(f"❌ [CONTEXT_UPDATER] Failed to update DB paths")
        return False
    
    print(f"\n{'='*60}")
    print(f"✅ [CONTEXT_UPDATER] Context update completed successfully!")
    print(f"   New JSON: {new_json_path}")
    print(f"   New collection: {new_collection_name}")
    print(f"{'='*60}\n")
    
    return True


__all__ = [
    "finalize_context_update",
    "read_scraping_json",
    "update_json_with_llm",
    "save_updated_json",
    "chunk_pages",
    "embed_and_upload_to_qdrant",
    "delete_qdrant_collection",
]
