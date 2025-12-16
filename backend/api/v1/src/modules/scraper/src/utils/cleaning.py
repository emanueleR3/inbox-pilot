"""Text cleaning utilities using LLM for improving chunk quality."""

import os
from typing import List
import hashlib
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

from src.modules.scraper.src.utils.chunking import Chunk
from src.modules.scraper.src.models.config import (
    LLM_MODEL,
    LLM_TEMPERATURE,
    CLEANING_BATCH_SIZE
)
from src.modules.scraper.src.models.llm_prompts import (
    CLEANING_SYSTEM_PROMPT,
    CLEANING_USER_PROMPT_TEMPLATE
)
from src.modules.scraper.src.models.llm_response import CleanedChunkResponse

load_dotenv()


# LangSmith configuration
os.environ["LANGCHAIN_TRACING_V2"] = os.getenv("LANGCHAIN_TRACING_V2", "true")
os.environ["LANGCHAIN_API_KEY"] = os.getenv("LANGCHAIN_API_KEY", "")
os.environ["LANGCHAIN_ENDPOINT"] = os.getenv("LANGCHAIN_ENDPOINT", "https://api.smith.langchain.com")
os.environ["LANGCHAIN_PROJECT"] = os.getenv("LANGCHAIN_PROJECT", "corretto_scraper")


def init_llm() -> ChatOpenAI:
    """
    Initialize LLM via LangChain with structured output.
    """
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY not set in environment.")

    llm = ChatOpenAI(
        model=LLM_MODEL,
        temperature=LLM_TEMPERATURE,
    )
    return llm.with_structured_output(CleanedChunkResponse)


def build_user_prompt(raw_text: str) -> str:
    """Build user prompt for text cleaning."""
    return CLEANING_USER_PROMPT_TEMPLATE.format(text=raw_text)


def clean_chunks_batch(llm, chunks: List[Chunk]) -> List[Chunk]:
    """
    Clean a batch of chunks using LLM.
    
    Args:
        llm: The LLM instance with structured output
        chunks: List of chunks to clean
        
    Returns:
        List of cleaned chunks
    """
    if not chunks:
        return []

    # Prepare messages for each chunk
    messages_list = []
    for chunk in chunks:
        messages_list.append([
            {"role": "system", "content": CLEANING_SYSTEM_PROMPT},
            {"role": "user", "content": build_user_prompt(chunk.text)},
        ])

    # Batch call to model
    responses: List[CleanedChunkResponse] = llm.batch(messages_list)

    # Update chunks with cleaned text (preserve metadata)
    cleaned_chunks = []
    for chunk, resp in zip(chunks, responses):
        cleaned_text = (resp.cleaned_text or "").strip()
        cleaned_chunk = Chunk(
            id=chunk.id,
            url=chunk.url,
            title=chunk.title,
            page_index=chunk.page_index,
            chunk_index=chunk.chunk_index,
            text=cleaned_text,
            deprecated=chunk.deprecated,
            source=chunk.source,
            content_hash=hashlib.sha256(cleaned_text.encode("utf-8")).hexdigest() if cleaned_text else "",
        )
        cleaned_chunks.append(cleaned_chunk)

    return cleaned_chunks


def clean_all_chunks(
    chunks: List[Chunk], 
    batch_size: int = CLEANING_BATCH_SIZE,
    progress_callback: callable = None
) -> List[Chunk]:
    """
    Clean all chunks using LLM in batches.
    
    Args:
        chunks: List of chunks to clean
        batch_size: Number of chunks to process per batch
        progress_callback: Optional callback function to report progress.
                          Called with (chunks_cleaned: int)
        
    Returns:
        List of cleaned chunks
    """
    llm = init_llm()
    all_cleaned: List[Chunk] = []
    
    count = 0
    batch: List[Chunk] = []

    for chunk in chunks:
        if not chunk.text.strip():
            continue

        batch.append(chunk)

        if len(batch) >= batch_size:
            print(f"[{count}] Cleaning batch of {len(batch)} chunks...")
            cleaned_batch = clean_chunks_batch(llm, batch)
            all_cleaned.extend(cleaned_batch)
            count += len(batch)
            batch = []
            
            # Report progress via callback
            if progress_callback:
                progress_callback(count)

    # Process remaining batch
    if batch:
        print(f"[{count}] Cleaning final batch of {len(batch)} chunks...")
        cleaned_batch = clean_chunks_batch(llm, batch)
        all_cleaned.extend(cleaned_batch)
        count += len(batch)
        
        # Report final progress
        if progress_callback:
            progress_callback(count)

    print(f"Cleaning completed. Total chunks cleaned: {count}")
    return all_cleaned
