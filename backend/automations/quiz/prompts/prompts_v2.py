"""
Prompts for the new quiz system (v2).
Centralized prompt management for better maintainability.
"""


# ============================================================================
# Validate Business Description Prompts
# ============================================================================

VALIDATE_BUSINESS_SYSTEM_PROMPT = """Valuta se la descrizione aziendale è sufficiente per creare un piano.
VALIDA se: indica settore/attività (es: "ristorante", "studio legale", "e-commerce")
NON VALIDA se: troppo vaga o incomprensibile"""

VALIDATE_BUSINESS_USER_PROMPT_TEMPLATE = """"{user_answer}" - È valida?"""


# ============================================================================
# Generate Plan Node Prompts
# ============================================================================

GENERATE_PLAN_SYSTEM_PROMPT = """Crea piano raccolta info per azienda. Pensa come CLIENTE che scrive email all'azienda.

Regole:
- Crea 8-12 categorie SOLO ad alta probabilità di essere richieste dai clienti in quel settore.
- Le categorie devono essere specifiche per l'ambito (no template generici).
- NON includere categorie non pertinenti al settore.
- "Resi/Garanzie" SOLO se l'azienda vende prodotti o servizi con policy di reso/garanzia rilevante.

Esempi (adatta al settore): servizi offerti, prezzi/rette, orari, contatti, modalità di accesso/prenotazione, processo (ammissione/acquisto), supporto/assistenza.

Stile delle domande:
- La domanda NON deve essere telegrafica.
- Nel campo answer scrivi SEMPRE:
    1) la domanda principale per la prossima categoria
    2) una mini-scaletta (3-5 punti) su cosa e come rispondere per quella categoria (esempi di dettagli utili).

Domande al TITOLARE su cosa OFFRE (mai "cosa cercate")."""

GENERATE_PLAN_USER_PROMPT_TEMPLATE = """Settore: {business_description}

Crea piano con 8-12 categorie specifiche per questo business e prima domanda."""


# ============================================================================
# Process Answer Node Prompts
# ============================================================================

PROCESS_ANSWER_SYSTEM_PROMPT = """Raccogli info aziendali dal TITOLARE sui SERVIZI CHE OFFRE.

ESTRAI INFO: Qualsiasi risposta sostanziale su una categoria = COMPLETATA.
Quando salvi l'info:
- NON fare riassunti: mantieni dettagli, specializzazioni, ambiti (es. "diritto civile e penale"), target (privati/aziende), condizioni.
Esempi di risposte VALIDE da marcare come completate:
- "Non ho prezzi fissi, faccio preventivi" → Prezzi ✅ (info: "Preventivi personalizzati, nessun listino fisso")
- "Dipende dal caso" → ✅ (info: "Variabile in base al caso specifico")
- "Lo gestiamo caso per caso" → ✅ (info: quella frase)

AZIONI SPECIALI:
- SKIP esplicito: "salta", "non configurare", "gestisco manualmente" → completed=true, info=null
- AGGIUNGI: "aggiungi punto X" → items_to_add
- NOTA: frasi tipo "aggiungi/integra per quanto riguarda PREZZI/ORARI/CONTATTI" NON creano un nuovo punto:
    sono un aggiornamento della categoria esistente (metti l'info in collected_info e marca completed=true).
- RIMUOVI: "rimuovi punto X" → items_to_remove

REGOLE DI SICUREZZA (IMPORTANTISSIME):
- NON cambiare lo stato (completed) di categorie che NON hai aggiornato in questo turno.
- Marca completed=true SOLO se: (a) hai estratto info per quella categoria in collected_info, oppure (b) l'utente ha detto esplicitamente di SKIP.
- NON segnare all_completed=true a meno che TUTTE le categorie siano davvero complete.
- items_to_remove SOLO se l'utente lo chiede esplicitamente. Se l'utente dice "rimuovi questo punto" senza specificare il nome, rimuovi SOLO la categoria della domanda corrente.

Se utente vuole aggiungere senza nome → needs_name_for_new_item=true E in answer devi chiedere il nome (es. "Come vuoi chiamare il nuovo punto?").

STILE DELLA PROSSIMA DOMANDA (campo answer):
- NON essere troppo breve.
- Fai 1 domanda alla volta, sulla prossima categoria da completare.
- Includi SEMPRE una mini-scaletta (3-5 punti) che guida l'utente su cosa inserire per quella categoria.
    Esempio formato:
    "Domanda: ...\n\nPer aiutarmi, includi se puoi:\n- ...\n- ...\n- ..."
"""

PROCESS_ANSWER_USER_PROMPT_TEMPLATE = """Settore: {business_field}

Categorie:
{bullet_status}

Chat:
{history}

IMPORTANTE: Se l'utente ha risposto su una categoria (anche con "dipende", "variabile", "personalizzato"), marcala COMPLETATA e salva l'info."""


# ============================================================================
# Generate Markdown Node Prompts
# ============================================================================

GENERATE_MARKDOWN_SYSTEM_PROMPT = """Genera documento Markdown con tutte le info aziendali raccolte. Professionale, organizzato per sezioni. Solo contenuto MD."""

GENERATE_MARKDOWN_USER_PROMPT_TEMPLATE = """Settore: {business_field}

Info:
{collected_info}

Genera MD completo."""


# ============================================================================
# Review / Edit Context (post-quiz)
# ============================================================================

REVIEW_CONTEXT_START_MESSAGE = (
    "Questa è la prima versione del contesto aziendale che ho salvato.\n"
    "Puoi:\n"
    "- modificare direttamente il testo (incollando la versione corretta), oppure\n"
    "- dirmi cosa vuoi eliminare, modificare o aggiungere.\n\n"
    "Quando ti sembra tutto corretto, scrivi: \"OK, salva\"."
)

EDIT_CONTEXT_SYSTEM_PROMPT = """Aggiorna il Markdown del contesto aziendale.

Regole:
- Applica fedelmente le richieste dell'utente (aggiunte/rimozioni/correzioni).
- Se l'utente incolla un nuovo Markdown completo, usa quello.
- Non inventare dati.
- Mantieni stile Markdown pulito e sezioni coerenti.

Conferma:
- is_confirmed=true SOLO se l'utente dice chiaramente che va bene e che vuoi salvare (es. "OK, salva", "confermo").
"""

EDIT_CONTEXT_USER_PROMPT_TEMPLATE = """Markdown attuale:
{current_markdown}

Richiesta utente:
{user_request}

Restituisci markdown aggiornato e un messaggio breve."""


# ============================================================================
# Initial Question
# ============================================================================

INITIAL_QUESTION = (
    "Di cosa si occupa la tua azienda? In che campo opera?\n"
    "Dammi una breve descrizione per capire cosa devo chiederti successivamente per aiutarti a rispondere ai tuoi clienti."
)


# ============================================================================
# With Context Node (TODO)
# ============================================================================

WITH_CONTEXT_TODO_MESSAGE = "La funzionalità con contesto RAG sarà disponibile a breve."


__all__ = [
    "VALIDATE_BUSINESS_SYSTEM_PROMPT",
    "VALIDATE_BUSINESS_USER_PROMPT_TEMPLATE",
    "GENERATE_PLAN_SYSTEM_PROMPT",
    "GENERATE_PLAN_USER_PROMPT_TEMPLATE",
    "PROCESS_ANSWER_SYSTEM_PROMPT",
    "PROCESS_ANSWER_USER_PROMPT_TEMPLATE",
    "GENERATE_MARKDOWN_SYSTEM_PROMPT",
    "GENERATE_MARKDOWN_USER_PROMPT_TEMPLATE",
    "INITIAL_QUESTION",
    "WITH_CONTEXT_TODO_MESSAGE",
    "REVIEW_CONTEXT_START_MESSAGE",
    "EDIT_CONTEXT_SYSTEM_PROMPT",
    "EDIT_CONTEXT_USER_PROMPT_TEMPLATE",
]
