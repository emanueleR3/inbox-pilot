"""Text chunking utilities for splitting content into manageable pieces."""

from dataclasses import dataclass
from typing import List

from src.modules.scraper.src.models.config import (
    MAX_CHARS,
    OVERLAP_CHARS,
    THRESHOLD_NO_CHUNKING,
    MIN_CHARS
)


@dataclass
class Chunk:
    """Represents a text chunk with metadata."""
    id: str
    url: str
    title: str
    page_index: int
    chunk_index: int
    text: str


def chunk_text(text: str, max_chars: int = MAX_CHARS, overlap: int = OVERLAP_CHARS) -> List[str]:
    """
    Chunk text by paragraphs with overlap between consecutive chunks.
    Works for any text with \\n\\n between paragraphs.
    
    Args:
        text: Text to chunk
        max_chars: Maximum characters per chunk
        overlap: Overlap characters between chunks
        
    Returns:
        List of text chunks
    """
    text = text.strip()
    if not text:
        return []

    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: List[str] = []
    current_paras: List[str] = []
    current_len = 0

    def flush_chunk():
        nonlocal current_paras, current_len
        if current_paras:
            chunk = "\n\n".join(current_paras).strip()
            if chunk:
                chunks.append(chunk)
            current_paras = []
            current_len = 0

    for i, para in enumerate(paragraphs):
        para_len = len(para)

        # Large single paragraph - split by characters
        if para_len > max_chars:
            flush_chunk()

            start = 0
            while start < para_len:
                end = min(start + max_chars, para_len)
                big_chunk = para[start:end].strip()
                if big_chunk:
                    chunks.append(big_chunk)
                start = end
            continue

        # If adding this paragraph exceeds limit, close chunk
        if current_len + para_len + (2 if current_paras else 0) > max_chars:
            flush_chunk()

            # Overlap: carry over last paragraph from previous chunk
            if chunks and overlap > 0:
                last_chunk = chunks[-1]
                last_chunk_paras = [p.strip() for p in last_chunk.split("\n\n") if p.strip()]
                if last_chunk_paras:
                    overlap_para = last_chunk_paras[-1]
                    current_paras = [overlap_para]
                    current_len = len(overlap_para)

        # Add paragraph to current chunk
        if not current_paras:
            current_paras = [para]
            current_len = para_len
        else:
            current_paras.append(para)
            current_len += para_len + 2  # +2 for "\n\n"

    # Final flush
    flush_chunk()

    # Merge tiny last chunk with previous if too small
    if len(chunks) >= 2 and len(chunks[-1]) < MIN_CHARS:
        last = chunks.pop()
        chunks[-1] = (chunks[-1] + "\n\n" + last).strip()

    return chunks


def chunk_pages(pages: List[dict]) -> List[Chunk]:
    """
    Chunk a list of scraped pages into smaller text chunks.
    
    Args:
        pages: List of page dictionaries with 'url', 'title', 'content'
        
    Returns:
        List of Chunk objects
    """
    all_chunks: List[Chunk] = []
    
    for page_index, page in enumerate(pages):
        content = page.get('content', '').strip()
        url = page.get('url', '')
        title = page.get('title', '')
        
        if not content:
            continue
            
        # If page is short, single chunk
        if len(content) < THRESHOLD_NO_CHUNKING:
            page_chunks = [content]
        else:
            page_chunks = chunk_text(content)

        for chunk_index, chunk_text_content in enumerate(page_chunks):
            chunk = Chunk(
                id=f"{page_index}_{chunk_index}",
                url=url,
                title=title,
                page_index=page_index,
                chunk_index=chunk_index,
                text=chunk_text_content
            )
            all_chunks.append(chunk)
    
    return all_chunks
