import os
import json
from typing import Dict, Any, Iterable, List

from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings

# -----------------------------
# CONFIG
# -----------------------------
CHUNKS_FILE = "chunks.jsonl"
OUTPUT_FILE = "qdrant_batches.jsonl"   # <--- RISULTATO QUI
BATCH_SIZE = 64                        # numero di punti per batch Qdrant
EMBEDDING_MODEL = "text-embedding-3-small"  # o "text-embedding-3-small"


def load_chunks(path: str) -> Iterable[Dict[str, Any]]:
    """Legge il jsonl di chunk e restituisce un dict per riga."""
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)


def init_embeddings() -> OpenAIEmbeddings:
    """
    Inizializza il modello di embedding OpenAI via LangChain.

    LangSmith si aggancia automaticamente grazie alle variabili:
    - LANGCHAIN_API_KEY
    - LANGCHAIN_TRACING_V2
    - LANGCHAIN_ENDPOINT
    - LANGCHAIN_PROJECT
    """
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY non impostata nell'ambiente.")

    embeddings = OpenAIEmbeddings(
        model=EMBEDDING_MODEL,
    )
    return embeddings


def build_qdrant_batch(
    records: List[Dict[str, Any]], vectors: List[List[float]]
) -> Dict[str, Any]:
    """
    Costruisce un payload batch compatibile con Qdrant:

    {
        "batch": {
            "ids": [...],
            "vectors": [...],
            "payloads": [...]
        }
    }
    """
    ids = []
    payloads = []

    for rec, vec in zip(records, vectors):
        ids.append(rec["id"])

        payload = {
            "url": rec.get("url"),
            "title": rec.get("title"),
            "page_index": rec.get("page_index"),
            "chunk_index": rec.get("chunk_index"),
            "text": rec.get("text"),
        }
        payloads.append(payload)

    return {
        "batch": {
            "ids": ids,
            "vectors": vectors,
            "payloads": payloads,
        }
    }


def main():
    # Carica env da .env (se esiste) + usa quelle già esportate
    load_dotenv()

    embeddings = init_embeddings()

    # Svuota/crea il file di output
    open(OUTPUT_FILE, "w", encoding="utf-8").close()

    buffer: List[Dict[str, Any]] = []

    for rec in load_chunks(CHUNKS_FILE):
        buffer.append(rec)

        if len(buffer) >= BATCH_SIZE:
            texts = [r["text"] for r in buffer]
            vectors = embeddings.embed_documents(texts)

            qdrant_batch = build_qdrant_batch(buffer, vectors)

            # Scrivi un batch per riga nel file
            with open(OUTPUT_FILE, "a", encoding="utf-8") as out_f:
                out_f.write(json.dumps(qdrant_batch, ensure_ascii=False) + "\n")

            buffer = []

    # Ultimo batch (se rimangono record)
    if buffer:
        texts = [r["text"] for r in buffer]
        vectors = embeddings.embed_documents(texts)
        qdrant_batch = build_qdrant_batch(buffer, vectors)

        with open(OUTPUT_FILE, "a", encoding="utf-8") as out_f:
            out_f.write(json.dumps(qdrant_batch, ensure_ascii=False) + "\n")

    print(f"Batch Qdrant salvati in {OUTPUT_FILE}")


if __name__ == "__main__":
    main()