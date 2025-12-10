import json
from dataclasses import dataclass
from typing import List


INPUT_FILE = "output.txt"
OUTPUT_FILE = "chunks.jsonl"

# Parametri di chunking (li puoi aggiustare dopo)
MAX_CHARS = 3000       # dimensione massima di un chunk
OVERLAP_CHARS = 200    # overlap tra chunk consecutivi
THRESHOLD_NO_CHUNKING = 3500

@dataclass
class Page:
    url: str
    title: str
    content: str


def parse_output_file(path: str) -> List[Page]:
    """
    Legge l'output del crawler nel formato:
    --- START PAGE ---
    URL: ...
    TITLE: ...
    CONTENT:
    ...
    --- END PAGE ---

    e restituisce una lista di Page.
    """
    pages: List[Page] = []

    with open(path, "r", encoding="utf-8") as f:
        raw = f.read()

    # split per blocchi pagina
    raw_pages = raw.split("--- START PAGE ---")
    for raw_page in raw_pages:
        raw_page = raw_page.strip()
        if not raw_page:
            continue

        # stop all'end
        # dovrebbe contenere ... --- END PAGE ---
        if "--- END PAGE ---" in raw_page:
            raw_page = raw_page.split("--- END PAGE ---")[0].strip()

        lines = raw_page.splitlines()
        url = ""
        title = ""
        content_lines = []
        in_content = False

        for line in lines:
            if line.startswith("URL:"):
                url = line[len("URL:"):].strip()
            elif line.startswith("TITLE:"):
                title = line[len("TITLE:"):].strip()
            elif line.startswith("CONTENT:"):
                in_content = True
            elif in_content:
                content_lines.append(line)

        content = "\n".join(content_lines).strip()
        if url and content:
            pages.append(Page(url=url, title=title, content=content))

    return pages

def chunk_text(text: str, max_chars: int = MAX_CHARS, overlap: int = OVERLAP_CHARS) -> List[str]:
    """
    Chunking per paragrafi, con overlap di un paragrafo tra chunk consecutivi.
    Funziona per qualsiasi testo con \n\n tra i paragrafi.
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

        # caso: paragrafo singolo enorme -> spezzalo a caratteri
        if para_len > max_chars:
            # chiudi eventuale chunk in corso
            flush_chunk()

            start = 0
            while start < para_len:
                end = min(start + max_chars, para_len)
                big_chunk = para[start:end].strip()
                if big_chunk:
                    chunks.append(big_chunk)
                start = end
            continue

        # se aggiungendo questo paragrafo superiamo il limite, chiudi chunk
        if current_len + para_len + (2 if current_paras else 0) > max_chars:
            flush_chunk()

            # overlap: riporta l'ultimo paragrafo del chunk precedente
            if chunks and overlap > 0:
                last_chunk = chunks[-1]
                last_chunk_paras = [p.strip() for p in last_chunk.split("\n\n") if p.strip()]
                if last_chunk_paras:
                    overlap_para = last_chunk_paras[-1]
                    current_paras = [overlap_para]
                    current_len = len(overlap_para)

        # aggiungi paragrafo al chunk corrente
        if not current_paras:
            current_paras = [para]
            current_len = para_len
        else:
            current_paras.append(para)
            current_len += para_len + 2  # +2 per il "\n\n"

    # flush finale
    flush_chunk()

    # opzionale: se l'ultimo chunk è minuscolo, unirlo al precedente
    MIN_CHARS = 300
    if len(chunks) >= 2 and len(chunks[-1]) < MIN_CHARS:
        last = chunks.pop()
        chunks[-1] = (chunks[-1] + "\n\n" + last).strip()

    return chunks

def main():
    pages = parse_output_file(INPUT_FILE)
    print(f"Trovate {len(pages)} pagine nel file {INPUT_FILE}")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as out_f:
        for page_index, page in enumerate(pages):
            # se la pagina è corta, un solo chunk
            if len(page.content) < THRESHOLD_NO_CHUNKING:
                page_chunks = [page.content.strip()]
            else:
                page_chunks = chunk_text(page.content)

            for chunk_index, chunk in enumerate(page_chunks):
                record = {
                    "id": f"{page_index}_{chunk_index}",
                    "url": page.url,
                    "title": page.title,
                    "page_index": page_index,
                    "chunk_index": chunk_index,
                    "text": chunk,
                }
                out_f.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(f"Chunk salvati in {OUTPUT_FILE}")


if __name__ == "__main__":
    main()