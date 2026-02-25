from fastapi import APIRouter, Body, status
from typing import Dict, Any

from fastapi.params import Depends
from api.v1.src.core.dependecy import get_current_user
from src.modules.calendars.src.controllers.calendar_controller import CalendarController

router = APIRouter(
    dependencies=[Depends(get_current_user)],
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

@router.post(
    "/events/create",
    status_code=status.HTTP_201_CREATED,
    summary="Crea evento di calendario",
    description="""
    Crea un nuovo evento su Google Calendar o Microsoft Outlook.
    
    **Provider supportati:**
    - `google`: Google Calendar API
    - `microsoft`: Microsoft Graph API (Outlook)
    
    **Campi obbligatori:**
    - `provider`: Provider calendario ("google" o "microsoft")
    - `email`: Email dell'account autenticato
    - `title`: Titolo dell'evento
    - `start`: Data/ora inizio (ISO 8601)
    - `end`: Data/ora fine (ISO 8601)
    
    **Campi opzionali:**
    - `description`: Descrizione dell'evento
    - `location`: Luogo dell'evento
    - `attendees`: Lista email dei partecipanti
    - `is_all_day`: Se True, evento per l'intera giornata
    - `calendar_id`: ID del calendario (default: "primary")
    - `timezone`: Timezone dell'evento (default: "Europe/Rome")
    - `reminders`: Lista di minuti per i promemoria (solo Google)
    """,
    responses={
        201: {
            "description": "Evento creato con successo",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "event_id": "abc123xyz",
                        "message": "Evento creato con successo",
                        "event": {
                            "id": "abc123xyz",
                            "title": "Riunione di progetto",
                            "description": "Discussione milestone Q1",
                            "start": "2025-01-20T10:00:00+01:00",
                            "end": "2025-01-20T11:00:00+01:00",
                            "location": "Sala riunioni A",
                            "is_all_day": False,
                            "status": "confirmed"
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
                            "summary": "Campi obbligatori mancanti",
                            "value": {
                                "error": True,
                                "status_code": 400,
                                "detail": "Campi obbligatori mancanti: title, start, end"
                            }
                        },
                        "invalid_dates": {
                            "summary": "Date non valide",
                            "value": {
                                "error": True,
                                "status_code": 400,
                                "detail": "Campo 'start/end' non valido: la data di inizio deve essere precedente alla data di fine"
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
                    "example": {
                        "error": True,
                        "status_code": 401,
                        "detail": "Token Google non valido"
                    }
                }
            }
        },
        502: {
            "description": "Errore di comunicazione con il servizio esterno",
            "content": {
                "application/json": {
                    "example": {
                        "error": True,
                        "status_code": 502,
                        "detail": "Errore servizio Gmail: Status code 403: Forbidden"
                    }
                }
            }
        }
    }
)
async def create_event(
    request_data: Dict[str, Any] = Body(
        ...,
        example={
            "provider": "google",
            "email": "user@example.it",
            "title": "Riunione di progetto",
            "description": "Discussione milestone Q1",
            "start": "2025-01-20T10:00:00+01:00",
            "end": "2025-01-20T11:00:00+01:00",
            "location": "Sala riunioni A",
            "attendees": ["collega@example.com"],
            "is_all_day": False,
            "calendar_id": "primary",
            "timezone": "Europe/Rome",
            "reminders": [30, 10]
        }
    )
):
    return await controller.create_calendar_event(request_data)


# =============================================================================
# MODIFICA EVENTO
# =============================================================================

@router.patch(
    "/events/{event_id}",
    status_code=status.HTTP_200_OK,
    summary="Modifica evento di calendario",
    description="""
    Modifica un evento esistente su Google Calendar o Microsoft Outlook.
    
    **Provider supportati:**
    - `google`: Google Calendar API
    - `microsoft`: Microsoft Graph API (Outlook)
    
    **Campi obbligatori:**
    - `provider`: Provider calendario ("google" o "microsoft")
    - `email`: Email dell'account autenticato
    - `event_id`: ID dell'evento da modificare (nel path)
    
    **Campi opzionali (solo quelli da modificare):**
    - `title`: Nuovo titolo
    - `description`: Nuova descrizione
    - `start`: Nuova data/ora inizio (ISO 8601)
    - `end`: Nuova data/ora fine (ISO 8601)
    - `location`: Nuovo luogo
    - `attendees`: Nuova lista partecipanti
    - `is_all_day`: Evento giornata intera
    - `calendar_id`: ID del calendario (default: "primary")
    - `timezone`: Timezone dell'evento
    """,
    responses={
        200: {
            "description": "Evento aggiornato con successo",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "event_id": "abc123xyz",
                        "message": "Evento aggiornato con successo",
                        "event": {
                            "id": "abc123xyz",
                            "title": "Riunione di progetto - UPDATED",
                            "description": "Discussione milestone Q1 e Q2",
                            "start": "2025-01-20T14:00:00+01:00",
                            "end": "2025-01-20T15:30:00+01:00",
                            "location": "Sala riunioni B",
                            "is_all_day": False,
                            "status": "confirmed"
                        }
                    }
                }
            }
        },
        400: {
            "description": "Richiesta non valida",
            "content": {
                "application/json": {
                    "example": {
                        "error": True,
                        "status_code": 400,
                        "detail": "Campi obbligatori mancanti: provider, email"
                    }
                }
            }
        },
        404: {
            "description": "Evento non trovato",
            "content": {
                "application/json": {
                    "example": {
                        "error": True,
                        "status_code": 404,
                        "detail": "Evento 'abc123xyz' non trovato"
                    }
                }
            }
        },
        401: {
            "description": "Token non valido o scaduto",
            "content": {
                "application/json": {
                    "example": {
                        "error": True,
                        "status_code": 401,
                        "detail": "Token Microsoft non valido"
                    }
                }
            }
        }
    }
)
async def update_event(
    event_id: str,
    request_data: Dict[str, Any] = Body(
        ...,
        example={
            "provider": "google",
            "email": "user@example.it",
            "title": "Riunione di progetto - UPDATED",
            "description": "Discussione milestone Q1 e Q2",
            "start": "2025-01-20T14:00:00+01:00",
            "end": "2025-01-20T15:30:00+01:00",
            "location": "Sala riunioni B"
        }
    )
):
    request_data["event_id"] = event_id
    return await controller.update_calendar_event(request_data)

@router.delete(
    "/events/{event_id}",
    status_code=status.HTTP_200_OK,
    summary="Elimina evento di calendario",
    description="""
    Elimina un evento esistente da Google Calendar o Microsoft Outlook.
    
    **Provider supportati:**
    - `google`: Google Calendar API
    - `microsoft`: Microsoft Graph API (Outlook)
    
    **Campi obbligatori:**
    - `provider`: Provider calendario ("google" o "microsoft")
    - `email`: Email dell'account autenticato
    - `event_id`: ID dell'evento da eliminare (nel path)
    
    **Campi opzionali:**
    - `calendar_id`: ID del calendario (default: "primary")
    """,
    responses={
        200: {
            "description": "Evento eliminato con successo",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "event_id": "abc123xyz",
                        "message": "Evento eliminato con successo"
                    }
                }
            }
        },
        400: {
            "description": "Richiesta non valida",
            "content": {
                "application/json": {
                    "example": {
                        "error": True,
                        "status_code": 400,
                        "detail": "Campi obbligatori mancanti: provider, email"
                    }
                }
            }
        },
        404: {
            "description": "Evento non trovato",
            "content": {
                "application/json": {
                    "example": {
                        "error": True,
                        "status_code": 404,
                        "detail": "Evento 'abc123xyz' non trovato"
                    }
                }
            }
        },
        401: {
            "description": "Token non valido o scaduto",
            "content": {
                "application/json": {
                    "example": {
                        "error": True,
                        "status_code": 401,
                        "detail": "Token Google non valido"
                    }
                }
            }
        }
    }
)
async def delete_event(
    event_id: str,
    request_data: Dict[str, Any] = Body(
        ...,
        example={
            "provider": "google",
            "email": "user@example.it",
            "calendar_id": "primary"
        }
    )
):
    request_data["event_id"] = event_id
    return await controller.delete_calendar_event(request_data)
