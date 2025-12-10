import os
from typing import List, Tuple

from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import ScoredPoint
from langchain_openai import OpenAIEmbeddings, ChatOpenAI


# -------------------------------------------------
# INIT
# -------------------------------------------------
load_dotenv()

os.environ["LANGCHAIN_TRACING_V2"] = os.getenv("LANGCHAIN_TRACING_V2", "true")
os.environ["LANGCHAIN_API_KEY"] = os.getenv("LANGCHAIN_API_KEY", "")
os.environ["LANGCHAIN_ENDPOINT"] = os.getenv("LANGCHAIN_ENDPOINT", "https://api.smith.langchain.com")
os.environ["LANGCHAIN_PROJECT"] = "corretto_rag_demo"

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY") or None
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "corretto_prova")

# Client Qdrant
client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)

# DEVE essere lo stesso modello usato per creare gli embedding nel DB
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

# Modello chat per la risposta RAG
llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0,   # risposte più precise/“da manuale”
)


# -------------------------------------------------
# RETRIEVAL
# -------------------------------------------------
def retrieve(query: str, k: int = 10) -> List[ScoredPoint]:
    """Cerca i k chunk più rilevanti in Qdrant."""
    query_vector = embeddings.embed_query(query)

    result = client.query_points(
        collection_name=QDRANT_COLLECTION,
        query=query_vector,
        limit=k,
        with_payload=True,
    )

    return result.points


def build_context(points: List[ScoredPoint]) -> str:
    """Costruisce una stringa di contesto a partire dai punti trovati."""
    blocks = []
    for i, point in enumerate(points, start=1):
        payload = point.payload or {}
        url = payload.get("url") or ""
        title = payload.get("title") or ""
        text = payload.get("text") or ""

        block = (
            f"[DOC {i}]\n"
            f"URL: {url}\n"
            f"TITLE: {title}\n"
            f"TEXT:\n{text}"
        )
        blocks.append(block)

    return "\n\n".join(blocks)


# -------------------------------------------------
# RAG: RETRIEVE + GENERATE
# -------------------------------------------------
def answer_with_rag(query: str) -> Tuple[str, List[ScoredPoint]]:
    """Esegue retrieval da Qdrant e genera una risposta con gpt-4o-mini."""
    points = retrieve(query)
    context = build_context(points)

    system_prompt = (
        "Sei un assistente che risponde usando SOLO le informazioni presenti "
        "nella sezione CONTEXT.\n"
        "- Se la domanda chiede un ELENCO (tutti i servizi, tutte le opzioni, ecc.), "
        "cerca di includere TUTTI gli elementi presenti nel CONTEXT.\n"
        "- Se il contesto contiene solo una parte dell'elenco, specifica che l'elenco "
        "potrebbe non essere completo.\n"
        "- Non inventare fatti che non trovi nel contesto.\n"
        "- Rispondi in italiano, in modo chiaro e comprensibile."
    )

    user_prompt = (
        f"CONTEXT:\n{context}\n\n"
        f"DOMANDA: {query}\n\n"
        "Scrivi una risposta completa ma sintetica basandoti esclusivamente sul CONTEXT."
    )

    response = llm.invoke(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
    )

    return response.content, points


# -------------------------------------------------
# CLI SEMPLICE
# -------------------------------------------------
def main():
    print("RAG demo su Villa Immacolata + Qdrant + gpt-4o-mini")
    print("Scrivi una domanda (vuoto per uscire)\n")

    while True:
        query = input("Domanda: ").strip()
        if not query:
            break

        print("\n[⏳] Recupero contesto da Qdrant e chiedo a gpt-4o-mini...\n")
        answer, points = answer_with_rag(query)

        print("=== RISPOSTA ===")
        print(answer)

        print("\n=== FONTI UTILIZZATE ===")
        for i, p in enumerate(points, start=1):
            payload = p.payload or {}
            print(f"{i}. {payload.get('title')} ({payload.get('url')})")

        print("\n" + "-" * 80 + "\n")


if __name__ == "__main__":
    main()