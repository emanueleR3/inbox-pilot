"""Minimal Qdrant RAG helpers for the automations quiz service.

Uses Qdrant REST API via httpx (no qdrant-client dependency).
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import httpx
from openai import OpenAI


QDRANT_URL = os.getenv("QDRANT_URL") or "http://qdrant:6333"
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY") or None

OPENAI_EMBEDDING_MODEL = os.getenv("QUIZ_EMBEDDING_MODEL") or "text-embedding-3-small"


def embed_texts(texts: List[str], model: str = OPENAI_EMBEDDING_MODEL) -> List[List[float]]:
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    # OpenAI embeddings API accepts list input; returns in the same order.
    res = client.embeddings.create(model=model, input=texts)
    return [item.embedding for item in res.data]


def qdrant_search(
    collection_name: str,
    vector: List[float],
    limit: int = 5,
    score_threshold: Optional[float] = None,
) -> List[Dict[str, Any]]:
    headers: Dict[str, str] = {}
    if QDRANT_API_KEY:
        headers["api-key"] = QDRANT_API_KEY

    payload: Dict[str, Any] = {
        "vector": vector,
        "limit": limit,
        "with_payload": True,
    }
    if score_threshold is not None:
        payload["score_threshold"] = score_threshold

    url = f"{QDRANT_URL.rstrip('/')}/collections/{collection_name}/points/search"

    with httpx.Client(timeout=20.0, headers=headers) as http:
        r = http.post(url, json=payload)
        r.raise_for_status()
        data = r.json()

    # Qdrant REST search returns {"result": [...]} for older versions,
    # and {"result": [...]} in current versions too.
    results = data.get("result") or []
    out: List[Dict[str, Any]] = []
    for item in results:
        out.append({
            "score": item.get("score"),
            "payload": item.get("payload") or {},
        })
    return out


def format_top_chunks(results: List[Dict[str, Any]], max_chunks: int = 5) -> List[str]:
    """Extract chunk texts from Qdrant results WITHOUT truncation.
    
    We want to preserve all the information from the scraped content.
    """
    chunks: List[str] = []
    for r in results[:max_chunks]:
        payload = r.get("payload") or {}
        text = (
            payload.get("text")
            or payload.get("content")
            or payload.get("page_content")
            or payload.get("chunk")
            or ""
        ).strip()
        if not text:
            continue
        # NO TRUNCATION - preserve full chunk content
        chunks.append(text)
    return chunks
