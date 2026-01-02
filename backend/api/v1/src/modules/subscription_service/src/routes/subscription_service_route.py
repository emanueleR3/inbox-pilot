from fastapi import APIRouter, Body, Depends, Query, HTTPException, status
from typing import Optional
from urllib.parse import urlencode
from src.core.dependecy import get_current_user
from src.modules.subscription_service.src.controllers.subscription_service_controller import SubscriptionServiceController
from src.modules.subscription_service.src.utils.utils import forward_post, forward_get

router = APIRouter(
    #dependencies=[Depends(get_current_user)],
    tags=["Subscription Service"],
)
controller = SubscriptionServiceController()


@router.post(
    "/quiz/start",
    summary="Avvia una nuova sessione di quiz",
    description="Crea una nuova sessione di quiz per un determinato servizio e restituisce la prima domanda.",
    responses={
        200: {
            "description": "Sessione avviata con successo",
            "content": {
                "application/json": {
                    "example": {
                        "session_id": "b6b3405a-e42f-42e3-9b29-0d5419481aba",
                        "question": "Ciao! Vorrei conoscerti meglio per configurare al meglio il servizio. Puoi descrivermi brevemente di cosa si occupa la tua attività?",
                        "bullet_list": [],
                        "phase": "initial_question",
                        "turn_count": 1,
                        "max_turns": 30,
                        "has_context": False,
                        "done": False,
                        "email": "user@example.it"
                    }
                }
            },
        },
        400: {
            "description": "Richiesta non valida",
            "content": {
                "application/json": {
                    "example": {"detail": "Email è richiesta"}
                }
            },
        },
        500: {
            "description": "Errore interno del server",
            "content": {
                "application/json": {
                    "example": {"detail": "Errore durante l'avvio del quiz"}
                }
            },
        },
    },
)
async def start_quiz( 
    req: dict = Body(
            ...,
            example={
                "email": "user@example.it"
            },
            description="Parametri da inviare per iniziare un quiz",
        ),
    ):
    return await forward_post("/start", req)


@router.post(
    "/static-quiz",
    summary="Aggiorna i dati del quiz statico",
    description="""
    Aggiorna i dati di configurazione del servizio tramite quiz statico.
    
    Questo endpoint permette di aggiornare i seguenti campi per un servizio identificato dall'email:
    - **business_hours**: Orari di lavoro settimanali in formato JSON (0=Domenica, 1=Lunedì, ..., 6=Sabato)
    - **appointment_duration**: Durata degli appuntamenti in minuti
    - **email_signature**: Firma email personalizzata
    - **tone_of_voice**: Tono di voce da utilizzare nelle comunicazioni
    - **phone_numbers**: Numeri di telefono di contatto
    - **draft**: Indica se il profilo è in bozza (true) o definitivo (false)
    
    **Formato business_hours:**
    ```json
    {
      "0": ["09:00-17:00"],
      "1": ["09:00-12:00", "14:00-18:00"],
      "2": ["09:00-17:00"]
    }
    ```
    
    **Formato phone_numbers:**
    ```json
    {
      "principale": "+39 123 456 7890",
      "secondario": "+39 098 765 4321"
    }
    ```
    oppure
    ```json
    ["+39 123 456 7890", "+39 098 765 4321"]
    ```
    
    **Parametri:**
    - `email` (obbligatorio): Email del servizio da aggiornare
    - Tutti gli altri campi sono opzionali
    """,
    responses={
        200: {
            "description": "Dati aggiornati con successo",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Dati static quiz inseriti con successo",
                    }
                }
            }
        },
        400: {
            "description": "Richiesta non valida",
            "content": {
                "application/json": {
                    "examples": {
                        "missing_email": {
                            "summary": "Email mancante",
                            "value": {
                                "error": True,
                                "status_code": 400,
                                "detail": "Campi obbligatori mancanti: email"
                            }
                        },
                        "invalid_business_hours": {
                            "summary": "Formato business_hours non valido",
                            "value": {
                                "error": True,
                                "status_code": 400,
                                "detail": "business_hours deve essere un oggetto JSON"
                            }
                        },
                        "invalid_duration": {
                            "summary": "Durata appuntamento non valida",
                            "value": {
                                "error": True,
                                "status_code": 400,
                                "detail": "appointment_duration deve essere un numero intero positivo"
                            }
                        },
                        "no_updates": {
                            "summary": "Nessun campo da aggiornare",
                            "value": {
                                "error": True,
                                "status_code": 400,
                                "detail": "Nessun campo da aggiornare fornito"
                            }
                        }
                    }
                }
            }
        },
        404: {
            "description": "Servizio non trovato",
            "content": {
                "application/json": {
                    "example": {
                        "error": True,
                        "status_code": 404,
                        "detail": "Servizio con email 'user@example.com' non trovato"
                    }
                }
            }
        },
        500: {
            "description": "Errore interno del server",
            "content": {
                "application/json": {
                    "example": {
                        "error": True,
                        "status_code": 500,
                        "detail": "Errore database durante: aggiornamento dati static quiz"
                    }
                }
            }
        }
    }
)
def static_quiz(
    payload: dict = Body(
        ...,
        description="Dati per l'aggiornamento del quiz statico",
        examples=[{
            "email": "user@example.com",
            "business_hours": {
                "0": ["09:00-17:00"],
                "1": ["09:00-17:00"],
                "2": ["09:00-17:00"],
                "3": ["09:00-17:00"],
                "4": ["09:00-17:00"]
            },
            "appointment_duration": 30,
            "email_signature": "Cordiali saluti,\nIl Team",
            "tone_of_voice": "Professionale e cordiale",
            "phone_numbers": {
                "principale": "+39 123 456 7890",
                "secondario": "+39 098 765 4321"
            },
            "draft": True
        }]
    )
) -> dict:
    static_quiz = controller.static_quiz(payload)
    
    return {
        "success": static_quiz,
        "message": "Dati static quiz inseriti con successo",
    }


@router.post(
    "/quiz/answer",
    summary="Invia una risposta alla domanda corrente",
    description="Registra la risposta fornita e restituisce la prossima domanda, oppure il risultato finale se il quiz è completato.",
    responses={
        200: {
            "description": "Risposta elaborata con successo",
            "content": {
                "application/json": {
                    "examples": {
                        "collecting": {
                            "summary": "Quiz in fase di raccolta informazioni",
                            "value": {
                                "done": False,
                                "question": "Grazie! Ora parliamo degli orari di apertura. Quali sono i vostri orari?",
                                "bullet_list": [
                                    {"name": "Servizi offerti", "completed": True, "info": "Consulenza legale, assistenza contrattuale"},
                                    {"name": "Orari di apertura", "completed": False, "info": None},
                                    {"name": "Contatti", "completed": False, "info": None}
                                ],
                                "phase": "collecting",
                                "turn_count": 3,
                                "max_turns": 30,
                                "extracted_markdown": None,
                                "error": None,
                                "conversation_log": []
                            },
                        },
                        "reviewing": {
                            "summary": "Quiz in fase di revisione",
                            "value": {
                                "done": False,
                                "question": "Ecco il profilo aziendale che ho generato. Puoi modificarlo o confermare con 'OK, salva'.",
                                "bullet_list": [
                                    {"name": "Servizi offerti", "completed": True, "info": "..."},
                                    {"name": "Orari di apertura", "completed": True, "info": "..."}
                                ],
                                "phase": "reviewing",
                                "turn_count": 8,
                                "max_turns": 30,
                                "extracted_markdown": "# Profilo Aziendale\n\n## Servizi\n...",
                                "error": None,
                                "conversation_log": []
                            },
                        },
                        "completed": {
                            "summary": "Quiz completato",
                            "value": {
                                "done": True,
                                "question": "Perfetto. Ho salvato il contesto aziendale definitivo.",
                                "bullet_list": [],
                                "phase": "completed",
                                "turn_count": 10,
                                "max_turns": 30,
                                "extracted_markdown": "# Profilo Aziendale\n\n## Servizi\n...",
                                "error": None,
                                "save_started": True,
                                "conversation_log": [
                                    "[2024-01-01T12:00:00] [MODIFY] L'utente ha cambiato l'orario da 9-18 a 8-17"
                                ]
                            },
                        },
                    }
                }
            },
        },
        400: {
            "description": "Richiesta non valida",
            "content": {
                "application/json": {
                    "example": {"detail": "Session ID e risposta sono obbligatori"}
                }
            },
        },
        404: {
            "description": "Sessione non trovata",
            "content": {
                "application/json": {
                    "example": {"detail": "Sessione non trovata"}
                }
            },
        },
        500: {
            "description": "Errore interno durante l'invio della risposta",
            "content": {
                "application/json": {
                    "example": {"detail": "Errore durante l'invio della risposta"}
                }
            },
        },
    },
)
async def submit_answer(
    req: dict = Body(
            ...,
            example={
                "session_id": "b6b3405a-e42f-42e3-9b29-0d5419481aba",
	            "answer": "Siamo uno studio legale specializzato in diritto civile"
            },
            description="Parametri per inviare una risposta. Supporta sia 'answer' che 'value' come campo.",
        ),
):
    return await forward_post("/answer", req)


@router.get(
    "/quiz/{session_id}/state",
    summary="Recupera lo stato corrente della sessione",
    description="Restituisce tutte le informazioni sulla sessione del quiz incluso lo storico messaggi.",
    responses={
        200: {
            "description": "Stato della sessione recuperato con successo",
            "content": {
                "application/json": {
                    "example": {
                        "session_id": "b6b3405a-e42f-42e3-9b29-0d5419481aba",
                        "service_id": "srv_12345",
                        "phase": "collecting",
                        "turn_count": 5,
                        "max_turns": 30,
                        "business_field": "Studio legale",
                        "bullet_list": [
                            {"name": "Servizi offerti", "completed": True, "info": "Consulenza legale"},
                            {"name": "Orari", "completed": False, "info": None}
                        ],
                        "messages": [
                            {"role": "assistant", "content": "Ciao! Descrivi la tua attività."},
                            {"role": "user", "content": "Siamo uno studio legale."}
                        ],
                        "is_done": False,
                        "has_context": False,
                        "final_markdown": None
                    }
                }
            },
        },
        400: {
            "description": "Session ID mancante",
            "content": {
                "application/json": {
                    "example": {"detail": "Session ID è richiesto"}
                }
            },
        },
        404: {
            "description": "Sessione non trovata",
            "content": {
                "application/json": {
                    "example": {"detail": "Sessione non trovata"}
                }
            },
        },
        500: {
            "description": "Errore durante il recupero dello stato",
            "content": {
                "application/json": {
                    "example": {"detail": "Errore durante il recupero dello stato"}
                }
            },
        },
    },
)
async def get_state(session_id: str):
    return await forward_get(f"/{session_id}/state")


@router.post(
    "/quiz/finish",
    summary="Termina la sessione di quiz",
    description="Completa forzatamente la sessione di quiz e restituisce il profilo aziendale generato in formato markdown.",
    responses={
        200: {
            "description": "Quiz completato con successo",
            "content": {
                "application/json": {
                    "example": {
                        "done": True,
                        "extracted_markdown": "# Profilo Aziendale\n\n## Servizi\nConsulenza legale...",
                        "bullet_list": [
                            {"name": "Servizi", "completed": True, "info": "..."}
                        ],
                        "error": None
                    }
                }
            },
        },
        400: {
            "description": "Session ID mancante",
            "content": {
                "application/json": {
                    "example": {"detail": "Session ID è richiesto"}
                }
            },
        },
        404: {
            "description": "Sessione non trovata",
            "content": {
                "application/json": {
                    "example": {"detail": "Sessione non trovata"}
                }
            },
        },
        500: {
            "description": "Errore durante la conclusione del quiz",
            "content": {
                "application/json": {
                    "example": {"detail": "Errore durante la conclusione del quiz"}
                }
            },
        },
    },
)
async def finish_quiz(
    req: dict = Body(
            ...,
            example={
                "session_id": "b6b3405a-e42f-42e3-9b29-0d5419481aba",
            },
            description="Parametri per forzare la conclusione di un quiz",
        ),
):
    return await forward_post("/finish", req)


@router.post(
    "/quiz/save",
    summary="Avvia il salvataggio del contesto in background",
    description="""
    Avvia la pipeline di salvataggio del contesto (pulizia JSON, chunking, embedding e upload su Qdrant) in background.

    Questo endpoint evita di dover inviare un messaggio tipo "OK, salva" in chat: avvia direttamente la pipeline usando i dati
    raccolti fino a quel momento nella sessione quiz.
    """,
    responses={
        200: {
            "description": "Pipeline avviata con successo",
            "content": {
                "application/json": {
                    "example": {
                        "started": True,
                        "session_id": "b6b3405a-e42f-42e3-9b29-0d5419481aba",
                        "email": "user@example.it",
                    }
                }
            },
        },
        400: {
            "description": "Impossibile avviare il salvataggio",
            "content": {
                "application/json": {
                    "examples": {
                        "missing_session_id": {
                            "summary": "Session ID mancante",
                            "value": {"detail": "Session ID è richiesto"},
                        },
                        "already_running": {
                            "summary": "Pipeline già in esecuzione",
                            "value": {"detail": "Pipeline già in esecuzione per questa sessione"},
                        },
                    }
                }
            },
        },
        404: {
            "description": "Sessione non trovata",
            "content": {
                "application/json": {
                    "example": {"detail": "Sessione non trovata"}
                }
            },
        },
        500: {
            "description": "Errore interno del server",
            "content": {
                "application/json": {
                    "example": {"detail": "Errore durante l'avvio del salvataggio"}
                }
            },
        },
    },
)
async def save_quiz_context(
    req: dict = Body(
        ...,
        example={
            "session_id": "b6b3405a-e42f-42e3-9b29-0d5419481aba",
        },
        description="Parametri per avviare il salvataggio del contesto per una sessione quiz",
    ),
):
    return await forward_post("/save", req)


@router.get(
    "/quiz/save-status",
    summary="Monitora lo stato del salvataggio del contesto",
    description="""
    Recupera lo stato della pipeline di salvataggio del contesto (background).

    In Kubernetes con più pod lo stato è persistito su DB (quiz_sessions), quindi è sempre recuperabile.
    """,
    responses={
        200: {
            "description": "Stato recuperato con successo",
            "content": {
                "application/json": {
                    "examples": {
                        "running": {
                            "summary": "Pipeline in esecuzione",
                            "value": {
                                "session_id": "b6b3405a-e42f-42e3-9b29-0d5419481aba",
                                "email": "user@example.it",
                                "phase": "EMBEDDING",
                                "actual_step": 7,
                                "total_steps": 9,
                                "started_at": "2026-01-02T10:30:00+00:00",
                                "updated_at": "2026-01-02T10:32:15+00:00",
                                "completed_at": None,
                                "error": None,
                                "details": {"message": "Embedding di 45 chunks in corso...", "chunks_count": 45},
                                "run_id": "f1a2b3c4-d5e6-4a1b-9c2d-1234567890ab",
                                "worker": "pod-abc123:1234",
                                "is_running": True,
                                "is_completed": False,
                                "is_failed": False,
                                "save_status": "running",
                            },
                        },
                        "idle": {
                            "summary": "Pipeline non avviata (idle)",
                            "value": {
                                "session_id": "b6b3405a-e42f-42e3-9b29-0d5419481aba",
                                "email": "user@example.it",
                                "phase": "idle",
                                "actual_step": 0,
                                "total_steps": 9,
                                "started_at": None,
                                "updated_at": None,
                                "completed_at": None,
                                "error": None,
                                "details": {},
                                "run_id": None,
                                "worker": None,
                                "is_running": False,
                                "is_completed": False,
                                "is_failed": False,
                                "save_status": "idle",
                            },
                        },
                        "failed": {
                            "summary": "Pipeline fallita",
                            "value": {
                                "session_id": "b6b3405a-e42f-42e3-9b29-0d5419481aba",
                                "email": "user@example.it",
                                "phase": "UPLOADING_TO_QDRANT",
                                "actual_step": 8,
                                "total_steps": 9,
                                "started_at": "2026-01-02T10:30:00+00:00",
                                "updated_at": "2026-01-02T10:41:00+00:00",
                                "completed_at": "2026-01-02T10:41:00+00:00",
                                "error": "Upload su Qdrant fallito",
                                "details": {
                                    "message": "Upload su Qdrant: quiz_updated_user_example_it_20260102_103000",
                                    "collection_name": "quiz_updated_user_example_it_20260102_103000",
                                },
                                "run_id": "f1a2b3c4-d5e6-4a1b-9c2d-1234567890ab",
                                "worker": "pod-abc123:1234",
                                "is_running": False,
                                "is_completed": False,
                                "is_failed": True,
                                "save_status": "failed",
                            },
                        },
                    }
                }
            },
        },
        400: {
            "description": "Parametri mancanti",
            "content": {
                "application/json": {
                    "example": {"detail": "session_id o email è richiesto"}
                }
            },
        },
        404: {
            "description": "Sessione non trovata",
            "content": {
                "application/json": {
                    "example": {"detail": "Sessione non trovata"}
                }
            },
        },
        500: {
            "description": "Errore interno del server",
            "content": {
                "application/json": {
                    "example": {"detail": "Errore durante il recupero dello stato di salvataggio"}
                }
            },
        },
    },
)
async def get_quiz_save_status(
    session_id: Optional[str] = Query(None, description="ID sessione quiz"),
    email: Optional[str] = Query(None, description="Email del servizio"),
):
    if not session_id and not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="session_id o email è richiesto",
        )

    params: dict[str, str] = {}
    if session_id:
        params["session_id"] = session_id
    if email:
        params["email"] = email

    query = urlencode(params)
    return await forward_get(f"/save-status?{query}")


@router.get(
    "/quiz/sessions",
    summary="Elenca le sessioni attive",
    description="Restituisce una lista degli ID di sessione attualmente attivi nel sistema.",
    responses={
        200: {
            "description": "Elenco delle sessioni recuperato con successo",
            "content": {
                "application/json": {
                    "example": ["b6b3405a-e42f-42e3-9b29-0d5419481aba", "c7c4516b-f53g-53f4-0c3a-1e6520592bcb"]
                }
            },
        },
        500: {
            "description": "Errore durante il recupero delle sessioni",
            "content": {
                "application/json": {
                    "example": {"detail": "Errore durante il recupero delle sessioni"}
                }
            },
        },
    },
)
async def list_sessions():
    return await forward_get("/sessions")

@router.get(
    "/information/{email}",
    summary="Recupera il campo information di un servizio",
    description="""
    Restituisce il contenuto del campo `information` per il servizio specificato tramite email.
    
    Il campo `information` contiene un documento testuale in formato Markdown che descrive in modo dettagliato
    il profilo aziendale completo, includendo:
    - Contesto aziendale e storia
    - Mission e Vision
    - Valori aziendali
    - Servizi offerti (dettaglio completo)
    - Tipologie di clienti
    - Metodologie di lavoro
    - Organizzazione interna
    - Piani di supporto
    - Settori di attività
    - KPI aziendali
    - Sicurezza e conformità
    - Progetti tipici
    - Dati legali e contatti
    
    Questo documento è utilizzato dai sistemi AI per comprendere il contesto aziendale completo
    e fornire risposte accurate e personalizzate alle richieste dei clienti.
    """,
    responses={
        200: {
            "description": "Information recuperato con successo",
            "content": {
                "application/json": {
                    "example": "# 📌 Contesto Aziendale Esteso\n**SoftWave Solutions S.r.l. – Profilo Aziendale Completo**\n\n---\n\n# 🏢 1. Chi Siamo\n**SoftWave Solutions S.r.l.** è una software house italiana con sede principale a Milano...\n\n# 🎯 2. Mission\nSupportare aziende nella loro evoluzione digitale...\n\n# 🛠️ 5. Servizi Offerti\n## 5.1 Sviluppo Software\n### 🔹 Web Development\n- Applicazioni web enterprise\n- Piattaforme SaaS multi-tenant...\n\n[Il documento completo contiene tutte le sezioni del profilo aziendale]"
                }
            }
        },
        400: {
            "description": "Parametri mancanti",
            "content": {
                "application/json": {
                    "example": {"detail": "Campi richiesti mancanti: email"}
                }
            }
        },
        404: {
            "description": "Informazioni non trovate",
            "content": {
                "application/json": {
                    "example": {"detail": "Informazioni non trovate per email=xxx"}
                }
            }
        },
        500: {"description": "Errore interno del server"}
    }
)
def get_information(email: str):
    information = controller.get_information(email)
    return information


@router.patch(
    "/information/{email}",
    summary="Aggiorna il campo information di un servizio",
    description="""
    Aggiorna il campo `information` per il servizio specificato tramite email.
    
    Il campo `information` deve contenere un documento testuale completo in formato Markdown
    che descrive il profilo aziendale esteso.
    
    **Struttura Raccomandata del Documento:**
    - Contesto Aziendale (Chi Siamo, Storia, Fondazione)
    - Mission & Vision
    - Valori Aziendali
    - Servizi Offerti (con dettagli tecnici completi)
    - Tipologie di Clienti e Settori
    - Metodologie di Lavoro (Agile, DevOps, ecc.)
    - Organizzazione Interna (Team, Reparti)
    - Piani di Supporto e SLA
    - KPI Aziendali
    - Sicurezza e Conformità (GDPR, ISO, ecc.)
    - Progetti Tipici Realizzati
    - Dati Legali (Ragione Sociale, P.IVA, Sede, ecc.)
    - Contatti e Canali Social
    
    ** Nota Importante:** 
    L'aggiornamento sostituisce completamente il contenuto esistente del campo information.
    Assicurati di inviare il documento completo aggiornato.
    
    **Utilizzo:** 
    Questo documento viene utilizzato dai sistemi AI per comprendere il contesto aziendale
    e fornire risposte accurate, personalizzate e contestualizzate alle richieste dei clienti.
    """,
    responses={
        200: {
            "description": "Information aggiornato con successo",
            "content": {
                "application/json": {
                    "example": "# 📌 Contesto Aziendale Esteso\n**SoftWave Solutions S.r.l. – Profilo Aziendale Completo (Aggiornato)**\n\n---\n\n# 🏢 1. Chi Siamo\n**SoftWave Solutions S.r.l.** è una software house italiana...\n\n# 🎯 2. Mission\nSupportare aziende nella loro evoluzione digitale...\n\n# 🛠️ 5. Servizi Offerti\n## 5.1 Sviluppo Software\n### 🔹 Web Development\n- Applicazioni web enterprise\n- Piattaforme SaaS...\n\n[Documento completo aggiornato]"
                }
            }
        },
        400: {
            "description": "Richiesta non valida",
            "content": {
                "application/json": {
                    "examples": {
                        "missing_params": {
                            "value": {"detail": "Campi richiesti mancanti: email"}
                        },
                        "no_data": {
                            "value": {"detail": "Nessun dato da aggiornare"}
                        },
                        "invalid_format": {
                            "value": {"detail": "Information deve essere un testo (string)"}
                        }
                    }
                }
            }
        },
        404: {
            "description": "Servizio non trovato",
            "content": {
                "application/json": {
                    "example": {"detail": "Servizio non trovato per email=xxx"}
                }
            }
        },
        500: {"description": "Errore interno del server"}
    }
)
def update_information(
    subscription_id: str,
    email: str,
    payload: str = Body(
        ...,
        example="""# 📌 Contesto Aziendale Esteso e Ultra-Dettagliato
            **SoftWave Solutions S.r.l. – Profilo Aziendale Completo (Versione Estesa)**

            ---

            # 🏢 1. Chi Siamo
            **SoftWave Solutions S.r.l.** è una software house italiana con sede principale a Milano, attiva dal 2012 nello sviluppo di soluzioni digitali personalizzate ad alte prestazioni.

            # 🎯 2. Mission
            Supportare aziende di ogni dimensione nella loro evoluzione digitale attraverso:
            - Soluzioni software sicure, scalabili e altamente personalizzate
            - Approccio consulenziale che unisce tecnologia e comprensione dei processi aziendali

            # 🛠️ 5. Servizi Offerti (Dettaglio Esteso)
            ## 5.1 Sviluppo Software
            ### 🔹 Web Development
            - Applicazioni web enterprise
            - Piattaforme SaaS multi-tenant
            - Dashboard di Business Intelligence

            # 📞 15. Contatti
            - **Telefono:** +39 02 1234567
            - **Email Generale:** info@softwavesolutions.it
            - **Supporto Tecnico:** support@softwavesolutions.it

            [...resto del documento...]""",
        description="Documento testuale completo in formato Markdown con il profilo aziendale esteso.",
    )
):
    updated_info = controller.update_information(email, payload)
    return updated_info


@router.get(
    "/get_subscription_service/{subscription_id}",
    summary="Recupera tutti i servizi associati a una sottoscrizione",
    description=(
        "Restituisce una lista di tutti i record della tabella `subscription_services` collegati alla sottoscrizione indicata. "
        "Il contenuto restituito varia in base al provider del servizio (Google, Microsoft o provider personalizzato IMAP). "
        "\n\nL'endpoint ritorna tutti i servizi (email) associati alla subscription_id specificata."
    ),
    responses={
        200: {
            "description": "Lista dei servizi associati alla sottoscrizione",
            "content": {
                "application/json": {
                    "examples": {
                        "multiple_services": {
                            "summary": "Subscription con più servizi (Google e Microsoft)",
                            "value": [
                                {
                                    "email": "user@gmail.com",
                                    "email_provider": "google",
                                    "calendar_provider": "google",
                                    "calendar_names": None,
                                    "information": None,
                                    "imap_server": None,
                                    "imap_port": None,
                                    "smtp_server": None,
                                    "smtp_port": None,
                                    "hashed_password": None,
                                    "hashed_access_token": "token",
                                    "hashed_refresh_token": "token",
                                    "expiry_token": "2025-11-07T18:13:22.691046Z",
                                    "confidence_response_threshold": 0.8,
                                    "confidence_review_mail": 0.7,
                                    "priority_threshold": 0.6,
                                    "confidence_classification_threshold": 0.75,
                                    "urgent_meeting_threshold": 0.9,
                                    "history_id": "2425387",
                                    "microsoft_subscription_id_inbound": None,
                                    "microsoft_subscription_id_outbound": None,
                                    "microsoft_expiration_datetime_inbound": None,
                                    "microsoft_expiration_datetime_outbound": None,
                                    "oauth_user_id": None
                                },
                                {
                                    "email": "user@outlook.com",
                                    "email_provider": "microsoft",
                                    "calendar_provider": "microsoft",
                                    "calendar_names": None,
                                    "information": None,
                                    "imap_server": None,
                                    "imap_port": None,
                                    "smtp_server": None,
                                    "smtp_port": None,
                                    "hashed_password": None,
                                    "hashed_access_token": "token",
                                    "hashed_refresh_token": "token",
                                    "expiry_token": "2025-11-07T18:43:23.158594Z",
                                    "confidence_response_threshold": 0.8,
                                    "confidence_review_mail": 0.7,
                                    "priority_threshold": 0.6,
                                    "confidence_classification_threshold": 0.75,
                                    "urgent_meeting_threshold": 0.9,
                                    "history_id": None,
                                    "microsoft_subscription_id_inbound": "fdf98a28-a9e9-4111-8294-ae669735713c",
                                    "microsoft_subscription_id_outbound": "b474af03-2b22-42f8-bc5c-39cafec4c147",
                                    "microsoft_expiration_datetime_inbound": "2025-11-09T17:47:52Z",
                                    "microsoft_expiration_datetime_outbound": "2025-11-09T17:47:55Z",
                                    "oauth_user_id": None
                                }
                            ]
                        },
                        "single_imap_service": {
                            "summary": "Subscription con un solo servizio IMAP",
                            "value": [
                                {
                                    "email": "user@custommail.com",
                                    "email_provider": "imap",
                                    "calendar_provider": None,
                                    "calendar_names": None,
                                    "information": None,
                                    "imap_server": "imaps.custommail.com",
                                    "imap_port": 993,
                                    "smtp_server": "smtps.custommail.com",
                                    "smtp_port": 465,
                                    "hashed_password": "token",
                                    "hashed_access_token": None,
                                    "hashed_refresh_token": None,
                                    "expiry_token": None,
                                    "confidence_response_threshold": 0.8,
                                    "confidence_review_mail": 0.7,
                                    "priority_threshold": 0.6,
                                    "confidence_classification_threshold": 0.75,
                                    "urgent_meeting_threshold": 0.9,
                                    "history_id": None,
                                    "microsoft_subscription_id_inbound": None,
                                    "microsoft_subscription_id_outbound": None,
                                    "microsoft_expiration_datetime_inbound": None,
                                    "microsoft_expiration_datetime_outbound": None,
                                    "oauth_user_id": None
                                }
                            ]
                        }
                    }
                }
            }
        },
        400: {
            "description": "Parametri mancanti",
            "content": {
                "application/json": {
                    "example": {"detail": "Campi richiesti mancanti: subscription_id"}
                }
            }
        },
        404: {
            "description": "Nessun servizio associato trovato per la subscription_id specificata",
            "content": {
                "application/json": {
                    "example": {"detail": "Nessun servizio trovato per subscription_id=xxx"}
                }
            }
        },
        500: {
            "description": "Errore interno del server",
            "content": {
                "application/json": {
                    "example": {"detail": "Errore database durante: recupero servizi"}
                }
            }
        }
    }
)
async def get_services_by_subscription(subscription_id: str):
    return controller.get_services_by_subscription(subscription_id)
