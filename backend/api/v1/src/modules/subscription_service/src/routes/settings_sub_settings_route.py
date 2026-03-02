from fastapi import APIRouter, Body, Depends
from src.core.dependecy import get_current_user
from src.modules.subscription_service.src.controllers.subscription_service_controller import SubscriptionServiceController

router = APIRouter(
    dependencies=[Depends(get_current_user)],
    tags=["Settings Subscription Service"],
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
                            "draft": True
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
        "draft",
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

@router.get(
    "/service-settings/{email}",
    summary="Recupera tutti i settings del servizio",
    description="Restituisce i parametri di configurazione del servizio (business_hours, appointment_duration, email_signature, tone_of_voice, phone_numbers) associati all'email specificata.",
    responses={
        200: {
            "description": "Settings recuperati con successo",
            "content": {
                "application/json": {
                    "example": {
                        "business_hours": {
                            "monday": ["09:00-13:00", "14:00-18:00"],
                            "tuesday": ["09:00-13:00", "14:00-18:00"],
                            "wednesday": ["09:00-13:00", "14:00-18:00"],
                            "thursday": ["09:00-13:00", "14:00-18:00"],
                            "friday": ["09:00-13:00"]
                        },
                        "appointment_duration": 30,
                        "email_signature": "Cordiali saluti,\nIl Team",
                        "tone_of_voice": "professionale",
                        "phone_numbers": ["+39 123456789", "+39 987654321"]
                    }
                }
            },
        },
        400: {
            "description": "Richiesta non valida",
            "content": {
                "application/json": {
                    "example": {
                        "error": True,
                        "status_code": 400,
                        "detail": "Campi obbligatori mancanti: email"
                    }
                }
            }
        },
        404: {
            "description": "Settings non trovati",
            "content": {
                "application/json": {
                    "example": {
                        "error": True,
                        "status_code": 404,
                        "detail": "Settings non trovati per email=user@example.com"
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
                        "detail": "Errore database durante: recupero service settings"
                    }
                }
            }
        }
    },
)
async def get_service_settings(email: str):
    return controller.get_service_settings(email)

@router.patch(
    "/service-settings/{email}",
    summary="Aggiorna uno o più settings del servizio",
    description="""
    Aggiorna selettivamente uno o più parametri di configurazione del servizio.
    
    Questo endpoint permette di modificare i seguenti campi per un servizio identificato dall'email:
    - **business_hours**: Orari di lavoro settimanali in formato JSON (chiave=giorno, valore=array di fasce orarie)
    - **appointment_duration**: Durata degli appuntamenti in minuti (intero positivo)
    - **email_signature**: Firma email personalizzata (stringa)
    - **tone_of_voice**: Tono di voce da utilizzare nelle comunicazioni (stringa)
    - **phone_numbers**: Numeri di telefono di contatto (array o oggetto JSON)
    
    **Formato business_hours:**
    ```json
    {
      "monday": ["09:00-13:00", "14:00-18:00"],
      "tuesday": ["09:00-17:00"],
      "friday": ["09:00-13:00"]
    }
    ```
    
    **Formato phone_numbers (array):**
    ```json
    ["+39 123 456 7890", "+39 098 765 4321"]
    ```
    
    **Formato phone_numbers (oggetto):**
    ```json
    {
      "principale": "+39 123 456 7890",
      "secondario": "+39 098 765 4321"
    }
    ```
    
    **Parametri:**
    - `email` (obbligatorio): Email del servizio da aggiornare
    - Tutti i campi nel body sono opzionali - vengono aggiornati solo i campi forniti
    """,
    responses={
        200: {
            "description": "Settings aggiornati con successo",
            "content": {
                "application/json": {
                    "example": {
                        "business_hours": {
                            "monday": ["09:00-18:00"],
                            "wednesday": ["10:00-14:00"]
                        },
                        "appointment_duration": 60,
                        "email_signature": "Cordiali saluti,\nIl Team",
                        "tone_of_voice": "amichevole",
                        "phone_numbers": ["+39 123456789"]
                    }
                }
            },
        },
        400: {
            "description": "Richiesta non valida",
            "content": {
                "application/json": {
                    "examples": {
                        "missing_email": {
                            "summary": "Email mancante",
                            "value": {
                                "error": True,
                                "status_code": 400,
                                "detail": "Campi obbligatori mancanti: email"
                            }
                        },
                        "no_data": {
                            "summary": "Nessun dato da aggiornare",
                            "value": {
                                "error": True,
                                "status_code": 400,
                                "detail": "Nessun dato da aggiornare"
                            }
                        },
                        "invalid_business_hours_type": {
                            "summary": "Tipo business_hours non valido",
                            "value": {
                                "error": True,
                                "status_code": 400,
                                "detail": "business_hours deve essere un oggetto JSON"
                            }
                        },
                        "invalid_business_hours_format": {
                            "summary": "Formato orario non valido",
                            "value": {
                                "error": True,
                                "status_code": 400,
                                "detail": "Formato orario non valido: 09:00. Usare formato HH:MM-HH:MM"
                            }
                        },
                        "invalid_duration": {
                            "summary": "Durata appuntamento non valida",
                            "value": {
                                "error": True,
                                "status_code": 400,
                                "detail": "appointment_duration deve essere un numero intero positivo"
                            }
                        },
                        "invalid_signature": {
                            "summary": "Firma email non valida",
                            "value": {
                                "error": True,
                                "status_code": 400,
                                "detail": "email_signature deve essere una stringa"
                            }
                        },
                        "invalid_tone": {
                            "summary": "Tono di voce non valido",
                            "value": {
                                "error": True,
                                "status_code": 400,
                                "detail": "tone_of_voice deve essere una stringa"
                            }
                        },
                        "invalid_phone_numbers": {
                            "summary": "Numeri di telefono non validi",
                            "value": {
                                "error": True,
                                "status_code": 400,
                                "detail": "phone_numbers deve essere un oggetto JSON o un array"
                            }
                        }
                    }
                }
            }
        },
        404: {
            "description": "Servizio non trovato",
            "content": {
                "application/json": {
                    "example": {
                        "error": True,
                        "status_code": 404,
                        "detail": "Servizio non trovato per email=user@example.com"
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
                        "detail": "Errore database durante: aggiornamento service settings"
                    }
                }
            }
        }
    },
)
async def update_service_settings(
    email: str,
    payload: dict = Body(
        ...,
        example={
            "business_hours": {
                "monday": ["09:00-13:00", "14:00-18:00"],
                "friday": ["09:00-13:00"]
            },
            "appointment_duration": 45,
            "email_signature": "Cordiali saluti,\nIl Team",
            "tone_of_voice": "formale e cortese",
            "phone_numbers": ["+39 123456789", "+39 987654321"]
        }
    )
):
    return controller.update_service_settings(email, payload)

