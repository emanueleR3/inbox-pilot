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
#  CONFIGURAZIONE FILTRI TESTO (KEYWORDS)
# ------------------------------------------------------
COOKIE_KEYWORDS = [
    "consenso cookies",
    "gestisci preferenze",
    "gestisci servizi",
    "cookie per",
    "informativa cookie",
    "vendor_count",
    "salva preferenze"
]

NAV_KEYWORDS = [
    "vai al contenuto",
    "torna in alto",
    "scorri in alto"
]

# ------------------------------------------------------
#  PULIZIA GENERICA DEL TESTO (VALIDA PER QUALSIASI SITO)
# ------------------------------------------------------
# Keyword che identificano blocchi di testo rumore (cookie, nav, ecc.)
COOKIE_KEYWORDS = [
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