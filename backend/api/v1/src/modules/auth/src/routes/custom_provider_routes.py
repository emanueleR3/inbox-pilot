from fastapi import APIRouter, Depends, Body
from src.core.dependecy import get_current_user
from src.modules.auth.src.controllers.custom_provider_controller import CustomProviderController

router = APIRouter(tags=["Auth Custom Provider"])

@router.post(
    "/custom-provider/login",
    summary="Login con provider email personalizzato",
    description="""
    Permette il login utilizzando un provider email personalizzato (IMAP/SMTP).
    Richiede le credenziali e le configurazioni del server di posta.
    
    IMPORTANTE: service_id è OBBLIGATORIO. Devi prima chiamare POST /create-new-service 
    per ottenere un service_id, poi passarlo in questa richiesta.
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
                            "email": "user1@example.com",
                            "email_provider": "imap",
                            "calendar_provider": "null",
                            "calendar_names": "null",
                            "information": "null",
                            "imap_server": "imap.example.com",
                            "imap_port": 993,
                            "smtp_server": "smtp.example.com",
                            "smtp_port": 465,
                            "hashed_password": "null",
                            "hashed_access_token": "null",
                            "hashed_refresh_token": "null",
                            "expiry_token": "null",
                            "confidence_response_threshold": 0.8,
                            "confidence_review_mail": 0.7,
                            "priority_threshold": 0.6,
                            "confidence_classification_threshold": 0.75,
                            "urgent_meeting_threshold": 0.9,
                            "history_id": "null",
                            "microsoft_subscription_id_inbound": "null",
                            "microsoft_subscription_id_outbound": "null",
                            "microsoft_expiration_datetime_inbound": "null",
                            "microsoft_expiration_datetime_outbound": "null",
                            "oauth_user_id": "null"
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
                        "missing_service_id": {
                            "value": {
                                "detail": "service_id è obbligatorio. Devi prima creare un service con POST /create-new-service"
                            }
                        },
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
            "service_id": "service_id_12345",
            "subscription_id": "sub_12345",
            "server_imap": "imap.example.com",
            "server_smtp": "smtp.example.com",
            "imap_port": 993,
            "smtp_port": 465,
            "email": "user@example.com",
            "password": "secure_password",
            "calendar_provider": "google"
        },
        description="Credenziali e configurazione del server di posta personalizzato. IMPORTANTE: service_id è OBBLIGATORIO - ottienilo prima con POST /create-new-service"
    )
):
    # Validazione service_id obbligatorio
    if not payload.get("service_id"):
        from src.handler_exception import BadRequestException
        raise BadRequestException(detail="service_id è obbligatorio.")
    
    res = CustomProviderController.custom_provider_login(payload)
    return {"status": "success", "message": "Credenziali custom provider salvate con successo", "data": res}