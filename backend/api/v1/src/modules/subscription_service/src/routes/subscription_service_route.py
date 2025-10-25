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
