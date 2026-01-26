from fastapi import APIRouter, Body, Query, status
from typing import Dict, Any, Optional
from src.modules.mailbox.src.controllers.mailbox_controller import MailboxController

router = APIRouter(
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
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0)
):
    return controller.get_human_review_threads(limit, offset)


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
    "/emails/outbound/failed",
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
def get_failed_outbound_emails():
    return controller.get_failed_outbound_emails()

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
