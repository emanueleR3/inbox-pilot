from fastapi import APIRouter, Path, status
from fastapi.params import Depends
from src.core.dependecy import get_current_user
from src.modules.notifications.notification_controller import NotificationController

router = APIRouter(
    dependencies=[Depends(get_current_user)],
    tags=["Notifications"]
)

controller = NotificationController()


@router.get(
    "/retrieve/{email}",
    status_code=status.HTTP_200_OK,
    summary="Recupera tutte le notifiche per email",
    description=(
        "Recupera tutte le notifiche associate a una specifica email. "
        "Include il body dell'email dalla tabella emails.\n\n"
        "Note:\n"
        "- email è obbligatoria nel path\n"
        "- Le notifiche sono ordinate per data (più recenti prima)\n"
        "- Include informazioni complete dell'email associata"
    ),
    responses={
        200: {
            "description": "Lista di notifiche con informazioni email",
            "content": {
                "application/json": {
                    "example": {
                        "notifications": [
                            {
                                "notification_id": "n1n2n3n4-n5n6-7890-abcd-ef1234567890",
                                "text": "Nuova email ricevuta",
                                "type": "email_received",
                                "email": "user@example.com",
                                "email_id": "e1e2e3e4-e5e6-7890-abcd-ef1234567890",
                                "view": False,
                                "email_body": "Contenuto dell'email...",
                                "email_datetime": "2026-02-18T10:30:00Z",
                                "email_message_id": "msg123",
                                "email_outcome": "success",
                                "email_direction": "inbound",
                                "email_has_attachment": True
                            }
                        ],
                        "total": 1
                    }
                }
            },
        },
        400: {
            "description": "Richiesta non valida",
            "content": {
                "application/json": {
                    "example": {"detail": "Campi obbligatori mancanti: email"}
                }
            },
        },
        500: {
            "description": "Errore interno del server",
            "content": {
                "application/json": {
                    "example": {"detail": "Errore database durante: recupero notifiche"}
                }
            },
        },
    }
)
def retrieve_notifications_by_email(
    email: str = Path(..., description="Email dell'utente")
):
    """
    Recupera tutte le notifiche per una specifica email con il body dell'email associata.
    """
    return controller.get_notifications_by_email(email)


@router.patch(
    "/setTrue/{notification_id}",
    status_code=status.HTTP_200_OK,
    summary="Marca notifica come vista",
    description=(
        "Marca una notifica specifica come vista (view = true).\n\n"
        "Note:\n"
        "- notification_id è obbligatorio nel path\n"
        "- Restituisce conferma dell'operazione\n"
        "- Se la notifica non esiste, restituisce 404"
    ),
    responses={
        200: {
            "description": "Notifica marcata come vista con successo",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Notifica marcata come vista",
                        "notification_id": "n1n2n3n4-n5n6-7890-abcd-ef1234567890",
                        "view": True
                    }
                }
            },
        },
        400: {
            "description": "Richiesta non valida",
            "content": {
                "application/json": {
                    "example": {"detail": "Campi obbligatori mancanti: notification_id"}
                }
            },
        },
        404: {
            "description": "Notifica non trovata",
            "content": {
                "application/json": {
                    "example": {"detail": "Notifica con ID n1n2n3n4-n5n6-7890-abcd-ef1234567890 non trovata"}
                }
            },
        },
        500: {
            "description": "Errore interno del server",
            "content": {
                "application/json": {
                    "example": {"detail": "Errore database durante: aggiornamento notifica"}
                }
            },
        },
    }
)
def mark_notification_viewed(
    notification_id: str = Path(..., description="ID della notifica da marcare come vista")
):
    """
    Marca una notifica come vista impostando il campo view a true.
    """
    return controller.mark_notification_as_viewed(notification_id)
