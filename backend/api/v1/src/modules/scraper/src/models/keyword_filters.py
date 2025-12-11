"""Keyword filters and blocklists for web scraping."""

# ------------------------------------------------------
#  URL BLOCKLIST CONFIGURATION
# ------------------------------------------------------
URL_BLOCKLIST = [
    # Custom filters
    "/tag/", "/author/", "/category/", "/terms-conditions", 
    "/privacy-policy", "/legal-notice", "/blog", "/newsletter", "/cookie-policy",
    
    # WordPress technical patterns
    "/feed/", "/rss/", "/comments/", "#comment", 
    "wp-json", "wp-admin", "wp-login", "?share=", "?replytocom=",
    
    # E-Commerce patterns
    "/shop/", "/negozio/", "/store/", "/prodotto/", "/product/", "/item/",
    "/cart/", "/carrello/", "/basket/", "/checkout/", "/cassa/", "/pagamento/", "/catalogo/", "/catalog/",
    "?add-to-cart=", "?orderby=", "?price-min=", "/wishlist", "/catalogo-completo/",

    # User patterns
    "/register", "/login", "/account", "/my-account", "/mio-account", "/user", "/users", 
    "/profile", "/profilo", "/dashboard",
    "/il-mio-account", "/il-mio-profilo", "/registrazione-utente", "/registrazione"
]

GENERIC_EXCLUDED_SUBSTRINGS = [
    "privacy", "cookie", "cookies", "gdpr",
    "termini-di-utilizzo", "termini-di-uso",
    "terms-of-use", "terms-and-conditions", "termsconditions",
    "login", "sign-in", "signup"
]

# ------------------------------------------------------
#  NOISE KEYWORDS FOR TEXT FILTERING
# ------------------------------------------------------
COOKIE_KEYWORDS = [
    "consenso cookies", "gestisci preferenze", "gestisci servizi",
    "cookie per", "informativa cookie", "vendor_count", "salva preferenze",
    "cookie", "cookies", "archiviazione tecnica", "scopi di marketing simili",
    "cookie banner", "usiamo i cookie", "questa pagina utilizza i cookie",
    "privacy e cookie", "cookie di terze parti", "i cookie per",
    "informazioni sui cookie", "cookie policy", "privacy policy"
]

NAV_KEYWORDS = [
    "vai al contenuto", "torna in alto", "menu principale",
    "menu di navigazione", "chiudi menu", "chiudi menù", "leggi tutto...",
    "scorri in alto"
]

# Stop phrases for HTML cleaning
STOP_PHRASES = [
    "torna ai servizi", "scopri di più", "leggi tutto...", "contattaci", 
    "tutti i nostri servizi rsa", "menu", "seguici su", "chiudi", "accetta",
    "aggiungi al carrello", "visualizza carrello"
]

# HTML blacklist selectors for scraping
HTML_BLACKLIST_SELECTORS = [
    "script", "style", "nav", "footer", "header", "aside", "form", "noscript", "iframe",
    ".elementor-hidden-desktop", ".elementor-hidden-tablet", ".elementor-hidden-mobile",
    ".cookie-notice", "#cookie-law-info-bar", ".cookie-banner", 
    "[role='navigation']", "[role='banner']",
    ".widget_shopping_cart", ".widget_products", ".related.products", 
    ".upsells.products", ".cross-sells", ".mini-cart"
]

# Block tags for text extraction
BLOCK_TAGS = ['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'div', 'article', 'section', 'blockquote']