import os
import json
from typing import Dict, Any, Iterable, List

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

load_dotenv()


class CleanedChunkResponse(BaseModel):
    """Risposta strutturata per il testo pulito."""
    cleaned_text: str = Field(description="Il testo pulito, senza rumore e con leggibilità migliorata")


# LangSmith
os.environ["LANGCHAIN_TRACING_V2"] = os.getenv("LANGCHAIN_TRACING_V2", "true")
os.environ["LANGCHAIN_API_KEY"] = os.getenv("LANGCHAIN_API_KEY", "")
os.environ["LANGCHAIN_ENDPOINT"] = os.getenv("LANGCHAIN_ENDPOINT", "https://api.smith.langchain.com")
os.environ["LANGCHAIN_PROJECT"] = "corretto_rag_demo"


INPUT_FILE = "chunks.jsonl"
OUTPUT_FILE = "chunks_clean.jsonl"

# per test puoi limitarlo, in produzione lascialo a None
MAX_CHUNKS = None

# batch LLM: quanti chunk processare per volta
BATCH_SIZE = 16


SYSTEM_PROMPT = (
    "Sei un assistente che pulisce testo estratto da pagine web per usarlo in un motore di ricerca semantico (RAG).\n"
    "DEVI:\n"
    "- mantenere TUTTE le informazioni importanti e i dettagli utili (servizi, numeri, condizioni, ecc.),\n"
    "- migliorare solo la leggibilità: spazi, a capo, liste, frasi spezzate,\n"
    "- rimuovere solo frasi chiaramente di interfaccia (es. 'torna su', 'gestisci cookie', 'accetta', 'chiudi', "
    "voci di menu isolate) e testo di banner cookie / GDPR se presenti.\n"
    "- rimuovere frasi ripetute più volte identiche e rumore evidente.\n\n"
    "NON DEVI:\n"
    "- aggiungere nuove informazioni,\n"
    "- riassumere o accorciare troppo il contenuto,\n"
    "- cambiare il significato delle frasi."
)


def load_chunks(path: str) -> Iterable[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)


def init_llm() -> ChatOpenAI:
    """
    Usa gpt-4o-mini via LangChain con output strutturato.
    """
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY non impostata nell'ambiente.")

    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0,
    )
    return llm.with_structured_output(CleanedChunkResponse)


def build_user_prompt(raw_text: str) -> str:
    return (
        "TESTO ORIGINALE:\n"
        "-----------------\n"
        f"{raw_text}\n\n"
        "Pulisci il testo seguendo le istruzioni."
    )


def process_batch(llm, batch: List[Dict[str, Any]], out_f) -> None:
    """
    batch: lista di dict {"rec": rec, "raw_text": text}
    out_f: file aperto in append
    """
    if not batch:
        return

    # prepara i messaggi per ogni chunk
    messages_list = []
    for item in batch:
        raw_text = item["raw_text"]
        messages_list.append(
            [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": build_user_prompt(raw_text)},
            ]
        )

    # chiamata batch al modello: una sola roundtrip per N chunk
    responses: List[CleanedChunkResponse] = llm.batch(messages_list)

    # scrivi i risultati, allineati all'ordine del batch
    for item, resp in zip(batch, responses):
        rec = item["rec"]
        rec["text"] = resp.cleaned_text.strip()
        out_f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def main():
    llm = init_llm()

    # svuota / crea il file di output una volta sola
    open(OUTPUT_FILE, "w", encoding="utf-8").close()

    count = 0
    batch: List[Dict[str, Any]] = []

    with open(OUTPUT_FILE, "a", encoding="utf-8") as out_f:
        for rec in load_chunks(INPUT_FILE):
            raw_text = rec.get("text", "").strip()
            if not raw_text:
                continue

            if MAX_CHUNKS is not None and count >= MAX_CHUNKS:
                break

            batch.append({"rec": rec, "raw_text": raw_text})

            # se il batch è pieno, processalo
            if len(batch) >= BATCH_SIZE:
                print(f"[{count}] Pulizia batch da {len(batch)} chunk (ultimo id={rec.get('id')})...")
                process_batch(llm, batch, out_f)
                count += len(batch)
                batch = []

        # batch residuo
        if batch:
            print(f"[{count}] Pulizia batch finale da {len(batch)} chunk...")
            process_batch(llm, batch, out_f)
            count += len(batch)

    print(f"Pulizia completata. Chunk scritti in {OUTPUT_FILE}: {count}")


if __name__ == "__main__":
    main()