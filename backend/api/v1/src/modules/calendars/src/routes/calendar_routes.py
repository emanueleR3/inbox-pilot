from fastapi import APIRouter, Body, status
from typing import Dict, Any
from src.modules.calendars.src.controllers.calendar_controller import CalendarController

router = APIRouter(
    tags=["Calendars"]
)

controller = CalendarController()

@router.post(
    "/events",
    status_code=status.HTTP_200_OK,
    summary="Recupera eventi di calendario",
    description="""
    Recupera eventi di calendario da Google Calendar o Microsoft Outlook.
    
    Supporta entrambi i provider con un'interfaccia unificata.
    Gli eventi vengono normalizzati in un formato comune indipendentemente dal provider.
    
    **Provider supportati:**
    - `google`: Google Calendar API
    - `microsoft`: Microsoft Graph API (Outlook)
    
    **Autenticazione:**
    È necessario fornire un token OAuth valido per il provider selezionato.
    
    **Filtri opzionali:**
    - `time_min`: Filtra eventi a partire da questa data/ora (ISO 8601)
    - `time_max`: Filtra eventi fino a questa data/ora (ISO 8601)
    - `max_results`: Limita il numero di risultati (default: 100, max: 2500)
    - `calendar_id`: ID del calendario (default: "primary")
    
    **Thread Summary:**
    Per ogni evento, viene verificato se è stato generato da una email gestita dall'AI.
    Se l'evento è associato a un thread email (tramite `scheduled_events`), viene incluso
    il summary del thread nel campo `thread_summary`. Altrimenti, il campo conterrà
    "Evento non generato da email gestita da AI".
    """,
    responses={
        200: {
            "description": "Lista di eventi recuperati con successo",
            "content": {
                "application/json": {
                    "examples": {
                        "event_from_email": {
                            "summary": "Evento generato da email",
                            "value": [
                                {
                                    "id": "abc123xyz",
                                    "title": "Riunione di team",
                                    "description": "Discussione progetto Q1",
                                    "start": "2025-01-15T10:00:00+00:00",
                                    "end": "2025-01-15T11:00:00+00:00",
                                    "location": "Sala conferenze A",
                                    "organizer": {
                                        "email": "manager@example.com",
                                        "name": "Mario Rossi"
                                    },
                                    "attendees": [
                                        {
                                            "email": "user1@example.com",
                                            "name": "Luca Bianchi",
                                            "response_status": "accepted"
                                        }
                                    ],
                                    "is_all_day": False,
                                    "status": "confirmed",
                                    "html_link": "https://calendar.google.com/event?eid=abc123",
                                    "thread_summary": "Il cliente ha richiesto una riunione per discutere il progetto Q1 e le tempistiche di consegna."
                                }
                            ]
                        },
                        "event_not_from_email": {
                            "summary": "Evento non generato da email",
                            "value": [
                                {
                                    "id": "def456abc",
                                    "title": "Pausa pranzo",
                                    "description": None,
                                    "start": "2025-01-15T12:00:00+00:00",
                                    "end": "2025-01-15T13:00:00+00:00",
                                    "location": None,
                                    "organizer": {
                                        "email": "user@example.com",
                                        "name": "Utente"
                                    },
                                    "attendees": [],
                                    "is_all_day": False,
                                    "status": "confirmed",
                                    "html_link": "https://calendar.google.com/event?eid=def456",
                                    "thread_summary": "Evento non generato da email gestita da AI"
                                }
                            ]
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
                                "detail": "Campi obbligatori mancanti: provider, token"
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
                        "invalid_date": {
                            "summary": "Formato data non valido",
                            "value": {
                                "error": True,
                                "status_code": 400,
                                "detail": "Campo 'time_min' non valido: formato data/ora non valido. Utilizzare formato ISO 8601"
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
                        "google_error": {
                            "summary": "Errore Google Calendar",
                            "value": {
                                "error": True,
                                "status_code": 502,
                                "detail": "Errore servizio Gmail: Status code 403: Forbidden"
                            }
                        },
                        "microsoft_error": {
                            "summary": "Errore Microsoft Graph",
                            "value": {
                                "error": True,
                                "status_code": 502,
                                "detail": "Errore servizio Microsoft Graph: Timeout durante la richiesta"
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
async def get_events(
    request_data: Dict[str, Any] = Body(
        ...,
        example={
            "provider": "google",
            "email": "user@example.it",
            "time_min": "2025-01-01T00:00:00Z",
            "time_max": "2025-01-31T23:59:59Z",
            "max_results": 50,
            "calendar_id": "primary"
        }
    )
):
    return await controller.get_calendar_events(request_data)
