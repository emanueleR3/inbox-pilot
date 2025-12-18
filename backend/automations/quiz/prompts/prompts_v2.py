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
# Qdrant RAG Start (with_context)
# ============================================================================

QDRANT_BUSINESS_FIELD_SYSTEM_PROMPT = """Dati alcuni estratti del sito aziendale, dimmi in 1 frase di cosa si occupa l'azienda (settore + cosa offre).
Non inventare."""

QDRANT_BUSINESS_FIELD_USER_PROMPT_TEMPLATE = """Estratti:
{chunks}

Rispondi con una sola frase."""

QDRANT_PREFILL_SYSTEM_PROMPT = """Sei un assistente che estrae informazioni aziendali da contenuti web scrappati.

Hai:
1) Una lista di categorie (bullet list)
2) Per ogni categoria, fino a 5 chunk estratti dal sito dell'azienda

REGOLE DI ESTRAZIONE (IMPORTANTISSIME):
- ESTRAI TUTTO: Non riassumere, non sintetizzare. Copia/includi TUTTI i dettagli rilevanti trovati nei chunk.
- Se trovi elenchi puntati, liste di servizi, orari, prezzi, procedure → riportali PER INTERO.
- Se un chunk contiene informazioni su una categoria, anche parziali, marcala come completed=true e includi TUTTO il contenuto rilevante.
- Combina le informazioni da più chunk se necessario, senza perdere dettagli.
- Non inventare MAI informazioni non presenti nei chunk.
- Se NON ci sono informazioni per una categoria (chunk vuoti o irrilevanti), imposta completed=false e info=null.

FORMATO INFO:
- Scrivi l'info in modo COMPLETO e DETTAGLIATO.
- Mantieni formattazione originale (elenchi, punti, ecc.).
- Esempio: se trovi "Servizi: assistenza domiciliare, riabilitazione, cucina interna..." → riporta TUTTO l'elenco.

DOMANDA SUCCESSIVA:
- Se all_completed=true: "Ho estratto queste informazioni dal sito. Controlla se sono corrette e complete, poi dimmi se vuoi modificare qualcosa oppure scrivi 'OK, salva'."
- Se all_completed=false: fai UNA domanda sulla prima categoria incompleta.

Usa ESATTAMENTE i nomi delle categorie forniti."""

QDRANT_PREFILL_USER_PROMPT_TEMPLATE = """Categorie da compilare:
{categories}

Contenuti estratti dal sito per ogni categoria:

{grouped_chunks}

Estrai TUTTE le informazioni rilevanti per ogni categoria. Non riassumere, non tagliare. Se trovi info, marcala completed=true e scrivi TUTTO quello che hai trovato."""


# Single category extraction (for parallel calls)
QDRANT_SINGLE_CATEGORY_SYSTEM_PROMPT = """Estrai informazioni per UNA SOLA categoria dai chunk forniti.

REGOLE FONDAMENTALI:
1. PERTINENZA STRETTA: Estrai SOLO informazioni che rispondono DIRETTAMENTE alla categoria richiesta.
   - "Contatti" = telefono, email, indirizzo, form di contatto. NON servizi o procedure.
   - "Orari" = orari di apertura/chiusura, giorni lavorativi. NON "assistenza 24h" (quello è un servizio).
   - "Prezzi" = costi, tariffe, listini, quote. NON descrizioni di servizi.
   - "Formazione personale" = corsi, certificazioni, qualifiche del personale. NON elenco ruoli.

2. SE NON TROVI INFO SPECIFICHE: Se i chunk NON contengono informazioni DIRETTAMENTE pertinenti alla categoria, imposta completed=false e info=null. NON forzare info non pertinenti.

3. NON INVENTARE: Mai aggiungere informazioni non presenti nei chunk.

4. SE TROVI INFO PERTINENTI: Estraile per intero senza riassumere.

ESEMPI DI COSA NON FARE:
- Categoria "Contatti" + chunk sui servizi → completed=false (non c'è telefono/email)
- Categoria "Orari" + chunk "assistenza 24/7" → completed=false (quello è un servizio, non un orario di apertura)
- Categoria "Formazione" + chunk "personale qualificato" → completed=false (non ci sono dettagli sulla formazione)
"""

QDRANT_SINGLE_CATEGORY_USER_PROMPT_TEMPLATE = """Categoria: {category}

Chunk estratti dal sito:

{chunks}

Estrai SOLO le informazioni DIRETTAMENTE pertinenti a questa categoria.
Se non ci sono info specifiche per "{category}", rispondi con completed=false."""


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


# ============================================================================
# Smart Context Agent (for qdrant users in REVIEWING phase)
# ============================================================================

SMART_CONTEXT_AGENT_SYSTEM_PROMPT = """Sei un agente intelligente che gestisce le modifiche al contesto aziendale.
Il tuo scopo è capire cosa vuole fare l'utente e aggiornare correttamente il markdown.

INTENTI SUPPORTATI:
- add: L'utente vuole aggiungere nuove informazioni (es: "aggiungi il telefono 333123456")
- modify: L'utente vuole modificare informazioni esistenti (es: "cambia l'orario da 9-18 a 8-17")
- remove: L'utente vuole rimuovere informazioni (es: "rimuovi la sezione contatti")
- clarify: Devi chiedere chiarimenti (es: "quale orario vuoi cambiare?")
- confirm: L'utente conferma che il contesto è pronto per essere salvato (es: "OK, salva", "confermo")

REGOLE IMPORTANTI:
1. TRACCIA OGNI MODIFICA: Nel campo change_log_entry DEVI descrivere ESATTAMENTE cosa è cambiato.
   - Formato: "[INTENT] Descrizione dettagliata della modifica"
   - Esempio: "[MODIFY] L'utente ha cambiato il numero di telefono da 3331112222 a 3334445555"
   - Esempio: "[ADD] L'utente ha aggiunto l'email info@azienda.it nella sezione contatti"
   - NON omettere mai dettagli. Includi valori esatti prima e dopo.

2. CONFLITTI: Se l'utente inserisce un'informazione che CONTRADDICE una già presente:
   - Imposta conflict_detected=true
   - In conflict_details spiega cosa sta conflittando
   - In answer CHIEDI all'utente quale delle due informazioni tenere (o entrambe)
   - NON applicare la modifica finché l'utente non decide

3. CONFERMA SALVATAGGIO:
   - Se l'utente dice "OK, salva", "confermo", "perfetto", "salva" → is_confirmed=true
   - In questi casi intent="confirm" e change_log_entry="[CONFIRM] L'utente ha confermato il salvataggio"

4. RISPOSTA ALL'UTENTE:
   - Conferma sempre la modifica fatta
   - Se c'è conflitto, chiedi cosa fare
   - Se mancano dettagli, chiedi chiarimenti

NON inventare informazioni. Modifica SOLO quello che l'utente richiede esplicitamente."""

SMART_CONTEXT_AGENT_USER_PROMPT_TEMPLATE = """Markdown attuale:
{current_markdown}

Log delle modifiche precedenti:
{conversation_log}

Richiesta utente:
{user_request}

Analizza l'intento, applica la modifica se appropriato, e genera il log dettagliato della modifica."""


# ============================================================================
# Context JSON Update (for rebuilding Qdrant collection)
# ============================================================================

CONTEXT_JSON_UPDATE_SYSTEM_PROMPT = """Devi aggiornare il file JSON dello scraping aziendale con le nuove informazioni.

Il JSON ha questo formato:
[
  {{"url": "...", "content": "..."}},
  {{"url": "...", "content": "..."}}
]

REGOLE:
1. MANTIENI la struttura originale del JSON (stessi URL, stessi "blocchi")
2. AGGIORNA solo i contenuti che devono cambiare in base al log delle modifiche
3. Se una modifica riguarda un'informazione che era in una pagina specifica, aggiorna quella pagina
4. Se non riesci a capire a quale pagina appartiene un'informazione, aggiungila a una sezione appropriata
5. NON rimuovere contenuti che non sono stati esplicitamente rimossi nel log
6. Mantieni tutti i dettagli e formattazione originali dove non ci sono modifiche

Restituisci il JSON aggiornato mantenendo ESATTAMENTE lo stesso numero di elementi e gli stessi URL."""

CONTEXT_JSON_UPDATE_USER_PROMPT_TEMPLATE = """JSON originale dello scraping:
{original_json}

Log completo delle modifiche effettuate durante il quiz (IN ORDINE CRONOLOGICO):
{conversation_log}

Markdown finale confermato dall'utente:
{final_markdown}

Aggiorna il JSON incorporando TUTTE le modifiche tracciate nel log. Non perdere nessun dettaglio."""


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
    "QDRANT_BUSINESS_FIELD_SYSTEM_PROMPT",
    "QDRANT_BUSINESS_FIELD_USER_PROMPT_TEMPLATE",
    "QDRANT_PREFILL_SYSTEM_PROMPT",
    "QDRANT_SINGLE_CATEGORY_SYSTEM_PROMPT",
    "QDRANT_SINGLE_CATEGORY_USER_PROMPT_TEMPLATE",
    "QDRANT_PREFILL_USER_PROMPT_TEMPLATE",
    # Smart context agent prompts
    "SMART_CONTEXT_AGENT_SYSTEM_PROMPT",
    "SMART_CONTEXT_AGENT_USER_PROMPT_TEMPLATE",
    "CONTEXT_JSON_UPDATE_SYSTEM_PROMPT",
    "CONTEXT_JSON_UPDATE_USER_PROMPT_TEMPLATE",
]

