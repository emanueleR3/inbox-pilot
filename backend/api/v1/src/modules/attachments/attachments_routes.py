from fastapi import APIRouter, Query, status
from fastapi.params import Depends
from fastapi.responses import FileResponse
from src.core.dependecy import get_current_user
from src.modules.attachments.attachments_controller import AttachmentsController

router = APIRouter(
    dependencies=[Depends(get_current_user)],
    tags=["Attachments"]
)

controller = AttachmentsController()


@router.get(
    "/",
    status_code=status.HTTP_200_OK,
    summary="Lista attachments per service_id",
    description=(
        "Recupera la lista degli attachments per un dato service_id (subscription_service). "
        "I risultati sono ordinati per data di creazione decrescente e supportano paginazione.\n\n"
        "Note:\n"
        "- service_id è obbligatorio\n"
        "- Restituisce i metadati degli allegati con il contesto dell'email associata\n"
        "- Se il thread non è disponibile, email_context.available sarà False"
    ),
    responses={
        200: {
            "description": "Lista di attachments con paginazione e contesto email",
            "content": {
                "application/json": {
                    "example": {
                        "attachments": [
                            {
                                "attachment_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                                "thread_id": "t1t2t3t4-t5t6-7890-abcd-ef1234567890",
                                "email_id": "e1e2e3e4-e5e6-7890-abcd-ef1234567890",
                                "sender": "cliente@example.com",
                                "receiver": "azienda@example.com",
                                "cc": ["cc1@example.com"],
                                "file_name": "documento.pdf",
                                "mime_type": "application/pdf",
                                "size_bytes": 125000,
                                "created_at": "2026-02-16T10:30:00Z",
                                "service_id": "s1s2s3s4-s5s6-7890-abcd-ef1234567890",
                                "email_context": {
                                    "subject": "Richiesta preventivo",
                                    "sender_email": "cliente@example.com",
                                    "cc_emails": ["cc1@example.com"],
                                    "summary": "Il cliente richiede un preventivo per...",
                                    "category": "INFO_REQUESTED",
                                    "subcategory": "PRICING",
                                    "started_at": "2026-02-16T10:00:00Z",
                                    "last_message_at": "2026-02-16T10:30:00Z",
                                    "available": True
                                }
                            }
                        ],
                        "total": 150,
                        "limit": 50,
                        "offset": 0
                    }
                }
            },
        },
        400: {
            "description": "Richiesta non valida",
            "content": {
                "application/json": {
                    "example": {"detail": "Campi obbligatori mancanti: service_id"}
                }
            },
        },
        500: {
            "description": "Errore interno del server",
            "content": {
                "application/json": {
                    "example": {"detail": "Errore database durante: recupero attachments"}
                }
            },
        },
    }
)
def get_attachments(
    service_id: str = Query(..., description="ID del subscription service"),
    limit: int = Query(50, ge=1, le=200, description="Numero massimo di risultati"),
    offset: int = Query(0, ge=0, description="Offset per paginazione")
):
    return controller.get_attachments_by_service_id(
        service_id=service_id,
        limit=limit,
        offset=offset
    )


@router.get(
    "/{attachment_id}/preview",
    summary="Metadati attachment per preview",
    description=(
        "Restituisce i metadati completi di un attachment per visualizzazione. "
        "Include tutte le informazioni sull'attachment e il contesto dell'email associata.\n\n"
        "Se il thread non è disponibile, email_context.available sarà False."
    ),
    responses={
        200: {
            "description": "Metadati attachment con contesto email",
            "content": {
                "application/json": {
                    "example": {
                        "attachment_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                        "thread_id": "t1t2t3t4-t5t6-7890-abcd-ef1234567890",
                        "email_id": "e1e2e3e4-e5e6-7890-abcd-ef1234567890",
                        "sender": "cliente@example.com",
                        "receiver": "azienda@example.com",
                        "cc": ["cc1@example.com"],
                        "file_name": "documento.pdf",
                        "mime_type": "application/pdf",
                        "size_bytes": 125000,
                        "created_at": "2026-02-16T10:30:00Z",
                        "service_id": "s1s2s3s4-s5s6-7890-abcd-ef1234567890",
                        "email_context": {
                            "subject": "Richiesta preventivo",
                            "sender_email": "cliente@example.com",
                            "cc_emails": ["cc1@example.com"],
                            "summary": "Il cliente richiede un preventivo per...",
                            "category": "INFO_REQUESTED",
                            "subcategory": "PRICING",
                            "started_at": "2026-02-16T10:00:00Z",
                            "last_message_at": "2026-02-16T10:30:00Z",
                            "available": True
                        }
                    }
                }
            },
        },
        404: {
            "description": "Attachment non trovato",
            "content": {
                "application/json": {
                    "example": {"detail": "Attachment con ID xxx non trovato"}
                }
            },
        },
        500: {
            "description": "Errore interno",
            "content": {
                "application/json": {
                    "example": {"detail": "Errore database durante: recupero attachment"}
                }
            },
        },
    }
)
def preview_attachment(attachment_id: str):
    attachment_data = controller.get_attachment_file(attachment_id)
    
    return FileResponse(
        path=attachment_data["file_path"],
        media_type=attachment_data["mime_type"],
        filename=attachment_data["file_name"],
        headers={
            "Content-Disposition": f'inline; filename="{attachment_data["file_name"]}"'
        }
    )


@router.get(
    "/{attachment_id}/download",
    summary="Metadati attachment per download",
    description=(
        "Restituisce i metadati completi di un attachment per download. "
        "Include tutte le informazioni sull'attachment e il contesto dell'email associata.\n\n"
        "Se il thread non è disponibile, email_context.available sarà False."
    ),
    responses={
        200: {
            "description": "Metadati attachment con contesto email",
            "content": {
                "application/json": {
                    "example": {
                        "attachment_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                        "thread_id": "t1t2t3t4-t5t6-7890-abcd-ef1234567890",
                        "email_id": "e1e2e3e4-e5e6-7890-abcd-ef1234567890",
                        "sender": "cliente@example.com",
                        "receiver": "azienda@example.com",
                        "cc": ["cc1@example.com"],
                        "file_name": "documento.pdf",
                        "mime_type": "application/pdf",
                        "size_bytes": 125000,
                        "created_at": "2026-02-16T10:30:00Z",
                        "service_id": "s1s2s3s4-s5s6-7890-abcd-ef1234567890",
                        "email_context": {
                            "subject": "Richiesta preventivo",
                            "sender_email": "cliente@example.com",
                            "cc_emails": ["cc1@example.com"],
                            "summary": "Il cliente richiede un preventivo per...",
                            "category": "INFO_REQUESTED",
                            "subcategory": "PRICING",
                            "started_at": "2026-02-16T10:00:00Z",
                            "last_message_at": "2026-02-16T10:30:00Z",
                            "available": True
                        }
                    }
                }
            },
        },
        404: {
            "description": "Attachment non trovato",
            "content": {
                "application/json": {
                    "example": {"detail": "Attachment con ID xxx non trovato"}
                }
            },
        },
        500: {
            "description": "Errore interno",
            "content": {
                "application/json": {
                    "example": {"detail": "Errore database durante: recupero attachment"}
                }
            },
        },
    }
)
def download_attachment(attachment_id: str):
    attachment_data = controller.get_attachment_file(attachment_id)
    
    return FileResponse(
        path=attachment_data["file_path"],
        media_type=attachment_data["mime_type"],
        filename=attachment_data["file_name"],
    )
