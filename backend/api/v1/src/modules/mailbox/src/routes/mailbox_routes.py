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
    description="Recupera la lista dei thread con filtri e paginazione.",
    responses={
        200: {"description": "Inbox recuperata con successo"},
        400: {"description": "Richiesta non valida"},
        500: {"description": "Errore interno"}
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
    description="Recupera i thread che richiedono revisione umana.",
    responses={
        200: {"description": "Thread HUMAN_REVIEW recuperati"},
        500: {"description": "Errore interno"}
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
    description="Ricostruisce l'intera conversazione di un thread.",
    responses={
        200: {"description": "Conversazione recuperata"},
        404: {"description": "Thread non trovato"},
        500: {"description": "Errore interno"}
    }
)
def get_thread_conversation(thread_id: str):
    return controller.get_thread_conversation(thread_id)


@router.get(
    "/emails/outbound/failed",
    status_code=status.HTTP_200_OK,
    summary="Email outbound fallite",
    description="Recupera le email OUTBOUND con errori di invio.",
    responses={
        200: {"description": "Email fallite recuperate"},
        500: {"description": "Errore interno"}
    }
)
def get_failed_outbound_emails():
    return controller.get_failed_outbound_emails()

@router.get(
    "/threads/by-category",
    status_code=status.HTTP_200_OK,
    summary="Thread per categoria",
    description="Recupera thread filtrati per categoria e subcategory.",
)
def get_threads_by_category(
    category: str,
    subcategory: Optional[str] = None
):
    return controller.get_threads_by_category(category, subcategory)
