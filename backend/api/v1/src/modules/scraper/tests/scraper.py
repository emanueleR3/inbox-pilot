import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, urldefrag
import re
import hashlib  # Usato per creare impronte digitali dei testi

session = requests.Session()
session.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://www.google.com/",
})

OUTPUT_FILE = "output.txt"

# ------------------------------------------------------
#  CONFIGURAZIONE FILTRI URL (BLOCKLIST)
# ------------------------------------------------------
URL_BLOCKLIST = [
    # 1. I tuoi filtri personalizzati
    "/tag/", "/author/", "/category/", "/terms-conditions", 
    "/privacy-policy", "/legal-notice", "/blog", "/newsletter", "/cookie-policy",
    
    # 2. Pattern Tecnici WordPress
    "/feed/", "/rss/", "/comments/", "#comment", 
    "wp-json", "wp-admin", "wp-login", "?share=", "?replytocom=",
    
    # 3. Pattern E-Commerce (Shop, Prodotti, Carrello)
    "/shop/", "/negozio/", "/store/", "/prodotto/", "/product/", "/item/",
    "/cart/", "/carrello/", "/basket/", "/checkout/", "/cassa/", "/pagamento/", "/catalogo/", "/catalog/",
    "?add-to-cart=", "?orderby=", "?price-min=", "/wishlist", "/catalogo-completo/",

    # 4. Pattern Utenti (Registrazione, Login)
    "/register", "/login", "/account", "/my-account", "/mio-account", "/user", "/users", "/profile", "/profilo", "/dashboard", "/dashboard",
    "/il-mio-account", "/il-mio-profilo", "/registrazione-utente", "/registrazione"
]

GENERIC_EXCLUDED_SUBSTRINGS = [
    "privacy", "cookie", "cookies", "gdpr",
    "termini-di-utilizzo", "termini-di-uso",
    "terms-of-use", "terms-and-conditions", "termsconditions",
    "login", "sign-in", "signup"
]

# ------------------------------------------------------
#  PULIZIA GENERICA DEL TESTO (VALIDA PER QUALSIASI SITO)
# ------------------------------------------------------

# Keyword che identificano blocchi di testo rumore (cookie, nav, ecc.)
COOKIE_KEYWORDS = [
    "consenso cookies",
    "gestisci preferenze",
    "gestisci servizi",
    "cookie per",
    "informativa cookie",
    "vendor_count",
    "salva preferenze",
    "cookie",
    "cookies",
    "archiviazione tecnica",
    "scopi di marketing simili",
    "cookie banner",
    "usiamo i cookie",
    "questa pagina utilizza i cookie",
    "privacy e cookie",
    "cookie di terze parti",
    "i cookie per",
    "consenso cookies",
    "informativa cookie",
    "informazioni sui cookie",
    "cookie policy",
    "privacy policy",
    "vendor_count",
    "scopi di marketing simili",
    "salva preferenze",
    "gestisci preferenze"
]

NAV_KEYWORDS = [
    "vai al contenuto",
    "torna in alto",
    "menu principale",
    "menu di navigazione",
    "chiudi menu",
    "chiudi menù",
    "leggi tutto..."
]

# ------------------------------------------------------
#  PULIZIA TESTO E RIMOZIONE RUMORE
# ------------------------------------------------------
def is_noise_block(text: str) -> bool:
    """
    Ritorna True se il blocco è probabilmente rumore
    (cookie banner, nav, bottoni, micro-frasi).
    """
    t = text.lower().strip()
    length = len(t)

    # cookie / privacy / consenso
    # filtra cookie banner e elementi di navigazione
    if any(k in t for k in COOKIE_KEYWORDS + NAV_KEYWORDS):
        return True

    # blocchi molto corti: spesso bottoni o label
    if length < 40 and len(t.split()) < 6:
        return True

    # blocchi quasi privi di lettere/digit (icone, simboli)
    letters = sum(c.isalpha() for c in t)
    digits = sum(c.isdigit() for c in t)
    if letters + digits < 5:
        return True

    return False

# ------------------------------------------------------
#  NORMALIZZAZIONE TESTO
# ------------------------------------------------------
def normalize_text(text: str) -> str:
    """
    Rimuove caratteri strani, normalizza spazi e righe vuote.
    """
    # rimuove simboli non alfanumerici / punteggiatura principale (es. )
    text = re.sub(r"[^\wÀ-ÿ.,;:!?%€@/\-\(\)\n ]+", " ", text)

    # collassa spazi multipli in uno
    text = re.sub(r"[ \t]+", " ", text)

    # pulizia righe
    lines = [ln.strip() for ln in text.splitlines()]

    cleaned_lines = []
    empty_streak = 0
    for ln in lines:
        if ln == "":
            empty_streak += 1
            if empty_streak > 1:
                continue
        else:
            empty_streak = 0
        cleaned_lines.append(ln)

    return "\n".join(cleaned_lines).strip()

# ------------------------------------------------------
#  PULIZIA TESTO DA PAGINA
# ------------------------------------------------------
def clean_page_text(raw_text: str) -> str:
    """
    Prende il testo già estratto/filtro-deduplicato e:
    - rimuove i blocchi rumorosi
    - normalizza il formato
    """
    if not raw_text:
        return ""

    # spezza in blocchi/paragrafi usando il doppio newline
    blocks = [b.strip() for b in raw_text.split("\n\n") if b.strip()]

    # filtra i blocchi rumorosi
    kept_blocks = [b for b in blocks if not is_noise_block(b)]

    if not kept_blocks:
        return ""

    joined = "\n\n".join(kept_blocks)
    return normalize_text(joined)

# ------------------------------------------------------
#  LOGICA DI DEDUPLICAZIONE GLOBALE
# ------------------------------------------------------
def filter_redundant_content(text, seen_hashes):
    """
    Spezza il testo in blocchi (paragrafi).
    Se un blocco > 100 char è già stato visto in altre pagine, lo rimuove.
    """
    if not text:
        return ""

    # Dividiamo il testo in blocchi usando il doppio a capo come separatore naturale
    blocks = text.split('\n\n')
    unique_blocks = []

    for block in blocks:
        # Rimuove sequenze di almeno 100 segni di uguale
        block = re.sub(r'={100,}', '', block)
        
        block_clean = block.strip()
        
        # Se il blocco è vuoto, saltalo
        if not block_clean:
            continue

        # Calcoliamo se dobbiamo controllarlo (solo se > 100 caratteri)
        if len(block_clean) > 100:
            # Creiamo un hash del contenuto per efficienza di memoria
            # Usiamo md5 per creare un'impronta digitale univoca del blocco
            block_hash = hashlib.md5(block_clean.encode('utf-8')).hexdigest()
            
            if block_hash in seen_hashes:
                # Già visto! È un duplicato (es. footer lungo o disclaimer), lo scartiamo
                # Opzionale: print(f"   [Deduplica] Rimosso blocco duplicato di {len(block_clean)} chars")
                continue
            
            # Nuovo blocco lungo: aggiungiamolo alla memoria
            seen_hashes.add(block_hash)
        
        # I blocchi corti (<100) li teniamo sempre (titoli, brevi frasi)
        # I blocchi lunghi nuovi li teniamo
        unique_blocks.append(block)

    return "\n\n".join(unique_blocks)

# ------------------------------------------------------
#  FILTRI URL PER CRAWLING
# ------------------------------------------------------
def should_index_url(url: str) -> bool:
    """
    Ritorna False se l'URL non va né visitato né salvato.
    Usa sia la URL_BLOCKLIST che i pattern generici.
    """
    lower_url = url.lower()

    # 1) blocklist specifica che hai già definito
    if any(pattern in lower_url for pattern in URL_BLOCKLIST):
        return False

    # 2) pattern generici (privacy, cookie, termini, ecc.)
    if any(sub in lower_url for sub in GENERIC_EXCLUDED_SUBSTRINGS):
        return False

    # 3) risorse che NON sono pagine HTML interessanti
    if any(ext in lower_url for ext in [".pdf", ".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp"]):
        return False
    if lower_url.startswith("mailto:") or lower_url.startswith("tel:") or lower_url.startswith("javascript:"):
        return False

    return True

# ------------------------------------------------------
#  RILEVAMENTO BLOCCHI DI RUMORE
# ------------------------------------------------------
def is_noise_block(text: str) -> bool:
    t = text.lower()
    if any(k in t for k in COOKIE_KEYWORDS):
        return True
    if any(k in t for k in NAV_KEYWORDS):
        return True
    # blocchi quasi solo link / pulsanti
    if len(t) < 50 and len(t.split()) < 10:
        return True
    return False

# ------------------------------------------------------
#  RILEVAMENTO PAGINE PRODOTTO
# ------------------------------------------------------
def is_product_page(soup):
    body_classes = soup.body.get('class', []) if soup.body else []
    if any(cls in body_classes for cls in ['single-product', 'tax-product_cat', 'woocommerce-cart', 'woocommerce-checkout']):
        return True
    if soup.select_one("form.cart") or soup.select_one(".add_to_cart_button"):
        return True
    if soup.select_one(".price") and soup.select_one(".product_title"):
        return True
    if soup.find(attrs={"itemtype": re.compile(r"schema\.org/Product")}):
        return True
    return False

# ------------------------------------------------------
#  PULIZIA HTML
# ------------------------------------------------------
def clean_html(html):
    soup = BeautifulSoup(html, "html.parser")

    # 1. RIMOZIONE ELEMENTI INUTILI
    blacklist_selectors = [
        "script", "style", "nav", "footer", "header", "aside", "form", "noscript", "iframe",
        ".elementor-hidden-desktop", ".elementor-hidden-tablet", ".elementor-hidden-mobile",
        ".cookie-notice", "#cookie-law-info-bar", ".cookie-banner", 
        "[role='navigation']", "[role='banner']",
        ".widget_shopping_cart", ".widget_products", ".related.products", 
        ".upsells.products", ".cross-sells", ".mini-cart"
    ]

    for sel in blacklist_selectors:
        for tag in soup.select(sel):
            tag.decompose()

    # 2. GESTIONE BLOCCHI DI TESTO
    # Usiamo un marcatore speciale per separare i blocchi in modo netto
    MARKER = "###BLOCK###"
    block_tags = ['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'div', 'article', 'section', 'blockquote']
    
    for tag in soup.find_all(block_tags):
        tag.insert_before(MARKER)
        tag.insert_after(MARKER)

    # Gestione specifica per <br>: li trasformiamo in newline
    for br in soup.find_all('br'):
        br.replace_with('\n')

    # 3. ESTRAZIONE TESTO
    # Usiamo separator=" " perché i blocchi sono già delimitati dai MARKER
    text = soup.get_text(separator=" ", strip=True)

    # 4. PULIZIA RIGHE E BLOCCHI
    # Invece di sostituire subito il marker, splittiamo per il marker
    # così processiamo ogni blocco separatamente
    raw_blocks = text.split(MARKER)
    clean_blocks = []
    
    stop_phrases = [
        "torna ai servizi", "scopri di più", "leggi tutto...", "contattaci", 
        "tutti i nostri servizi rsa", "menu", "seguici su", "chiudi", "accetta",
        "aggiungi al carrello", "visualizza carrello"
    ]
    
    for raw_block in raw_blocks:
        lines = []
        for line in raw_block.split('\n'):
            clean_line = line.strip()
            
            if not clean_line:
                continue
                
            if len(clean_line) < 2: continue
            if clean_line.lower() in stop_phrases: continue
            
            clean_line = re.sub(r'\s+', ' ', clean_line)
            lines.append(clean_line)
            
        # Se il blocco ha contenuto valido, lo aggiungiamo
        if lines:
            clean_blocks.append(" ".join(lines))

    # Uniamo i blocchi con doppio a capo per garantire la separazione
    final_text = "\n\n".join(clean_blocks)
    return re.sub(r'\n{3,}', '\n\n', final_text)

# ---------------------------------------
# NORMALIZZAZIONE URL
# ---------------------------------------
def normalize_url(url):
    clean_url, _ = urldefrag(url)
    return clean_url.rstrip("/")

# ---------------------------------------
# CRAWLER
# ---------------------------------------
def crawl(start_url, visited, seen_content_hashes):
    """
    Ora accetta 'seen_content_hashes' per gestire la deduplicazione globale
    """
    start_url = normalize_url(start_url)

    start_url = normalize_url(start_url)

    if start_url in visited:
        return
    if not should_index_url(start_url):
        return

    visited.add(start_url)
    print(f"[+] Visiting: {start_url}")

    try:
        response = session.get(start_url, timeout=10)
        
        if response.url != start_url:
             final_url = normalize_url(response.url)
             # Se l'URL finale è diverso da quello di partenza (es. redirect reale)
             # controlliamo se lo abbiamo già visitato o se è in blocklist.
             # Se invece final_url == start_url (es. redirect da / a senza slash), va bene procedere.
             if final_url != start_url and (final_url in visited or any(p in final_url for p in URL_BLOCKLIST)):
                 return
                 
        response.raise_for_status()
    except Exception as e:
        print(f"   Errore nel caricamento: {e}")
        return

    content_type = response.headers.get('Content-Type', '').lower()
    if 'text/html' not in content_type or start_url.endswith(".pdf"):
        return

    soup = BeautifulSoup(response.text, "html.parser")
    if is_product_page(soup):
        print("   -> Skipping: Pagina Prodotto/Shop rilevata.")
        return

    # ---------------------------
    #  ESTRAZIONE E DEDUPLICAZIONE
    # ---------------------------
    # 1. Pulisci l'HTML (estrazione testo grezzo)
    raw_text = clean_html(response.text)

    # 2. Deduplica blocchi lunghi già visti su altre pagine
    deduped_text = filter_redundant_content(raw_text, seen_content_hashes)

    # 3. Pulizia generica del testo (cookie, nav, rumore, normalizzazione)
    final_text = clean_page_text(deduped_text)

    page_title = soup.title.string.strip() if soup.title else "No Title"

    # Scriviamo solo se è rimasto qualcosa dopo tutto
    if final_text.strip():
        with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
            f.write(f"--- START PAGE ---\n")
            f.write(f"URL: {start_url}\n")
            f.write(f"TITLE: {page_title}\n")
            f.write(f"CONTENT:\n{final_text}\n")
            f.write(f"--- END PAGE ---\n\n")

    # ---- CONTINUA CRAWLING ----
    for link in soup.find_all("a", href=True):
        url = urljoin(start_url, link["href"])
        url = normalize_url(url)

        # stesso dominio
        if urlparse(url).netloc != urlparse(start_url).netloc:
            continue

        # passa dal filtro unico
        if not should_index_url(url):
            continue

        crawl(url, visited, seen_content_hashes)

# ---------------------------------------
# MAIN
# ---------------------------------------
if __name__ == "__main__":
    open(OUTPUT_FILE, "w").close()

    sito = "[inserire_il_sito_da_crawling]"
    visited_pages = set()
    
    # Set globale per tracciare gli hash dei blocchi di testo già salvati
    seen_content_hashes = set() 
    
    crawl(sito, visited_pages, seen_content_hashes)

    print("\nScraping completato! Pagine totali:", len(visited_pages))
    print("Contenuto salvato in:", OUTPUT_FILE)