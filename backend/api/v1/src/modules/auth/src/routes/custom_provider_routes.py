from fastapi import APIRouter, Depends, Body, HTTPException, status
from src.core.dependecy import get_current_user
from src.modules.auth.src.controllers.custom_provider_controller import CustomProviderController

router = APIRouter(tags=["Auth Custom Provider"])

@router.post(
    "/custom-provider/login",
    summary="Login con provider email personalizzato",
    description="""
    Permette il login utilizzando un provider email personalizzato (IMAP/SMTP).
    Richiede le credenziali e le configurazioni del server di posta.
    """,
    responses={
        200: {
            "description": "Credenziali salvate con successo",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "message": "Credenziali custom provider salvate con successo",
                        "data": {
                            "email": "user@example.com",
                            "subscription_id": "sub_12345",
                            "email_provider": "imap",
                            "imap_server": "imap.example.com",
                            "smtp_server": "smtp.example.com"
                        }
                    }
                }
            }
        },
        400: {
            "description": "Richiesta non valida",
            "content": {
                "application/json": {
                    "examples": {
                        "missing_fields": {
                            "value": {
                                "detail": "Campi obbligatori mancanti: server_imap, server_smtp, email, password"
                            }
                        },
                        "invalid_port": {
                            "value": {
                                "detail": "Porte IMAP/SMTP non valide"
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
                        "detail": "Errore durante il salvataggio delle credenziali"
                    }
                }
            }
        }
    }
)
async def custom_login_route(
    payload: dict = Body(
        ...,
        example={
            "server_imap": "imap.example.com",
            "server_smtp": "smtp.example.com",
            "imap_port": 993,
            "smtp_port": 465,
            "email": "user@example.com",
            "password": "secure_password",
            "subscription_id": "sub_12345"
        },
        description="Credenziali e configurazione del server di posta personalizzato"
    )
):
    return await CustomProviderController.custom_provider_login(payload)