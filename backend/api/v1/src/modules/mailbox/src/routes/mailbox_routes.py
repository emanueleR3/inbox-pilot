from fastapi import APIRouter, Body, Query, status
from typing import Dict, Any, Optional

from fastapi.params import Depends
from src.core.dependecy import get_current_user
from src.modules.mailbox.src.controllers.mailbox_controller import MailboxController

router = APIRouter(
    dependencies=[Depends(get_current_user)],
    tags=["Mailbox"]
)

controller = MailboxController()

@router.post(
    "/threads/inbox",
    status_code=status.HTTP_200_OK,
    summary="Recupera inbox thread",
    description=(
        "Recupera la lista dei thread presenti nella inbox per una specifica casella (box_email). "
        "Supporta filtri (status, category, subcategory) e paginazione (limit/offset). "
        "I risultati sono ordinati per last_message_at decrescente.\n\n"
        "Note:\n"
        "- box_email è obbligatorio\n"
        "- limit/offset vengono applicati a livello di query (range)"
    ),
    responses={
        200: {
            "description": "Lista di thread (EmailThreadSummary)",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "thread_id": "th_123",
                            "subject": "Richiesta informazioni",
                            "category": "INFO_REQUESTED",
                            "subcategory": "PRICING",
                            "status": "HUMAN_REVIEW",
                            "last_message_at": "2026-01-06T10:15:30Z",
                            "last_sender_email": "cliente@example.com",
                            "human_response": False,
                            "summary": "Il cliente chiede dettagli sul pricing.",
                            "email_count": 3,
                            "has_attachments": False,
                            "max_priority": 0.82
                        }
                    ]
                }
            },
        },
        400: {
            "description": "Richiesta non valida (es. campo obbligatorio mancante)",
            "content": {
                "application/json": {
                    "examples": {
                        "missing_box_email": {
                            "summary": "Campo obbligatorio mancante",
                            "value": {"detail": "Campi obbligatori mancanti: box_email"},
                        }
                    }
                }
            },
        },
        500: {
            "description": "Errore interno / errore database",
            "content": {
                "application/json": {
                    "examples": {
                        "database_error": {
                            "summary": "Errore database",
                            "value": {"detail": "Errore database durante: <dettaglio>"},
                        }
                    }
                }
            },
        },
    }
)
def get_inbox_threads(
    payload: dict = Body(
        ...,
        example={
            "box_email": "support@azienda.com",
            "status": "HUMAN_REVIEW",
            "category": "INFO_REQUESTED",
            "limit": 50,
            "offset": 0
        }
    )
):
    return controller.get_inbox_threads(payload)

@router.get(
    "/threads/human-review",
    status_code=status.HTTP_200_OK,
    summary="Recupera thread in HUMAN_REVIEW",
    description=(
        "Recupera i thread che richiedono revisione umana (vista dedicata). "
        "Supporta paginazione con limit/offset. "
        "I risultati sono ordinati per last_message_at decrescente."
    ),
    responses={
        200: {
            "description": "Lista di thread in HUMAN_REVIEW (EmailThreadSummary)",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "thread_id": "th_456",
                            "subject": "Problema ordine",
                            "category": "SUPPORT",
                            "subcategory": None,
                            "status": "HUMAN_REVIEW",
                            "last_message_at": "2026-01-06T09:01:00Z",
                            "last_sender_email": "utente@example.com",
                            "human_response": False,
                            "summary": None,
                            "email_count": 1,
                            "has_attachments": True,
                            "max_priority": 0.95
                        }
                    ]
                }
            },
        },
        500: {
            "description": "Errore interno / errore database",
            "content": {
                "application/json": {
                    "example": {"detail": "Errore database durante: <dettaglio>"}
                }
            },
        },
    }
)
def get_human_review_threads(
    email: str = Query(..., description="Email del box"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0)
):
    return controller.get_human_review_threads(email, limit, offset)


@router.get(
    "/threads/{thread_id}",
    status_code=status.HTTP_200_OK,
    summary="Recupera conversazione thread",
    description=(
        "Ricostruisce l'intera conversazione di un thread (dettaglio + lista messaggi). "
        "I messaggi sono ordinati per datetime crescente (dal più vecchio al più recente)."
    ),
    responses={
        200: {
            "description": "Dettaglio thread (EmailThreadDetail)",
            "content": {
                "application/json": {
                    "example": {
                        "thread_id": "th_123",
                        "subject": "Richiesta informazioni",
                        "messages": [
                            {
                                "id": "em_1",
                                "subject": "Richiesta informazioni",
                                "body": "Buongiorno, vorrei informazioni...",
                                "direction": "INBOUND",
                                "outcome": None,
                                "datetime": "2026-01-05T08:00:00Z",
                                "has_attachment": False,
                                "ai_generated": False,
                                "priority_score": 0.4
                            },
                            {
                                "id": "em_2",
                                "subject": "Re: Richiesta informazioni",
                                "body": "Grazie, ecco i dettagli...",
                                "direction": "OUTBOUND",
                                "outcome": "SENT",
                                "datetime": "2026-01-05T09:00:00Z",
                                "has_attachment": False,
                                "ai_generated": True,
                                "priority_score": None
                            }
                        ],
                        "message_count": 2
                    }
                }
            },
        },
        404: {
            "description": "Thread non trovato",
            "content": {"application/json": {"example": {"detail": "Thread non trovato"}}},
        },
        500: {
            "description": "Errore interno / errore database",
            "content": {
                "application/json": {
                    "example": {"detail": "Errore database durante: <dettaglio>"}
                }
            },
        },
    }
)
def get_thread_conversation(thread_id: str):
    return controller.get_thread_conversation(thread_id)


@router.get(
    "/emails/outbound/failed/{subscription_service_id}",
    status_code=status.HTTP_200_OK,
    summary="Email outbound fallite",
    description=(
        "Recupera le email in uscita (OUTBOUND) che hanno riscontrato errori di invio, "
        "ordinate per datetime decrescente."
    ),
    responses={
        200: {
            "description": "Lista email outbound fallite (FailedOutboundEmail)",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "email_id": "em_fail_1",
                            "thread_id": "th_999",
                            "datetime": "2026-01-06T11:30:00Z",
                            "outcome": "SMTP_ERROR",
                            "body": "...contenuto email..."
                        }
                    ]
                }
            },
        },
        500: {
            "description": "Errore interno / errore database",
            "content": {
                "application/json": {
                    "example": {"detail": "Errore database durante: <dettaglio>"}
                }
            },
        },
    }
)
def get_failed_outbound_emails(subscription_service_id: str):
    return controller.get_failed_outbound_emails(subscription_service_id)

@router.get(
    "/threads/by-category",
    status_code=status.HTTP_200_OK,
    summary="Thread per categoria",
    description=(
        "Recupera i thread filtrati per categoria (obbligatoria) e subcategory (opzionale). "
        "I risultati sono ordinati per last_message_at decrescente.\n\n"
        "Nota: questa rotta non applica limit/offset (ritorna tutti i risultati della query)."
    ),
    responses={
        200: {
            "description": "Lista di thread (EmailThreadSummary)",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "thread_id": "th_777",
                            "subject": "Domanda su fatturazione",
                            "category": "BILLING",
                            "subcategory": "INVOICE",
                            "status": "OPEN",
                            "last_message_at": "2026-01-04T14:20:00Z",
                            "last_sender_email": "cliente@example.com",
                            "human_response": True,
                            "summary": "Richiesta copia fattura.",
                            "email_count": 2,
                            "has_attachments": False,
                            "max_priority": 0.2
                        }
                    ]
                }
            },
        },
        400: {
            "description": "Richiesta non valida (es. category mancante)",
            "content": {
                "application/json": {
                    "example": {"detail": "Campi obbligatori mancanti: category"}
                }
            },
        },
        500: {
            "description": "Errore interno / errore database",
            "content": {
                "application/json": {
                    "example": {"detail": "Errore database durante: <dettaglio>"}
                }
            },
        },
    },
)
def get_threads_by_category(
    category: str,
    subcategory: Optional[str] = None
):
    return controller.get_threads_by_category(category, subcategory)


# =============================================================================
# INVIO EMAIL
# =============================================================================

@router.post(
    "/send",
    status_code=status.HTTP_200_OK,
    summary="Invia email",
    description="""
    Invia una email tramite Google Gmail API o Microsoft Graph API.
    
    **Provider supportati:**
    - `google`: Gmail API
    - `microsoft`: Microsoft Graph API (Outlook)
    
    **Autenticazione:**
    L'email del mittente deve corrispondere a un account registrato con token OAuth valido.
    
    **Campi obbligatori:**
    - `provider`: Provider email ("google" o "microsoft")
    - `email`: Email del mittente (account autenticato)
    - `to`: Lista di destinatari
    - `subject`: Oggetto dell'email
    - `body`: Corpo dell'email (testo o HTML)
    
    **Campi opzionali:**
    - `cc`: Lista di indirizzi in copia
    - `bcc`: Lista di indirizzi in copia nascosta
    - `reply_to`: Indirizzo per le risposte
    - `attachments`: Lista di allegati (base64 encoded)
    - `is_html`: Se True, il body viene interpretato come HTML
    
    **Formato allegati:**
    Ogni allegato deve avere:
    - `filename`: Nome del file
    - `content`: Contenuto in base64
    - `content_type`: MIME type (default: application/octet-stream)
    """,
    responses={
        200: {
            "description": "Email inviata con successo",
            "content": {
                "application/json": {
                    "examples": {
                        "success": {
                            "summary": "Invio riuscito",
                            "value": {
                                "success": True,
                                "message_id": "18d1a2b3c4d5e6f7",
                                "message": "Email inviata con successo"
                            }
                        }
                    }
                }
            }
        },
        400: {
            "description": "Richiesta non valida - parametri mancanti o non validi",
            "content": {
                "application/json": {
                    "examples": {
                        "missing_fields": {
                            "summary": "Campi obbligatori mancanti",
                            "value": {
                                "error": True,
                                "status_code": 400,
                                "detail": "Campi obbligatori mancanti: provider, email, to"
                            }
                        },
                        "invalid_provider": {
                            "summary": "Provider non valido",
                            "value": {
                                "error": True,
                                "status_code": 400,
                                "detail": "Campo 'provider' non valido: deve essere 'google' o 'microsoft'"
                            }
                        },
                        "invalid_email": {
                            "summary": "Indirizzo email non valido",
                            "value": {
                                "error": True,
                                "status_code": 400,
                                "detail": "Campo 'to' non valido: indirizzo email non valido: invalid-email"
                            }
                        }
                    }
                }
            }
        },
        401: {
            "description": "Token non valido o scaduto",
            "content": {
                "application/json": {
                    "examples": {
                        "google_token": {
                            "summary": "Token Google non valido",
                            "value": {
                                "error": True,
                                "status_code": 401,
                                "detail": "Token Google non valido"
                            }
                        },
                        "microsoft_token": {
                            "summary": "Token Microsoft non valido",
                            "value": {
                                "error": True,
                                "status_code": 401,
                                "detail": "Token Microsoft non valido"
                            }
                        }
                    }
                }
            }
        },
        502: {
            "description": "Errore di comunicazione con il servizio esterno",
            "content": {
                "application/json": {
                    "examples": {
                        "gmail_error": {
                            "summary": "Errore Gmail API",
                            "value": {
                                "error": True,
                                "status_code": 502,
                                "detail": "Errore servizio Gmail: Status code 403: Forbidden"
                            }
                        },
                        "graph_error": {
                            "summary": "Errore Microsoft Graph",
                            "value": {
                                "error": True,
                                "status_code": 502,
                                "detail": "Errore servizio Microsoft Graph: Timeout durante l'invio dell'email"
                            }
                        }
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
                        "detail": "Errore interno del server"
                    }
                }
            }
        }
    }
)
async def send_email(
    payload: Dict[str, Any] = Body(
        ...,
        example={
            "provider": "google",
            "email": "mittente@example.com",
            "to": ["destinatario@example.com"],
            "subject": "Oggetto dell'email",
            "body": "Contenuto dell'email",
            "cc": ["copia@example.com"],
            "bcc": ["nascosta@example.com"],
            "reply_to": "risposta@example.com",
            "is_html": False,
            "attachments": [
                {
                    "filename": "documento.pdf",
                    "content": "base64-encoded-content",
                    "content_type": "application/pdf"
                }
            ]
        }
    )
):
    return await controller.send_email(payload)
