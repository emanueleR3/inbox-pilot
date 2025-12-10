import os
import json
from typing import Dict, Any

from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, Batch


BATCHES_FILE = "qdrant_batches.jsonl"


def read_first_batch(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            return json.loads(line)
    raise RuntimeError("Nessun batch trovato nel file.")


def main():
    load_dotenv()

    qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
    qdrant_api_key = os.getenv("QDRANT_API_KEY") or None
    collection_name = os.getenv("QDRANT_COLLECTION", "corretto_collection")

    client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key)

    # 1) Leggi il primo batch per capire la dimensione dei vettori
    first = read_first_batch(BATCHES_FILE)
    first_vectors = first["batch"]["vectors"]
    if not first_vectors:
        raise RuntimeError("Il primo batch non contiene vettori.")
    vector_size = len(first_vectors[0])
    print(f"Vector size: {vector_size}")

    # 2) Crea / ricrea la collection
    print(f"Creo/Ricreo la collection '{collection_name}'...")
    client.recreate_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(
            size=vector_size,
            distance=Distance.COSINE,
        ),
    )

    # 3) Scorri tutti i batch e fai upsert
    total_points = 0
    next_id = 1  # ID numerico incrementale valido per Qdrant

    with open(BATCHES_FILE, "r", encoding="utf-8") as f:
        for line_idx, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue

            data = json.loads(line)
            batch = data["batch"]

            vectors = batch["vectors"]
            payloads = batch["payloads"]
            batch_size = len(vectors)

            # GENERA NUOVI ID INTERI VALIDI (IGNORANDO quelli nel file)
            ids = list(range(next_id, next_id + batch_size))
            next_id += batch_size

            points = Batch(
                ids=ids,
                vectors=vectors,
                payloads=payloads,
            )

            client.upsert(
                collection_name=collection_name,
                points=points,
            )

            total_points += batch_size
            print(f"[Batch {line_idx}] upsert di {batch_size} punti (totale: {total_points})")

    print(f"Caricamento completato. Punti totali in '{collection_name}': {total_points}")


if __name__ == "__main__":
    main()