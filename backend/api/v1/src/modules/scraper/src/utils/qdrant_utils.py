"""Qdrant utilities for storing and querying vector embeddings."""

import os
from typing import List, Tuple, Optional
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, Batch, ScoredPoint

from src.modules.scraper.src.utils.chunking import Chunk
from src.modules.scraper.src.models.config import QDRANT_BATCH_SIZE, DEFAULT_VECTOR_SIZE

load_dotenv()

# Configuration from environment
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY") or None


def get_qdrant_client() -> QdrantClient:
    """Get Qdrant client instance."""
    return QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)


def create_collection(collection_name: str, vector_size: int = DEFAULT_VECTOR_SIZE) -> bool:
    """
    Create or recreate a Qdrant collection.
    
    Args:
        collection_name: Name of the collection
        vector_size: Dimension of vectors (1536 for text-embedding-3-small)
        
    Returns:
        True if successful
    """
    client = get_qdrant_client()
    
    print(f"Creating/recreating collection '{collection_name}'...")
    client.recreate_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(
            size=vector_size,
            distance=Distance.COSINE,
        ),
    )
    
    return True


def upload_to_qdrant(
    collection_name: str, 
    embedded_chunks: List[Tuple[Chunk, List[float]]],
    batch_size: int = QDRANT_BATCH_SIZE
) -> int:
    """
    Upload embedded chunks to Qdrant.
    
    Args:
        collection_name: Name of the collection
        embedded_chunks: List of (chunk, vector) tuples
        batch_size: Number of points per batch
        
    Returns:
        Total number of points uploaded
    """
    if not embedded_chunks:
        return 0
        
    client = get_qdrant_client()
    
    # Get vector size from first embedding
    vector_size = len(embedded_chunks[0][1])
    
    # Create collection
    create_collection(collection_name, vector_size)
    
    total_points = 0
    next_id = 1
    
    # Process in batches
    for i in range(0, len(embedded_chunks), batch_size):
        batch = embedded_chunks[i:i + batch_size]
        batch_size_actual = len(batch)
        
        ids = list(range(next_id, next_id + batch_size_actual))
        next_id += batch_size_actual
        
        vectors = [v for _, v in batch]
        payloads = []
        
        for chunk, _ in batch:
            payload = {
                "url": chunk.url,
                "title": chunk.title,
                "page_index": chunk.page_index,
                "chunk_index": chunk.chunk_index,
                "text": chunk.text,
            }
            payloads.append(payload)
        
        points = Batch(
            ids=ids,
            vectors=vectors,
            payloads=payloads,
        )
        
        client.upsert(
            collection_name=collection_name,
            points=points,
        )
        
        total_points += batch_size_actual
        print(f"Uploaded batch: {batch_size_actual} points (total: {total_points})")
    
    print(f"Upload completed. Total points in '{collection_name}': {total_points}")
    return total_points


def delete_collection(collection_name: str) -> bool:
    """
    Delete a Qdrant collection.
    
    Args:
        collection_name: Name of the collection to delete
        
    Returns:
        True if successful
    """
    client = get_qdrant_client()
    
    try:
        client.delete_collection(collection_name=collection_name)
        print(f"Collection '{collection_name}' deleted successfully.")
        return True
    except Exception as e:
        print(f"Error deleting collection: {e}")
        return False


def collection_exists(collection_name: str) -> bool:
    """
    Check if a collection exists.
    
    Args:
        collection_name: Name of the collection
        
    Returns:
        True if collection exists
    """
    client = get_qdrant_client()
    
    try:
        collections = client.get_collections()
        return any(c.name == collection_name for c in collections.collections)
    except Exception as e:
        print(f"Error checking collection: {e}")
        return False


def query_collection(
    collection_name: str, 
    query_vector: List[float], 
    limit: int = 10
) -> List[ScoredPoint]:
    """
    Query a collection for similar vectors.
    
    Args:
        collection_name: Name of the collection
        query_vector: Query vector
        limit: Number of results to return
        
    Returns:
        List of scored points
    """
    client = get_qdrant_client()
    
    result = client.query_points(
        collection_name=collection_name,
        query=query_vector,
        limit=limit,
        with_payload=True,
    )
    
    return result.points


def get_collection_info(collection_name: str) -> Optional[dict]:
    """
    Get information about a collection.
    
    Args:
        collection_name: Name of the collection
        
    Returns:
        Collection info dict or None
    """
    client = get_qdrant_client()
    
    try:
        info = client.get_collection(collection_name=collection_name)
        return {
            "name": collection_name,
            "points_count": info.points_count,
            "vectors_count": info.vectors_count,
            "status": info.status.value if info.status else "unknown"
        }
    except Exception as e:
        print(f"Error getting collection info: {e}")
        return None
