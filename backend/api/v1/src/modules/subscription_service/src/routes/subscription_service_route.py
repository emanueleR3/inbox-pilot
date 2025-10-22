from fastapi import APIRouter, Body, Depends
from src.core.dependecy import get_current_user
from src.modules.subscription_service.src.controllers.subscription_service_controller import SubscriptionServiceController

router = APIRouter(
    dependencies=[Depends(get_current_user)],
    tags=["Subscription Service"],
)
controller = SubscriptionServiceController()

@router.get(
    "/getConfig/{subscription_id}",
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
        404: {"description": "Configurazione non trovata"},
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


@router.post(
    "/createConfig",
    summary="Crea una nuova configurazione di abbonamento",
    description=(
        "Crea una nuova configurazione completa per un abbonamento. "
        "Richiede informazioni sull'account email, i parametri di priorità e le soglie di confidenza."
    ),
    responses={
        200: {
            "description": "Configurazione creata con successo",
            "content": {
                "application/json": {
                    "example": {
                        "status": "ok",
                        "result": {
                            "subscription_id": "sub_12345",
                            "email": "user@example.com",
                            "calendar_provider": "google",
                            "calendar_names": ["Lavoro", "Personale"],
                            "information": {"timezone": "Europe/Rome"},
                            "imap_server": "imap.gmail.com",
                            "imap_port": 993,
                            "smtp_server": "smtp.gmail.com",
                            "smtp_port": 465,
                            "confidence_response_threshold": 0.8,
                            "confidence_review_mail": 0.7,
                            "priority_threshold": 0.5,
                            "confidence_classification_threshold": 0.75,
                            "urgent_meeting_threshold": 0.9,
                            "history_id": "h_123456",
                            "microsoft_subscription_id": None,
                            "microsoft_expiration_datetime": None,
                            "oauth_user_id": "oauth_67890",
                            "expiry_token": "2025-12-31T23:59:59Z",
                        },
                    }
                }
            },
        },
        400: {"description": "Dati forniti non validi"},
    },
)
def create_configuration(
    payload: dict = Body(
        ...,
        example={
            "configuration": {
                "subscription_id": "sub_12345",
                "email": "user@example.com",
                "calendar_provider": "google",
                "calendar_names": ["Lavoro", "Personale"],
                "information": {"timezone": "Europe/Rome"},
                "imap_server": "imap.gmail.com",
                "imap_port": 993,
                "smtp_server": "smtp.gmail.com",
                "smtp_port": 465,
                "hashed_password": "hashed_pwd_123",
                "hashed_access_token": "hashed_access_456",
                "hashed_refresh_token": "hashed_refresh_789",
                "expiry_token": "2025-12-31T23:59:59Z",
                "confidence_response_threshold": 0.8,
                "confidence_review_mail": 0.7,
                "priority_threshold": 0.5,
                "confidence_classification_threshold": 0.75,
                "urgent_meeting_threshold": 0.9,
                "history_id": "h_123456",
                "microsoft_subscription_id": None,
                "microsoft_expiration_datetime": None,
                "oauth_user_id": "oauth_67890",
            }
        },
        description="Tutti i campi necessari per creare una configurazione di abbonamento completa.",
    ),
):
    result = controller.create_configuration(payload)
    return {"status": "ok", "result": result}

@router.patch(
    "/updateConfig/{subscription_id}",
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
        400: {"description": "Parametri di aggiornamento non validi"},
        404: {"description": "Configurazione non trovata"},
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
