"""Embedding utilities for generating vector embeddings from text chunks."""

import os
from typing import List, Tuple
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings

from src.modules.scraper.src.utils.chunking import Chunk
from src.modules.scraper.src.models.config import EMBEDDING_MODEL, EMBEDDING_BATCH_SIZE

load_dotenv()


def init_embeddings() -> OpenAIEmbeddings:
    """
    Initialize OpenAI embedding model via LangChain.
    """
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY not set in environment.")

    return OpenAIEmbeddings(model=EMBEDDING_MODEL)


def embed_chunks(chunks: List[Chunk], batch_size: int = EMBEDDING_BATCH_SIZE) -> List[Tuple[Chunk, List[float]]]:
    """
    Generate embeddings for all chunks.
    
    Args:
        chunks: List of chunks to embed
        batch_size: Number of chunks to process per batch
        
    Returns:
        List of tuples (chunk, embedding_vector)
    """
    embeddings_model = init_embeddings()
    results: List[Tuple[Chunk, List[float]]] = []
    
    buffer: List[Chunk] = []

    for chunk in chunks:
        buffer.append(chunk)

        if len(buffer) >= batch_size:
            texts = [c.text for c in buffer]
            vectors = embeddings_model.embed_documents(texts)
            
            for c, v in zip(buffer, vectors):
                results.append((c, v))
            
            print(f"Embedded {len(results)} chunks so far...")
            buffer = []

    # Process remaining buffer
    if buffer:
        texts = [c.text for c in buffer]
        vectors = embeddings_model.embed_documents(texts)
        
        for c, v in zip(buffer, vectors):
            results.append((c, v))

    print(f"Embedding completed. Total chunks embedded: {len(results)}")
    return results
