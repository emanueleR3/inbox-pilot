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

    return " ".join(unique_blocks)


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

    if start_url in visited:
        return
    if any(pattern in start_url for pattern in URL_BLOCKLIST):
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
    # 1. Pulisci l'HTML
    raw_text = clean_html(response.text)
    
    # 2. Applica il filtro di unicità globale
    # Questo rimuove i blocchi > 100 char già visti in precedenza
    final_text = filter_redundant_content(raw_text, seen_content_hashes)
    
    page_title = soup.title.string.strip() if soup.title else "No Title"

    # Scriviamo solo se è rimasto qualcosa dopo la deduplicazione
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

        if any(x in url.lower() for x in [".pdf", ".jpg", ".png", "mailto:", "tel:", "javascript:"]):
            continue

        if urlparse(url).netloc != urlparse(start_url).netloc:
            continue
            
        if any(pattern in url for pattern in URL_BLOCKLIST):
            continue

        crawl(url, visited, seen_content_hashes)

# ---------------------------------------
# MAIN
# ---------------------------------------
if __name__ == "__main__":
    open(OUTPUT_FILE, "w").close()

    sito = "[website-url]"
    visited_pages = set()
    
    # Set globale per tracciare gli hash dei blocchi di testo già salvati
    seen_content_hashes = set() 
    
    crawl(sito, visited_pages, seen_content_hashes)

    print("\nScraping completato! Pagine totali:", len(visited_pages))
    print("Contenuto salvato in:", OUTPUT_FILE)