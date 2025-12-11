import os
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from langchain_openai import OpenAIEmbeddings

load_dotenv()

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY") or None
COLLECTION = os.getenv("QDRANT_COLLECTION", "corretto_prova")

client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

query = "Sono interessato alla vostra struttura. Quali servizi offrite? Siete una struttura accreditata con l'ASL?"
query_vector = embeddings.embed_query(query)

# NUOVA API: query_points (non search)
result = client.query_points(
    collection_name=COLLECTION,
    query=query_vector,      # vettore denso
    limit=5,
    with_payload=True,
)

for i, point in enumerate(result.points, start=1):
    print(f"\n=== RISULTATO {i} (score={point.score:.4f}) ===")
    payload = point.payload or {}
    print("URL:", payload.get("url"))
    print("TITLE:", payload.get("title"))
    text = payload.get("text") or ""
    print("TESTO:", text[:400], "...")