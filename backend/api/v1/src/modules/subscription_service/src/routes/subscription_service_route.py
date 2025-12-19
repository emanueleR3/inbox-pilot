from fastapi import APIRouter, Body, Depends
from src.core.dependecy import get_current_user
from src.modules.subscription_service.src.controllers.subscription_service_controller import SubscriptionServiceController
from src.modules.subscription_service.src.utils.utils import forward_post, forward_get

router = APIRouter(
    #dependencies=[Depends(get_current_user)],
    tags=["Subscription Service"],
)
controller = SubscriptionServiceController()

@router.get(
    "/get-config/{subscription_id}",
    summary="Recupera la configurazione di un abbonamento",
    description="Restituisce i parametri di configurazione associati all'abbonamento specificato.",
    responses={
        200: {
            "description": "Configurazione trovata con successo",
            "content": {
                "application/json": {
                    "example": {
                        "status": "ok",
                        "result": {
                            "confidence_response_threshold": 0.8,
                            "confidence_review_mail": 0.7,
                            "priority_threshold": 0.5,
                            "confidence_classification_threshold": 0.75,
                            "urgent_meeting_threshold": 0.9,
                        },
                    }
                }
            },
        },
        400: {
            "description": "Richiesta non valida",
            "content": {
                "application/json": {
                    "example": {"detail": "ID sottoscrizione richiesto"}
                }
            }
        },
        404: {
            "description": "Configurazione non trovata",
            "content": {
                "application/json": {
                    "example": {"detail": "Configurazione con ID {subscription_id} non trovata"}
                }
            }
        },
        500: {
            "description": "Errore interno del server",
            "content": {
                "application/json": {
                    "example": {"detail": "Errore durante il recupero della configurazione"}
                }
            }
        }
    },
)
def get_configuration(subscription_id: str):
    result = controller.get_configuration(subscription_id)
    fields = [
        "confidence_response_threshold",
        "confidence_review_mail",
        "priority_threshold",
        "confidence_classification_threshold",
        "urgent_meeting_threshold",
    ]
    if not result:
        return {"status": "not_found"}
    filtered = {k: result.get(k) for k in fields}
    return {"status": "ok", "result": filtered}

@router.patch(
    "/update-config/{subscription_id}",
    summary="Aggiorna una configurazione esistente",
    description="Aggiorna uno o più parametri di configurazione per un abbonamento esistente.",
    responses={
        200: {
            "description": "Configurazione aggiornata con successo",
            "content": {
                "application/json": {
                    "example": {
                        "status": "ok",
                        "result": {
                            "subscription_id": "sub_12345",
                            "confidence_response_threshold": 0.9,
                            "priority_threshold": 0.6,
                        },
                    }
                }
            },
        },
        400: {
            "description": "Richiesta non valida",
            "content": {
                "application/json": {
                    "examples": {
                        "missing_id": {
                            "value": {"detail": "ID sottoscrizione richiesto"}
                        },
                        "missing_updates": {
                            "value": {"detail": "Nessun aggiornamento fornito"}
                        },
                        "invalid_fields": {
                            "value": {"detail": "Campi non validi per l'aggiornamento"}
                        },
                        "invalid_values": {
                            "value": {"detail": "I valori devono essere numeri tra 0 e 1"}
                        }
                    }
                }
            }
        },
        404: {
            "description": "Configurazione non trovata",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Configurazione con ID {subscription_id} non trovata"
                    }
                }
            }
        },
        500: {
            "description": "Errore interno del server",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Errore durante l'aggiornamento della configurazione"
                    }
                }
            }
        },
        400: {
            "description": "Richiesta non valida",
            "content": {
                "application/json": {
                    "examples": {
                        "missing_id": {
                            "value": {"detail": "ID sottoscrizione richiesto"}
                        },
                        "missing_updates": {
                            "value": {"detail": "Nessun aggiornamento fornito"}
                        },
                        "invalid_fields": {
                            "value": {"detail": "Campi non validi per l'aggiornamento"}
                        },
                        "invalid_values": {
                            "value": {"detail": "I valori devono essere numeri tra 0 e 1"}
                        }
                    }
                }
            }
        },
        404: {
            "description": "Configurazione non trovata",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Configurazione con ID {subscription_id} non trovata"
                    }
                }
            }
        },
        500: {
            "description": "Errore interno del server",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Errore durante l'aggiornamento della configurazione"
                    }
                }
            }
        },
    },
)
def update_configuration(
    subscription_id: str,
    payload: dict = Body(
        ...,
        example={
            "confidence_response_threshold": 0.9,
            "priority_threshold": 0.6,
        },
        description="Parametri da aggiornare nella configurazione dell'abbonamento.",
    ),
):
    updated = controller.update_configuration(subscription_id, payload)
    return {"status": "ok", "result": updated}


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
    "/get_subscription_service/{subscription_id}/{email}",
    summary="Recupera i servizi associati a una sottoscrizione",
    description=(
        "Restituisce tutti i record della tabella `subscription_services` collegati alla sottoscrizione indicata. "
        "Il contenuto restituito varia in base al provider del servizio (Google, Microsoft o provider personalizzato IMAP)."
    ),
    responses={
        200: {
            "description": "Servizi trovati",
            "content": {
                "application/json": {
                    "examples": {
                        "google": {
                            "summary": "Servizio Google",
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
                                }
                            ]
                        },
                        "microsoft": {
                            "summary": "Servizio Microsoft",
                            "value": [
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
                        "imap": {
                            "summary": "Servizio IMAP personalizzato",
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
        404: {"description": "Nessun servizio associato trovato"},
        500: {"description": "Errore interno del server"}
    }
)
async def get_services_by_subscription(subscription_id: str, email: str):
    return controller.get_services_by_subscription(subscription_id, email)
